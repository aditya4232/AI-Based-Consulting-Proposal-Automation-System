"""LLM proposal generation with retry logic, validation, and anti-hallucination post-processing."""

import re
import json
import time
import requests

from app.config import settings
from app.logger import get_logger

log = get_logger(__name__)

# Keys we always expect in the parsed result.
EXPECTED_KEYS = [
    "executive_summary",
    "technical_approach",
    "timeline",
    "risk_assessment",
    "deliverables",
]


# ====================================================================== #
#                        TEXT CLEANING                                     #
# ====================================================================== #

def _clean_text(text: str) -> str:
    """Remove markdown formatting and special characters from plain text."""
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


# ====================================================================== #
#                        JSON EXTRACTION                                   #
# ====================================================================== #

def _extract_json(raw: str) -> dict | None:
    """Try to extract a valid JSON object from the raw LLM response.

    1. Strip code-fence markers.
    2. Try direct parse.
    3. Try regex extraction of outermost { ... }.
    """
    raw = re.sub(r'```(?:json)?\s*', '', raw)
    raw = raw.replace('```', '').strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


# ====================================================================== #
#                     POST-PROCESSING / VALIDATION                         #
# ====================================================================== #

def _validate_timeline(timeline: list, expected_weeks: int) -> list:
    """Ensure timeline phases sum to the expected total weeks.

    If the LLM gets the total wrong we proportionally adjust so the output
    is always deterministic and correct.
    """
    if not isinstance(timeline, list) or not timeline:
        return timeline

    total = sum(p.get("weeks", 0) for p in timeline if isinstance(p, dict))
    if total == expected_weeks or total == 0:
        return timeline

    # Proportionally rescale
    ratio = expected_weeks / total
    adjusted = []
    running = 0
    for i, phase in enumerate(timeline):
        if not isinstance(phase, dict):
            adjusted.append(phase)
            continue
        w = phase.get("weeks", 0)
        if i == len(timeline) - 1:
            # last phase absorbs remainder
            new_w = expected_weeks - running
        else:
            new_w = max(1, round(w * ratio))
            running += new_w
        adjusted.append({**phase, "weeks": new_w})
    return adjusted


def _validate_risk_impact(risks: list) -> list:
    """Normalise impact labels to one of High / Medium / Low."""
    valid = {"high", "medium", "low"}
    if not isinstance(risks, list):
        return risks
    result = []
    for r in risks:
        if not isinstance(r, dict):
            result.append(r)
            continue
        impact = str(r.get("impact", "Medium")).strip().lower()
        if impact not in valid:
            impact = "medium"
        r["impact"] = impact.capitalize()
        result.append(r)
    return result


# ====================================================================== #
#                     API CALL WITH RETRIES                                #
# ====================================================================== #

def _call_groq_api(prompt: str) -> str:
    """Call the Groq API with exponential backoff retry."""
    last_error = None
    for attempt in range(1, settings.groq_max_retries + 1):
        try:
            log.info("Groq API call attempt %d/%d", attempt, settings.groq_max_retries)
            response = requests.post(
                settings.groq_api_url,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": settings.groq_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": settings.groq_temperature,
                    "max_tokens": settings.groq_max_tokens,
                    "stream": False,
                },
                timeout=settings.groq_timeout,
            )
            response.raise_for_status()

            data = response.json()
            if "choices" in data and data["choices"]:
                content = data["choices"][0]["message"]["content"]
                log.info("Groq API returned %d chars", len(content))
                return content

            log.warning("Groq response had no choices: %s", str(data)[:200])
            return str(data)

        except requests.exceptions.HTTPError as e:
            last_error = e
            status = e.response.status_code if e.response is not None else "?"
            log.warning("Groq HTTP %s on attempt %d: %s", status, attempt, str(e)[:200])
            if status == 429:
                # rate limited — wait longer
                time.sleep(2 ** attempt)
                continue
            if status and int(str(status)) >= 500:
                time.sleep(1.5 ** attempt)
                continue
            raise
        except requests.exceptions.Timeout:
            last_error = TimeoutError("Groq API timeout")
            log.warning("Timeout on attempt %d", attempt)
            time.sleep(1.5 ** attempt)
        except requests.exceptions.ConnectionError as e:
            last_error = e
            log.warning("Connection error on attempt %d: %s", attempt, str(e)[:100])
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Groq API failed after {settings.groq_max_retries} attempts: {last_error}")


# ====================================================================== #
#                     PUBLIC ENTRY POINT                                    #
# ====================================================================== #

def generate_proposal(prompt: str, expected_weeks: int = 0) -> dict:
    """Call Groq API and return a validated, structured proposal dict.

    Parameters
    ----------
    prompt : str
        The prompt constructed by `build_prompt()`.
    expected_weeks : int
        If > 0, the timeline phases are validated / rescaled to sum to this.

    Returns
    -------
    dict with keys matching `EXPECTED_KEYS`.
    """
    try:
        raw_content = _call_groq_api(prompt)

        parsed = _extract_json(raw_content)
        if parsed:
            result = {}
            for k in EXPECTED_KEYS:
                val = parsed.get(k, "N/A")
                result[k] = _clean_value(val)

            # Post-validation
            if expected_weeks > 0 and isinstance(result.get("timeline"), list):
                result["timeline"] = _validate_timeline(result["timeline"], expected_weeks)

            if isinstance(result.get("risk_assessment"), list):
                result["risk_assessment"] = _validate_risk_impact(result["risk_assessment"])

            log.info("Proposal generated successfully with structured data")
            return result

        # Fallback: JSON parsing failed — return cleaned text
        log.warning("JSON extraction failed, falling back to raw text")
        cleaned = _clean_text(raw_content)
        return {k: cleaned for k in EXPECTED_KEYS}

    except RuntimeError as e:
        error_msg = str(e)
        log.error("Proposal generation failed: %s", error_msg)
        return {k: error_msg for k in EXPECTED_KEYS}
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        body = e.response.text[:300] if e.response is not None else ""
        error_msg = f"API Error [{status}]: {body}"
        log.error(error_msg)
        return {k: error_msg for k in EXPECTED_KEYS}
    except Exception as e:
        error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
        log.error(error_msg)
        return {k: error_msg for k in EXPECTED_KEYS}
