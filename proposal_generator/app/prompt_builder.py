"""Build structured prompts that force the LLM to return strict JSON."""

import re as _re


# ── Shared injection sanitizer ────────────────────────────────────────────────
def _sanitize(text: str) -> str:
    text = _re.sub(
        r"(?i)(ignore|forget|disregard)\s+(previous|prior|above|all)\s*(instructions?|rules?|context)",
        "[REDACTED]", text
    )
    text = text.replace("</", "&lt;/").replace("<|", "&lt;|")
    return text.strip()


def build_prompt(data) -> str:
    """Build a strict JSON-only prompt with anti-hallucination guardrails.
    Calibrated for Feb 2026 technology landscape and industry context.
    """
    total_weeks = data.duration_months * 4
    tech_csv = ", ".join(data.tech_stack)
    client_note = f" for {data.client_name}" if getattr(data, "client_name", None) else ""
    user_note = f" (prepared by {data.user_name})" if getattr(data, "user_name", None) else ""
    custom_section = ""
    if getattr(data, "custom_notes", None):
        safe_notes = _sanitize(data.custom_notes)
        custom_section = (
            "\n\n<USER_NOTES>\n"
            "The client provided the following additional context. Incorporate relevant details "
            "into the proposal sections above, but do NOT alter the required JSON schema:\n"
            f"{safe_notes}\n"
            "</USER_NOTES>"
        )

    return f"""You are a senior consulting solution architect{user_note} writing a professional proposal{client_note}.
Today's date is February 2026. Use current 2026 industry standards, tools, and best practices.

TASK: Produce a SINGLE JSON object for a project proposal. No extra text, no markdown, only the JSON object.

PROJECT DETAILS:
- Title: {data.project_title}
- Industry: {data.industry}
- Duration: {data.duration_months} months ({total_weeks} weeks total)
- Expected End-Users: {data.expected_users:,}
- Tech Stack: {tech_csv}{custom_section}

REQUIRED JSON SCHEMA - return EXACTLY this structure, no extra keys:
{{
  "executive_summary": "<string: 4-5 sentences. Cover: (1) what the system does, (2) the specific business problem it solves for the {data.industry} industry, (3) at least one quantified outcome e.g. reduce processing time by 40%, (4) which organisations benefit, (5) strategic ROI or compliance value. Write in active, confident tone. Be specific to {data.industry} in 2026.>",
  "technical_approach": "<string: 4-5 sentences. Cover: (1) frontend architecture using relevant parts of {tech_csv}, (2) backend services and API design, (3) database strategy with RDBMS vs NoSQL justification for {data.expected_users:,} users, (4) scalability and cloud-native deployment approach appropriate for 2026, (5) CI/CD, monitoring, and security posture. Reference at least 2 specific technologies from {tech_csv}.>",
  "timeline": [
    {{
      "phase": "<string: phase name, e.g. Discovery and Requirements>",
      "weeks": <integer: weeks for this phase>,
      "description": "<string: one concrete sentence listing key activities and primary deliverable>"
    }}
  ],
  "risk_assessment": [
    {{
      "risk": "<string: 3-6 word risk title>",
      "impact": "<string: exactly High, Medium, or Low>",
      "probability": "<string: exactly High, Medium, or Low>",
      "mitigation": "<string: one concrete, actionable mitigation step specific to {data.industry}>"
    }}
  ],
  "deliverables": ["<string: specific output or artifact name>"]
}}

HARD RULES (failure to follow = rejected output):
1. Return ONLY a raw JSON object. Zero markdown, zero code fences, zero commentary.
2. timeline: phases must sum to EXACTLY {total_weeks} weeks. Include 4-6 phases (Discovery, Design, Development, Testing, UAT, Deployment). Use realistic week distributions.
3. risk_assessment: EXACTLY 5 items. impact and probability each must be exactly: High, Medium, or Low.
4. deliverables: EXACTLY 6 short strings. Concrete artifact names only (e.g. "Deployed Production System", "API Documentation", "User Training Guide").
5. Do NOT include any cost or budget numbers - computed separately.
6. No markdown formatting inside any JSON string values. No **, ##, backticks, bullet dashes.
7. Language: professional, industry-specific, precise. Match {data.industry} terminology as of 2026.
8. executive_summary MUST mention at least one specific metric or KPI.
9. technical_approach MUST name at least 2 technologies from: {tech_csv}.
10. All string values: single plain paragraph. No embedded lists, no newlines inside string values.

OUTPUT (raw JSON only, starting with open brace):"""


def build_edit_prompt(
    original_data: dict,
    current_sections: dict,
    edit_instruction: str,
) -> str:
    """Build a context-aware edit prompt so the AI understands what to change."""
    tech_csv  = ", ".join(original_data.get("tech_stack", []))
    total_weeks = original_data.get("duration_months", 1) * 4
    # Compact JSON of the current sections for context (truncate very long values)
    context_lines = []
    for key, val in current_sections.items():
        if isinstance(val, str):
            context_lines.append(f'  "{key}": "{val[:300]}..."')
        elif isinstance(val, list):
            context_lines.append(f'  "{key}": [... {len(val)} items ...]')
        else:
            context_lines.append(f'  "{key}": <...>')
    context_str = "{\n" + ",\n".join(context_lines) + "\n}"

    safe_instruction = _sanitize(edit_instruction)

    return f"""You are a senior consulting solution architect. You are editing a professional proposal.
Today's date is February 2026.

ORIGINAL PROPOSAL CONTEXT:
- Project: {original_data.get('project_title', '')}
- Industry: {original_data.get('industry', '')}
- Duration: {original_data.get('duration_months', '')} months ({total_weeks} weeks)
- Users: {original_data.get('expected_users', 0):,}
- Tech Stack: {tech_csv}

CURRENT PROPOSAL SECTIONS (abbreviated):
{context_str}

USER EDIT INSTRUCTION:
"{safe_instruction}"

TASK: Apply the user's edit instruction to the proposal. Understand the intent:
- If the instruction says "remove X", remove or significantly reduce that element.
- If it says "add X" or "include X", add that element with relevant detail.
- If it says "replace X with Y", make that substitution.
- If it says "make it more detailed / shorter / formal", adjust the tone/length.
- Preserve all sections that are not affected by the edit.
- Keep all content accurate for the {original_data.get('industry', '')} industry in 2026.

Return the COMPLETE updated proposal as a SINGLE JSON object with the same schema:
{{
  "executive_summary": "<updated string>",
  "technical_approach": "<updated string>",
  "timeline": [{{ "phase": "<str>", "weeks": <int>, "description": "<str>" }}],
  "risk_assessment": [{{ "risk": "<str>", "impact": "<High|Medium|Low>", "probability": "<High|Medium|Low>", "mitigation": "<str>" }}],
  "deliverables": ["<str>"]
}}

RULES:
1. Raw JSON only. No markdown, no code fences.
2. timeline weeks must still sum to EXACTLY {total_weeks}.
3. risk_assessment must still have EXACTLY 5 items.
4. deliverables must still have EXACTLY 6 items.
5. No cost or budget numbers.
6. No markdown formatting inside string values.

OUTPUT (raw JSON only):"""
