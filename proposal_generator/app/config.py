"""Centralized configuration management.

All secrets and tunables are loaded from environment variables
with sensible defaults for local development.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    # ---- Groq API ----
    groq_api_url: str = os.environ.get(
        "GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions"
    )
    groq_api_key: str = os.environ.get(
        "GROQ_API_KEY", "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"
    )
    groq_model: str = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
    groq_temperature: float = float(os.environ.get("GROQ_TEMPERATURE", "0.05"))
    groq_max_tokens: int = int(os.environ.get("GROQ_MAX_TOKENS", "2500"))
    groq_timeout: int = int(os.environ.get("GROQ_TIMEOUT", "45"))
    groq_max_retries: int = int(os.environ.get("GROQ_MAX_RETRIES", "3"))

    # ---- Output ----
    output_dir: str = os.environ.get("OUTPUT_DIR", os.path.join(os.getcwd(), "outputs"))

    # ---- CORS ----
    cors_origins: list[str] = field(
        default_factory=lambda: os.environ.get(
            "CORS_ORIGINS", "*"
        ).split(",")
    )

    # ---- App ----
    app_title: str = "AI Proposal Generator"
    app_version: str = "2.0.0"
    debug: bool = os.environ.get("DEBUG", "0") == "1"


# Singleton
settings = Settings()
