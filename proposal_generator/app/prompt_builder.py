"""Build a structured prompt that forces the LLM to return strict JSON."""


def build_prompt(data) -> str:
    """Build a strict JSON-only prompt with anti-hallucination guardrails.

    The prompt is deliberately precise about expected format, data types,
    and constraints to minimise LLM improvisation.
    """
    total_weeks = data.duration_months * 4
    tech_csv = ", ".join(data.tech_stack)

    return f"""You are a senior consulting solution architect.

TASK: Produce a JSON object for a project proposal.

PROJECT DETAILS:
- Title: {data.project_title}
- Industry: {data.industry}
- Duration: {data.duration_months} months ({total_weeks} weeks)
- Expected End-Users: {data.expected_users:,}
- Tech Stack: {tech_csv}

REQUIRED JSON SCHEMA (return EXACTLY this structure):
{{
  "executive_summary": "<string: 2-3 factual sentences about scope, goals, and expected business value>",
  "technical_approach": "<string: 2-3 sentences about system architecture, database choice, caching layer, deployment strategy suitable for {data.industry}>",
  "timeline": [
    {{
      "phase": "<string: phase name>",
      "weeks": <integer>,
      "description": "<string: one sentence describing activities>"
    }}
  ],
  "risk_assessment": [
    {{
      "risk": "<string: short risk title>",
      "impact": "<string: exactly one of High, Medium, Low>",
      "mitigation": "<string: one sentence mitigation>"
    }}
  ],
  "deliverables": ["<string>"]
}}

HARD RULES:
1. Return ONLY a raw JSON object. No markdown, no code fences, no text before or after the JSON.
2. timeline must have 4-6 phases whose "weeks" values sum to EXACTLY {total_weeks}.
3. risk_assessment must have EXACTLY 4 items. "impact" must be one of: "High", "Medium", "Low".
4. deliverables must be an array of 4-6 short strings.
5. Do NOT invent cost/budget numbers — cost is computed separately.
6. Do NOT use markdown formatting (**, ##, ```) inside any value.
7. Do NOT exaggerate. Keep language professional, realistic, and factual.
8. All descriptions must be relevant to the {data.industry} industry.
9. Do NOT repeat project details verbatim in the summary; synthesise them.
10. Every JSON string value must be plain text — no bullet points, no lists inside strings.

OUTPUT:"""
