import os
import json
import csv
import tempfile
import time
from uuid import uuid4
from math import ceil


def estimate_team_composition(
    duration_months: int,
    expected_users: int,
    tech_stack: list[str],
) -> list[dict]:
    """Return a deterministic team composition estimate.

    Uses simple heuristic rules based on project size.
    No LLM involved; purely formula-driven so it never hallucinates.
    """
    # Base team always has these roles
    team = [
        {"role": "Project Manager", "count": 1, "allocation": "Full-time"},
    ]

    # Backend developers: 1 per 3 months, min 1
    backend_count = max(1, ceil(duration_months / 3))
    team.append(
        {"role": "Backend Developer", "count": backend_count, "allocation": "Full-time"}
    )

    # Frontend developers: 1 per 4 months, min 1
    frontend_count = max(1, ceil(duration_months / 4))
    team.append(
        {
            "role": "Frontend Developer",
            "count": frontend_count,
            "allocation": "Full-time",
        }
    )

    # QA engineer: always at least 1
    qa_count = 1 if duration_months <= 4 else 2
    team.append({"role": "QA Engineer", "count": qa_count, "allocation": "Full-time"})

    # DevOps: 1 for larger projects
    if duration_months >= 4 or expected_users >= 5000:
        team.append({"role": "DevOps Engineer", "count": 1, "allocation": "Part-time"})

    # UI/UX designer for any project with a frontend stack
    frontend_stacks = {
        "react",
        "vue.js",
        "vue",
        "angular",
        "next.js",
        "svelte",
        "flutter",
    }
    has_frontend = any(t.lower() in frontend_stacks for t in tech_stack)
    if has_frontend:
        team.append({"role": "UI/UX Designer", "count": 1, "allocation": "Part-time"})

    # Database admin for large user bases
    if expected_users >= 10000:
        team.append(
            {"role": "Database Administrator", "count": 1, "allocation": "Part-time"}
        )

    return team


def calculate_cost(
    duration_months: int,
    expected_users: int,
    dev_rate_per_month: float = 150000.0,  # INR per month (reduced from USD)
    contingency_pct: float = 0.10,
    discount_pct: float = 0.0,
):
    """Return a detailed cost breakdown in INR.

    - Uses tiered per-user infra pricing.
    - Applies contingency to development cost.
    - Applies an optional overall discount.
    - All values in Indian Rupees (INR)
    """

    base_dev_cost = float(dev_rate_per_month) * duration_months

    # Tiered infra cost per user in INR (converted from USD: 1 USD ~ 83 INR)
    if expected_users <= 1000:
        infra_per_user = 42.0  # 0.50 USD * 83
    elif expected_users <= 10000:
        infra_per_user = 29.0  # 0.35 USD * 83
    else:
        infra_per_user = 17.0  # 0.20 USD * 83

    infra_cost = expected_users * infra_per_user

    contingency = base_dev_cost * float(contingency_pct)

    subtotal = base_dev_cost + infra_cost + contingency

    discount = subtotal * float(discount_pct)
    total = subtotal - discount

    monthly_average = total / max(1, duration_months)

    return {
        "development_cost": round(base_dev_cost, 2),
        "infrastructure_cost": round(infra_cost, 2),
        "contingency": round(contingency, 2),
        "discount": round(discount, 2),
        "total_estimated_cost": round(total, 2),
        "monthly_average": round(monthly_average, 2),
        "currency": "INR",
        "details": {
            "duration_months": int(duration_months),
            "expected_users": int(expected_users),
            "infra_per_user": infra_per_user,
            "dev_rate_per_month": float(dev_rate_per_month),
            "contingency_pct": float(contingency_pct),
            "discount_pct": float(discount_pct),
        },
    }


def _resolve_output_dir(provided_dir: str | None) -> str:
    """Resolve a writable output directory.

    Priority: provided_dir -> ENV COST_OUTPUT_DIR -> ./outputs (if writable) -> system temp dir
    """
    env_dir = os.environ.get("COST_OUTPUT_DIR")

    # Base directory that output directories must be under. This prevents path traversal.
    base_root = os.path.abspath(os.environ.get("COST_OUTPUT_BASE", os.getcwd()))

    candidates = [
        provided_dir,
        env_dir,
        os.path.join(os.getcwd(), "outputs"),
        tempfile.gettempdir(),
    ]

    for c in candidates:
        if not c:
            continue
        try:
            candidate_abs = os.path.abspath(c)

            # Ensure candidate is inside allowed base_root
            try:
                common = os.path.commonpath([base_root, candidate_abs])
            except Exception:
                # if paths are on different drives on Windows, skip
                continue

            if common != base_root:
                # candidate is outside allowed base
                continue

            os.makedirs(candidate_abs, exist_ok=True)
            # attempt a tiny write test
            test_path = os.path.join(candidate_abs, ".write_test")
            with open(test_path, "w") as tf:
                tf.write("ok")
            os.remove(test_path)
            return candidate_abs
        except Exception:
            continue

    # As a next attempt, try to create an outputs directory under base_root.
    try:
        fallback_under_base = os.path.join(base_root, "outputs")
        os.makedirs(fallback_under_base, exist_ok=True)
        test_path = os.path.join(fallback_under_base, ".write_test")
        with open(test_path, "w") as tf:
            tf.write("ok")
        os.remove(test_path)
        return os.path.abspath(fallback_under_base)
    except Exception:
        pass

    # final fallback behavior:
    # By default we allow returning the system temp directory as a last resort
    # because some environments may not allow writing under `base_root` (e.g., read-only containers).
    # To opt out of this behavior and enforce strict containment under `base_root`, set
    # the environment variable `COST_ALLOW_SYSTEM_TEMP=0`.
    # default to strict mode (no system temp fallback) unless explicitly allowed
    allow_system_temp = os.environ.get("COST_ALLOW_SYSTEM_TEMP", "0")
    if allow_system_temp and allow_system_temp != "0":
        return os.path.abspath(tempfile.gettempdir())

    # Strict mode: do not fall back outside base_root
    raise RuntimeError(
        "No writable output directory found within allowed base; set COST_ALLOW_SYSTEM_TEMP=1 to permit system temp fallback."
    )


def save_cost_report(
    cost_data: dict, output_dir: str | None = None, prefix: str | None = None
) -> dict:
    """Save `cost_data` as JSON and CSV in `output_dir` and return file paths.

    `output_dir` can be None to let the function resolve a safe writable location.
    """
    resolved_dir = _resolve_output_dir(output_dir)

    # ensure a unique filename prefix by default to avoid overwrites
    if not prefix:
        prefix = f"cost_report_{int(time.time())}_{uuid4().hex[:6]}"

    base_name = f"{prefix}"
    json_path = os.path.join(resolved_dir, f"{base_name}.json")
    csv_path = os.path.join(resolved_dir, f"{base_name}.csv")

    # JSON
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(cost_data, jf, indent=2)

    # CSV (flat key / value pairs for top-level items)
    with open(csv_path, "w", newline="", encoding="utf-8") as cf:
        writer = csv.writer(cf)
        writer.writerow(["key", "value"])

        for k, v in cost_data.items():
            if isinstance(v, dict):
                writer.writerow([k, json.dumps(v)])
            else:
                writer.writerow([k, v])

    return {"json": os.path.abspath(json_path), "csv": os.path.abspath(csv_path)}
