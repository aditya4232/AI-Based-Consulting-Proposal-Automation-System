<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" />
  <img src="https://img.shields.io/badge/Groq-F55036?style=for-the-badge&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
</p>

<h1 align="center">📄 AI-Based Consulting Proposal Automation System</h1>

<p align="center">
  <b>Generate professional, PDF-ready consulting proposals in minutes — powered by AI + deterministic cost logic.</b>
</p>

<p align="center">
  <a href="https://huggingface.co/spaces/Aditya4232/ai-proposal-generator">🚀 Live Demo on Hugging Face</a>
</p>

---

## 🎯 What It Does

This tool helps **pre-sales teams, solution architects, and consultants** draft enterprise-grade proposals by combining:

- **Generative AI** (Ollama / Groq / OpenAI / Anthropic) — creates Executive Summary, Technical Approach, Timeline, and Risk Assessment
- **Deterministic Cost Logic** — calculates exact infrastructure & resource estimates with no hallucinated numbers
- **Professional PDF Output** — generates polished PDFs with tables, charts, and proper formatting

> No more spending hours writing proposals from scratch. Describe your project, and the AI drafts a comprehensive proposal you can edit, iterate, and download.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 **Magic Fill** | Describe a project in one line → AI auto-fills all fields |
| 📊 **Live Cost Preview** | Real-time INR cost estimate as you adjust duration & users |
| 📄 **PDF Generation** | Professional multi-page PDF with tables, pie charts & timeline |
| 🔄 **Iterate & Edit** | Refine any section with follow-up AI instructions |
| 📁 **Reference Upload** | Attach PDFs, Word, Excel files for AI context |
| 🌗 **Dark Mode** | Full dark theme support |
| 🔐 **Secure by Design** | API keys stay in your browser — never stored on the server |
| 🏗️ **Multi-Provider** | Ollama (local), Groq (free cloud), OpenAI, Anthropic |
| 📜 **Session History** | Track all generated proposals per device |
| ⚡ **Background Jobs** | Generate PDFs in background while you keep working |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  Frontend (HTML/JS)              │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │Dashboard │ │ Generate │ │  Settings/History │ │
│  └────┬─────┘ └────┬─────┘ └────────┬─────────┘ │
│       └─────────────┼────────────────┘           │
│                     ▼                            │
│           window.location.origin                 │
└─────────────────────┬───────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────┐
│              FastAPI Backend                      │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │  Generator  │ │ Cost Logic │ │ PDF Builder  │ │
│  │ (AI calls)  │ │(determin.) │ │(fpdf2+charts)│ │
│  └──────┬─────┘ └────────────┘ └──────────────┘ │
│         │                                        │
│  ┌──────▼─────┐  ┌───────────┐  ┌────────────┐  │
│  │Prompt      │  │  Schemas  │  │ Session DB │  │
│  │Builder     │  │ (Pydantic)│  │ (SQLite)   │  │
│  └────────────┘  └───────────┘  └────────────┘  │
└─────────────────────┬───────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐  ┌─────────┐  ┌──────────┐
   │ Ollama  │  │  Groq   │  │ OpenAI / │
   │ (Local) │  │ (Cloud) │  │Anthropic │
   └─────────┘  └─────────┘  └──────────┘
```

---

## 🚀 Quick Start (Local)

### Prerequisites

- **Python 3.11+**
- **Ollama** installed and running ([Download Ollama](https://ollama.com))
- A model pulled (e.g., `ollama pull llama3.2`)

### Installation

```bash
# Clone the repository
git clone https://github.com/aditya4232/AI-Based-Consulting-Proposal-Automation-System.git
cd AI-Based-Consulting-Proposal-Automation-System/proposal_generator

# Install dependencies
pip install -r requirements.txt

# Start the server
python -m uvicorn app.main:app --reload
```

Then open **http://localhost:8000** in your browser.

---

## ☁️ Cloud Deployment (Free)

The project is deployed on **Hugging Face Spaces** using Docker:

👉 **[Live Demo](https://huggingface.co/spaces/Aditya4232/ai-proposal-generator)**

> **Note:** Ollama is a local-only provider. The cloud version uses **Groq** (free, no credit card required) as the default AI provider. Get a free API key at [console.groq.com](https://console.groq.com).

---

## 📂 Project Structure

```
proposal_generator/
├── app/
│   ├── main.py              # FastAPI app, routes, static serving
│   ├── generator.py          # AI provider integration (Ollama/Groq/OpenAI/Anthropic)
│   ├── prompt_builder.py     # Dynamic prompt construction
│   ├── pdf_builder.py        # PDF generation with tables & charts
│   ├── cost_logic.py         # Deterministic cost estimation engine
│   ├── schemas.py            # Pydantic request/response models
│   ├── config.py             # App configuration
│   └── db.py                 # SQLite session & history management
├── frontend/
│   ├── index.html            # Main SPA interface
│   ├── instruction.html      # User guide
│   ├── css/style.css         # Custom styles
│   └── js/
│       ├── app.js            # Application logic
│       └── api.js            # API communication layer
├── prompts/
│   └── proposal_template.txt # Base prompt template
├── Dockerfile                # Docker config for HF Spaces
└── requirements.txt          # Python dependencies
```

---

## 🔐 Security

- **API keys are stored client-side only** (browser sessionStorage) — the server never persists them
- **HMAC device tokens** for session verification
- **SSRF protection** on Ollama endpoint URLs
- **CORS** configured for deployment safety
- No hardcoded secrets — all sensitive values via environment variables

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **Frontend** | Vanilla HTML/CSS/JS, Tailwind CSS (CDN), Lucide Icons |
| **AI Providers** | Ollama, Groq, OpenAI, Anthropic |
| **PDF Engine** | fpdf2, Matplotlib, Pillow |
| **Database** | SQLite (ephemeral on cloud) |
| **Deployment** | Docker, Hugging Face Spaces |
| **Charts** | Chart.js (frontend), Matplotlib (PDF) |

---

## 📊 Supported Proposal Sections

The AI generates comprehensive proposals covering:

1. **Executive Summary** — Project overview and business value
2. **Technical Approach** — Architecture, tools, methodology
3. **Project Timeline** — Phased milestones with Gantt-style visualization
4. **Cost Breakdown** — Development, infrastructure, contingency (deterministic)
5. **Team Composition** — Roles, headcount, and allocation
6. **Risk Assessment** — Identified risks with mitigation strategies
7. **Compliance** — HIPAA, GDPR, SOC2 requirements (if specified)

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is part of an internship at **ScriptBees** under **Aditya Shenvi**.

---

<p align="center">
  <b>Built with ❤️ by <a href="https://github.com/aditya4232">Aditya Shenvi</a></b>
</p>
