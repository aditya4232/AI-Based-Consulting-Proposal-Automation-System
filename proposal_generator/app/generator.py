"""LLM proposal generation with provider support (Ollama default, Groq, OpenAI)."""

import re
import json
import time
import requests

from app.config import settings
from app.logger import get_logger

log = get_logger(__name__)

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

def _extract_json(raw: str) -> dict | None:
    """Try to extract a valid JSON object from the raw LLM response."""
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

def _validate_timeline(timeline: list, expected_weeks: int) -> list:
    """Ensure timeline phases sum to the expected total weeks."""
    if not isinstance(timeline, list) or not timeline:
        return timeline

    total = sum(p.get("weeks", 0) for p in timeline if isinstance(p, dict))
    if total == expected_weeks or total == 0:
        return timeline

    ratio = expected_weeks / total
    adjusted = []
    running = 0
    for i, phase in enumerate(timeline):
        if not isinstance(phase, dict):
            adjusted.append(phase)
            continue
        w = phase.get("weeks", 0)
        if i == len(timeline) - 1:
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
#                     PROVIDER IMPLEMENTATIONS                             #
# ====================================================================== #

def _get_active_ollama_model(base_url: str) -> str:
    """Fetch the first available LOCAL model from Ollama (skip cloud models)."""
    try:
        url = base_url.rstrip("/") + "/api/tags"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        # Filter out cloud models
        local_models = [m for m in models if ":cloud" not in m.get("name", "")]
        if local_models:
            return local_models[0]["name"]
        if models:
            log.warning("Only cloud models available, using first model: %s", models[0]["name"])
            return models[0]["name"]
    except Exception as e:
        log.warning("Could not automatically detect Ollama model: %s", e)
    return "llama3"


def _call_ollama(prompt: str, custom_url: str = None, custom_model: str = None) -> str:
    """Call local Ollama strictly for JSON generation."""
    base_url = custom_url or "http://localhost:11434"
    model = custom_model or _get_active_ollama_model(base_url)
    url = base_url.rstrip("/") + "/api/generate"
    
    log.info("Calling Ollama (Model: %s) at %s", model, url)
    
    payload = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": settings.groq_temperature,
        }
    }
    
    response = requests.post(url, json=payload, timeout=settings.groq_timeout * 2)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def _call_openai_compatible(prompt: str, url: str, api_key: str, model: str) -> str:
    """Call an OpenAI-compatible /v1/chat/completions endpoint (like Groq or OpenAI)."""
    log.info("Calling OpenAI-compatible API at %s (Model: %s)", url, model)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": settings.groq_temperature,
        "max_tokens": settings.groq_max_tokens,
        "stream": False,
    }
    
    # Try requesting JSON mode if supported (may fail on some older models)
    try:
        # Check if the URL relates to a provider that strictly supports json_object (like Groq/OpenAI)
        payload["response_format"] = {"type": "json_object"}
    except Exception:
        pass
        
    last_error = None
    for attempt in range(1, settings.groq_max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=settings.groq_timeout)
            response.raise_for_status()
            data = response.json()
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
            return str(data)
        except requests.exceptions.HTTPError as e:
            last_error = e
            status = e.response.status_code if e.response else "?"
            log.warning("HTTP %s on attempt %d: %s", status, attempt, str(e)[:200])
            # If 400 Bad Request and we forced json_object, try again without it
            if status == 400 and "response_format" in payload:
                log.info("Retrying without response_format=json_object")
                del payload["response_format"]
                time.sleep(1)
                continue
                
            if status == 429 or status >= 500:
                time.sleep(2 ** attempt)
                continue
            raise
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            time.sleep(2 ** attempt)

    raise RuntimeError(f"API call failed after {settings.groq_max_retries} attempts: {last_error}")


def _call_llm(prompt: str, provider: str, model: str, api_key: str, api_url: str) -> str:
    """Route to the correct provider implementation."""
    provider = provider.lower().strip() if provider else "ollama"
    
    if provider == "ollama":
        return _call_ollama(prompt, custom_url=api_url, custom_model=model)
        
    # Groq fallback
    if provider == "groq":
        url = api_url or settings.groq_api_url
        key = api_key or settings.groq_api_key
        mod = model or settings.groq_model
        return _call_openai_compatible(prompt, url, key, mod)
        
    # Generic OpenAI fallback
    if provider == "openai":
        url = api_url or "https://api.openai.com/v1/chat/completions"
        mod = model or "gpt-4o-mini"
        if not api_key:
            raise ValueError("API Key is required for OpenAI")
        return _call_openai_compatible(prompt, url, api_key, mod)
        
    raise ValueError(f"Unknown provider: {provider}")


# ====================================================================== #
#                     PUBLIC ENTRY POINT                                   #
# ====================================================================== #

def generate_proposal(prompt: str, expected_weeks: int = 0, provider_opts: dict = None) -> dict:
    """Call LLM and return a validated, structured proposal dict."""
    if not provider_opts:
        provider_opts = {}
        
    try:
        raw_content = _call_llm(
            prompt=prompt,
            provider=provider_opts.get("provider"),
            model=provider_opts.get("model"),
            api_key=provider_opts.get("api_key"),
            api_url=provider_opts.get("api_url"),
        )

        parsed = _extract_json(raw_content)
        if parsed:
            result = {}
            for k in EXPECTED_KEYS:
                val = parsed.get(k, "N/A")
                result[k] = _clean_value(val)

            if expected_weeks > 0 and isinstance(result.get("timeline"), list):
                result["timeline"] = _validate_timeline(result["timeline"], expected_weeks)
            if isinstance(result.get("risk_assessment"), list):
                result["risk_assessment"] = _validate_risk_impact(result["risk_assessment"])

            log.info("Proposal generated successfully with structured data")
            return result

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
