"""FastAPI application — AI Proposal Generator v2."""

import os
import time
import glob
from datetime import datetime, timezone

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.logger import get_logger
from app.schemas import ProposalRequest, ProposalResponse, HealthResponse
from app.prompt_builder import build_prompt
from app.generator import generate_proposal
from app.cost_logic import calculate_cost, save_cost_report, estimate_team_composition
from app.pdf_builder import build_proposal_pdf

log = get_logger(__name__)

_start_time = time.time()

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description="AI-powered consulting proposal automation — generate professional proposals with deterministic cost logic.",
)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Serve frontend static files ----
_frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/static", StaticFiles(directory=_frontend_dir), name="frontend")


# ====================================================================== #
#                               ROUTES                                     #
# ====================================================================== #

@app.get("/")
def read_root():
    """Landing info."""
    return {
        "message": f"{settings.app_title} API v{settings.app_version} is running!",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health / readiness probe."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        uptime_seconds=round(time.time() - _start_time, 2),
    )


@app.post("/generate-proposal", response_model=ProposalResponse)
def generate(data: ProposalRequest, background_tasks: BackgroundTasks):
    """Generate a structured consulting proposal (JSON response)."""
    log.info("Generating proposal: %s (%s, %d months)", data.project_title, data.industry, data.duration_months)

    provider_opts = {
        "provider": data.provider,
        "model": data.model,
        "api_key": data.api_key,
        "api_url": data.api_url,
    }
    
    prompt = build_prompt(data)
    expected_weeks = data.duration_months * 4
    sections = generate_proposal(prompt, expected_weeks=expected_weeks, provider_opts=provider_opts)

    cost_data = calculate_cost(data.duration_months, data.expected_users)
    team = estimate_team_composition(data.duration_months, data.expected_users, data.tech_stack)

    # Persist cost report files in background
    try:
        background_tasks.add_task(save_cost_report, cost_data)
    except Exception as e:
        log.warning("Failed to schedule cost report save: %s", e)

    return {
        "executive_summary": sections["executive_summary"],
        "technical_approach": sections["technical_approach"],
        "timeline": sections["timeline"],
        "estimated_cost": cost_data,
        "risk_assessment": sections["risk_assessment"],
        "deliverables": sections["deliverables"],
        "team_composition": team,
    }


@app.post("/download-proposal-pdf")
def download_pdf(data: ProposalRequest):
    """Generate and return the proposal as a downloadable PDF."""
    log.info("Generating PDF for: %s", data.project_title)

    provider_opts = {
        "provider": data.provider,
        "model": data.model,
        "api_key": data.api_key,
        "api_url": data.api_url,
    }

    prompt = build_prompt(data)
    expected_weeks = data.duration_months * 4
    sections = generate_proposal(prompt, expected_weeks=expected_weeks, provider_opts=provider_opts)
    cost_data = calculate_cost(data.duration_months, data.expected_users)
    team = estimate_team_composition(data.duration_months, data.expected_users, data.tech_stack)

    proposal_for_pdf = {
        "project_title": data.project_title,
        "client_name": data.client_name or "",
        "industry": data.industry,
        "duration_months": data.duration_months,
        "expected_users": data.expected_users,
        "tech_stack": data.tech_stack,
        "executive_summary": sections["executive_summary"],
        "technical_approach": sections["technical_approach"],
        "timeline": sections["timeline"],
        "estimated_cost": cost_data,
        "risk_assessment": sections["risk_assessment"],
        "deliverables": sections["deliverables"],
        "team_composition": team,
    }

    pdf_path = build_proposal_pdf(proposal_for_pdf)
    safe_title = data.project_title.replace(" ", "_").replace("/", "_")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{safe_title}_Proposal.pdf",
    )


@app.get("/proposals")
def list_proposals():
    """List previously generated proposal PDFs and cost reports."""
    output_dir = settings.output_dir
    if not os.path.isdir(output_dir):
        return {"proposals": [], "cost_reports": []}

    pdfs = []
    for fp in sorted(glob.glob(os.path.join(output_dir, "proposal_*.pdf")), reverse=True):
        stat = os.stat(fp)
        pdfs.append({
            "filename": os.path.basename(fp),
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "size_kb": round(stat.st_size / 1024, 1),
            "download_url": f"/proposals/{os.path.basename(fp)}",
        })

    cost_files = []
    for fp in sorted(glob.glob(os.path.join(output_dir, "cost_report_*.json")), reverse=True):
        stat = os.stat(fp)
        cost_files.append({
            "filename": os.path.basename(fp),
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "size_kb": round(stat.st_size / 1024, 1),
        })

    return {"proposals": pdfs, "cost_reports": cost_files}


@app.get("/proposals/{filename}")
def download_existing_proposal(filename: str):
    """Download an existing proposal PDF by filename."""
    # Sanitise filename — prevent path traversal
    safe_name = os.path.basename(filename)
    filepath = os.path.join(settings.output_dir, safe_name)

    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Proposal not found")

    return FileResponse(path=filepath, media_type="application/pdf", filename=safe_name)
