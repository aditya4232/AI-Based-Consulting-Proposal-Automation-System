def build_prompt(data):
    """Build a strict JSON-only prompt that returns structured data for tables and charts."""
    return f"""You are a senior consulting solution architect who writes concise, professional project proposals.

Based on the following project details, produce a JSON object with exactly these keys:

1. "executive_summary" (string): A 2-3 sentence summary of the project scope, goals, and expected business value.

2. "technical_approach" (string): A 2-3 sentence description of the system architecture and key technology choices. Mention the database, caching, and deployment strategy appropriate for the industry.

3. "timeline" (array of objects): Each object must have:
   - "phase" (string): Phase name, e.g. "Requirements and Design"
   - "weeks" (integer): Number of weeks for this phase
   - "description" (string): One sentence describing this phase's activities

   The total weeks across all phases must equal exactly {data.duration_months * 4} weeks ({data.duration_months} months).

4. "risk_assessment" (array of objects): Provide exactly 3-4 risks. Each object must have:
   - "risk" (string): Short risk title
   - "impact" (string): one of "High", "Medium", or "Low"
   - "mitigation" (string): One sentence mitigation strategy

5. "deliverables" (array of strings): List of 4-6 key project deliverables.

Project Details:
- Project Title: {data.project_title}
- Industry: {data.industry}
- Duration: {data.duration_months} months ({data.duration_months * 4} weeks)
- Expected Users: {data.expected_users}
- Preferred Tech Stack: {', '.join(data.tech_stack)}

Rules:
- Return ONLY a valid JSON object. No markdown, no code fences, no extra text before or after.
- Do not include special characters like **, ##, or markdown formatting in any value.
- Keep language factual and professional. Do not exaggerate.
- The timeline weeks must sum to exactly {data.duration_months * 4}.
- Do not invent cost or budget numbers; cost is handled separately.
- Ensure risk impacts are realistic for the {data.industry} industry.

Output:"""
