"""SQLite-backed device session management.

Each browser/device gets a stable UUID (generated client-side and stored
in localStorage). The backend records devices and proposal history so that
history survives page reloads, tab closes, and multi-day sessions.
"""

import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

# ── Database location ────────────────────────────────────────────────────────
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(_DB_DIR, "sessions.db")


def _conn() -> sqlite3.Connection:
    """Return a new SQLite connection with Row factory enabled."""
    os.makedirs(_DB_DIR, exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")  # concurrent read/write
    return con


# ── Schema ───────────────────────────────────────────────────────────────────
def init_db() -> None:
    """Create tables and indexes if they do not exist. Safe to call on every start."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id       TEXT PRIMARY KEY,
                user_name       TEXT NOT NULL DEFAULT '',
                created_at      TEXT NOT NULL,
                last_seen       TEXT NOT NULL,
                proposal_count  INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS proposals (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id       TEXT NOT NULL,
                filename        TEXT NOT NULL,
                project_title   TEXT,
                client_name     TEXT,
                industry        TEXT,
                duration_months INTEGER,
                expected_users  INTEGER,
                provider        TEXT,
                model           TEXT,
                sections_json   TEXT,
                created_at      TEXT NOT NULL,
                FOREIGN KEY (device_id) REFERENCES devices (device_id)
            );

            CREATE INDEX IF NOT EXISTS idx_proposals_device
                ON proposals (device_id, created_at DESC);

            -- Migrations: add columns if upgrading from older schema
            PRAGMA table_info(devices);
            PRAGMA table_info(proposals);
        """)
        # Non-destructive column additions for existing databases
        try:
            con.execute("ALTER TABLE devices ADD COLUMN user_name TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        try:
            con.execute("ALTER TABLE proposals ADD COLUMN sections_json TEXT")
        except Exception:
            pass


# ── Device registration ───────────────────────────────────────────────────────
def register_device(device_id: str, user_name: str = "") -> dict:
    """Upsert a device record. Returns full device info."""
    now = datetime.now(timezone.utc).isoformat()
    user_name = (user_name or "").strip()[:80]
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()

        if row:
            con.execute(
                "UPDATE devices SET last_seen = ?, user_name = CASE WHEN ? != '' THEN ? ELSE user_name END WHERE device_id = ?",
                (now, user_name, user_name, device_id),
            )
            uname = user_name if user_name else (row["user_name"] or "")
            return {
                "device_id": device_id,
                "user_name": uname,
                "is_new": False,
                "created_at": row["created_at"],
                "last_seen": now,
                "proposal_count": row["proposal_count"],
            }
        else:
            con.execute(
                "INSERT INTO devices (device_id, user_name, created_at, last_seen, proposal_count) "
                "VALUES (?, ?, ?, ?, 0)",
                (device_id, user_name, now, now),
            )
            return {
                "device_id": device_id,
                "user_name": user_name,
                "is_new": True,
                "created_at": now,
                "last_seen": now,
                "proposal_count": 0,
            }


def get_device_info(device_id: str) -> Optional[dict]:
    """Return device info or None if not found."""
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
        return dict(row) if row else None


# ── Proposal tracking ─────────────────────────────────────────────────────────
def record_proposal(
    device_id: str,
    filename: str,
    title: str,
    client: str,
    industry: str,
    months: int,
    users: int,
    provider: str,
    model: str,
    sections: dict = None,
) -> int:
    """Insert a proposal record and bump device counter. Returns new row id."""
    now = datetime.now(timezone.utc).isoformat()
    sections_json = json.dumps(sections) if sections else None
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO proposals
               (device_id, filename, project_title, client_name, industry,
                duration_months, expected_users, provider, model, sections_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (device_id, filename, title, client or "", industry,
             months, users, provider or "ollama", model or "auto", sections_json, now),
        )
        con.execute(
            "UPDATE devices SET last_seen = ?, proposal_count = proposal_count + 1 "
            "WHERE device_id = ?",
            (now, device_id),
        )
        return cur.lastrowid


def get_proposal_sections(proposal_id: int) -> Optional[dict]:
    """Return the stored sections JSON for a proposal by its row id."""
    with _conn() as con:
        row = con.execute(
            "SELECT sections_json FROM proposals WHERE id = ?", (proposal_id,)
        ).fetchone()
        if row and row["sections_json"]:
            try:
                return json.loads(row["sections_json"])
            except Exception:
                return None
        return None


def get_device_proposals(device_id: str, limit: int = 100) -> list[dict]:
    """Return all proposals for a device, newest first."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM proposals WHERE device_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
