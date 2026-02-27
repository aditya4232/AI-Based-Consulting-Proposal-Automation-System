import re
import json
import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
API_KEY = "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"

# Keys we always expect in the parsed result.
# timeline, risk_assessment, and deliverables can be structured (list/dict).
EXPECTED_KEYS = [
    "executive_summary",
    "technical_approach",
    "timeline",
    "risk_assessment",
    "deliverables",
]


def _clean_text(text: str) -> str:
    """Remove markdown formatting and special characters from a plain-text value."""
    text = re.sub(r'\*{1,3}', '', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = text.replace('`', '')
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _clean_value(value):
    """Recursively clean strings inside nested structures."""
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, dict):
        return {k: _clean_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean_value(item) for item in value]
    return value


def _flatten_for_display(value) -> str:
    """Convert dicts/lists into a human-readable string (fallback for API response)."""
    if isinstance(value, dict):
        parts = [f"{k}: {v}" for k, v in value.items()]
        return ". ".join(parts) + "."
    if isinstance(value, list):
        items = []
        for item in value:
            if isinstance(item, dict):
                items.append(", ".join(f"{k}: {v}" for k, v in item.items()))
            else:
                items.append(str(item))
        return ". ".join(items) + "."
    return str(value)


def _extract_json(raw: str) -> dict | None:
    """Try to extract a JSON object from the raw LLM response."""
    raw = re.sub(r'```(?:json)?\s*', '', raw)
    raw = raw.replace('```', '')

    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def generate_proposal(prompt: str) -> dict:
    """Call Groq API and return a structured proposal dict.

    Returns a dict with keys matching EXPECTED_KEYS.
    Structured fields (timeline, risk_assessment, deliverables) are preserved
    as lists/dicts when the LLM returns valid JSON; otherwise they fall back
    to cleaned text strings.
    """
    try:
        response = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 2000,
                "stream": False,
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        raw_content = ""
        if "choices" in data and data["choices"]:
            raw_content = data["choices"][0]["message"]["content"]
        else:
            raw_content = str(data)

        parsed = _extract_json(raw_content)
        if parsed:
            result = {}
            for k in EXPECTED_KEYS:
                val = parsed.get(k, "N/A")
                result[k] = _clean_value(val)
            return result

        # Fallback: parsing failed, return cleaned text for every key
        cleaned = _clean_text(raw_content)
        return {k: cleaned for k in EXPECTED_KEYS}

    except requests.exceptions.HTTPError as e:
        error_msg = f"API Error [{e.response.status_code}]: {e.response.text}"
        return {k: error_msg for k in EXPECTED_KEYS}
    except Exception as e:
        error_msg = f"Error connecting to AI API: {str(e)}"
        return {k: error_msg for k in EXPECTED_KEYS}
