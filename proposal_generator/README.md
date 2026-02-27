# AI Proposal Generator 🚀

An AI-based consulting proposal automation tool using FastAPI, Ollama Cloud API, and deterministic cost logic.

It helps pre-sales teams and solution architects draft enterprise proposals faster by combining Generative AI with structured deterministic logic for real-world constraints like cost estimation.

## Setup

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python -m uvicorn app.main:app --reload
```

## Features

1. **Generative Drafts**: LLMs create an initial Executive Summary, Tech Approach, Timeline, and Risk Assessment.
2. **Deterministic Rules**: Cost logic calculates exact infrastructure and resource estimates (no hallucinated rates).
3. **Structured Schemas**: Strong type validation ensures inputs conform to the business model context.
