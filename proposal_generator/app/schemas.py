from pydantic import BaseModel
from typing import Dict, List, Any


class ProposalRequest(BaseModel):
    project_title: str
    industry: str
    duration_months: int
    expected_users: int
    tech_stack: List[str]


class ProposalResponse(BaseModel):
    executive_summary: str
    technical_approach: str
    timeline: Any  # can be list of phase dicts or string
    estimated_cost: Dict[str, Any]
    risk_assessment: Any  # can be list of risk dicts or string
    deliverables: Any  # can be list of strings or string
