"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Any, Optional
import re


class ProposalRequest(BaseModel):
    """Validated proposal generation request."""

    project_title: str = Field(
        ..., min_length=3, max_length=200,
        description="Project title / name",
    )
    industry: str = Field(
        ..., min_length=2, max_length=100,
        description="Target industry vertical",
    )
    duration_months: int = Field(
        ..., ge=1, le=60,
        description="Project duration in months (1-60)",
    )
    expected_users: int = Field(
        ..., ge=10, le=100_000_000,
        description="Expected number of end users",
    )
    tech_stack: List[str] = Field(
        ..., min_length=1, max_length=15,
        description="Preferred technology stack items",
    )
    client_name: Optional[str] = Field(
        None, max_length=200,
        description="Optional client / company name for the proposal",
    )
    
    # ---- Provider Overrides ----
    provider: Optional[str] = Field(
        "ollama", description="Provider logic to use (ollama, groq, openai)"
    )
    model: Optional[str] = Field(
        None, description="Model to use (if None, auto-detect or use default)"
    )
    api_key: Optional[str] = Field(
        None, description="API key to use for external providers"
    )
    api_url: Optional[str] = Field(
        None, description="Custom API URL / endpoint"
    )

    # ---- Custom project details ----
    custom_notes: Optional[str] = Field(
        None, max_length=2000,
        description="Additional custom requirements, constraints, or details provided by the user",
    )

    # ---- Session tracking ----
    device_id: Optional[str] = Field(
        None, max_length=128,
        description="Browser device UUID for session persistence (optional)",
    )
    user_name: Optional[str] = Field(
        None, max_length=80,
        description="User name for personalising the proposal (optional)",
    )

    @field_validator("project_title", "industry")
    @classmethod
    def strip_and_clean(cls, v: str) -> str:
        """Remove leading/trailing whitespace and collapse internal spaces."""
        v = re.sub(r"\s+", " ", v.strip())
        if not v:
            raise ValueError("Field cannot be blank")
        return v

    @field_validator("tech_stack")
    @classmethod
    def clean_tech_stack(cls, v: list[str]) -> list[str]:
        cleaned = [item.strip() for item in v if item.strip()]
        if not cleaned:
            raise ValueError("tech_stack must contain at least one item")
        return cleaned


class TimelinePhase(BaseModel):
    """Single phase in the project timeline."""
    phase: str
    weeks: int
    description: str


class RiskItem(BaseModel):
    """Single risk entry."""
    risk: str
    impact: str
    mitigation: str


class ProposalResponse(BaseModel):
    """Full proposal response."""
    executive_summary: str
    technical_approach: str
    timeline: Any  # list[TimelinePhase] or str fallback
    estimated_cost: Dict[str, Any]
    risk_assessment: Any  # list[RiskItem] or str fallback
    deliverables: Any  # list[str] or str fallback
    team_composition: Optional[List[Dict[str, Any]]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    uptime_seconds: float


class ProposalHistoryItem(BaseModel):
    """Single item from proposal history."""
    filename: str
    created_at: str
    size_kb: float
    download_url: str


class EditProposalRequest(BaseModel):
    """Request to iterate/edit an existing proposal with context."""
    # Original proposal context (so the AI knows what it's editing)
    project_title: str = Field(..., min_length=3, max_length=200)
    industry: str = Field(..., min_length=2, max_length=100)
    duration_months: int = Field(..., ge=1, le=60)
    expected_users: int = Field(..., ge=10, le=100_000_000)
    tech_stack: List[str] = Field(..., min_length=1)
    client_name: Optional[str] = Field(None, max_length=200)

    # Current sections (what the AI previously generated)
    current_sections: Dict[str, Any] = Field(
        ..., description="The existing proposal sections to edit"
    )

    # The user's edit instruction
    edit_instruction: str = Field(
        ..., min_length=5, max_length=1000,
        description="Natural language instruction for what to change, add, or remove"
    )

    # Provider settings (same as ProposalRequest)
    provider: Optional[str] = Field("ollama")
    model: Optional[str] = Field(None)
    api_key: Optional[str] = Field(None)
    api_url: Optional[str] = Field(None)
    device_id: Optional[str] = Field(None, max_length=128)

    @field_validator("edit_instruction")
    @classmethod
    def clean_instruction(cls, v: str) -> str:
        import re
        v = re.sub(r"\s+", " ", v.strip())
        # Basic injection guard
        v = re.sub(r"(?i)(ignore|forget|disregard)\s+(all|previous|prior|above)\s*(instructions?|rules?|context)", "[REDACTED]", v)
        return v
