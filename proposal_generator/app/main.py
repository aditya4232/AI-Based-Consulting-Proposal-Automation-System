from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import ProposalRequest, ProposalResponse
from app.prompt_builder import build_prompt
from app.generator import generate_proposal
from app.cost_logic import calculate_cost, save_cost_report, estimate_team_composition
from app.pdf_builder import build_proposal_pdf

app = FastAPI(title="AI Proposal Generator")

# Allow broad CORS so frontend clients can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "message": "AI Proposal Generator API is running! Visit /docs for the interactive API playground."
    }


@app.post("/generate-proposal", response_model=ProposalResponse)
def generate(data: ProposalRequest, background_tasks: BackgroundTasks):
    """Generate a structured consulting proposal."""

    prompt = build_prompt(data)
    sections = generate_proposal(prompt)

    cost_data = calculate_cost(data.duration_months, data.expected_users)

    # Persist cost report files in background
    try:
        background_tasks.add_task(save_cost_report, cost_data)
    except Exception as e:
        print(f"Warning: failed to schedule cost report save: {e}")

    return {
        "executive_summary": sections["executive_summary"],
        "technical_approach": sections["technical_approach"],
        "timeline": sections["timeline"],
        "estimated_cost": cost_data,
        "risk_assessment": sections["risk_assessment"],
        "deliverables": sections["deliverables"],
    }


@app.post("/download-proposal-pdf")
def download_pdf(data: ProposalRequest):
    """Generate the proposal and return it as a downloadable formal PDF."""

    prompt = build_prompt(data)
    sections = generate_proposal(prompt)
    cost_data = calculate_cost(data.duration_months, data.expected_users)
    team = estimate_team_composition(data.duration_months, data.expected_users, data.tech_stack)

    # Compose a full proposal dict for the PDF builder
    proposal_for_pdf = {
        "project_title": data.project_title,
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

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{data.project_title.replace(' ', '_')}_Proposal.pdf",
    )
