# SJ Project Planner Agent

> Agentic AI assistant that converts unstructured project conversations into structured, auditable plan updates — with a human-in-the-loop approval workflow.

**Microsoft Code Without Barriers Hackathon 2026** · Challenge: SJ Project Planner Agent · Solo submission

---

## Live Demo

🔗 **https://sjplanner-sm2026.calmbush-865eff5f.eastasia.azurecontainerapps.io/**

## Pitch Video

🎬 **[YouTube URL — to be added after recording]**

---

## What it does

Project plans drift out of sync with reality because decisions made in meetings and emails never make it back into the official tracker. This assistant:

1. **Ingests** a meeting note, email, or chat message via the Inbox
2. **Extracts** task-shaped items — title, owner, due date, status, dependencies, and an evidence quote from the exact source sentence
3. **Classifies** each item as a brand-new task, an update to an existing task, or a conflict requiring human clarification
4. **Drafts** a structured plan-update proposal with an executive-friendly summary
5. **Presents** the draft to a human reviewer who approves, rejects, or edits each change
6. **Commits** approved changes atomically, recording a full before/after audit trail

Nothing reaches the official tracker without explicit human approval.

---

## Key Features

### Basic Functions
- **Meeting-to-plan translation** — extract tasks, owners, due dates, status signals, and dependency hints from natural-language notes and emails
- **Structured tracker** — consistent schema: title, owner, due date, status, priority, source, confidence
- **Three-way classification** — NEW task / UPDATE existing / CONFLICT requiring clarification
- **Plan Update Draft** — every proposed change paired with the verbatim evidence quote from the source
- **Tracker + Gantt + Urgent panel** — filterable table with overdue/due-soon colour cues, Plotly Gantt timeline coloured by status

### Advanced Functions
- **Human-in-the-loop approval** — per-change approve/reject/edit controls, bulk approve/reject, apply decisions atomically
- **First-class conflict resolution** — side-by-side candidate comparison with Merge / Keep Separate

### Innovation Features
- **Confidence-driven UX** — high-confidence changes pre-checked; low-confidence flagged red and requiring explicit action
- **Evidence-quote pinning** — every applied plan change traceable to the exact source sentence in the meeting note
- **Weekly executive digest** — one-click agent summary of the last 7 days of plan changes for stakeholder reporting

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Streamlit Web App (Azure Container Apps)    │
│   Pages: Inbox · Drafts · Tracker · Gantt · Change Log  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│                    PlannerService                        │
│   ingest_note · run_pipeline · apply_draft · digest      │
└──────────┬──────────────────────────────┬───────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐    ┌─────────────────────────────┐
│  PlannerAgent        │    │  Repository layer            │
│  extract_tasks       │    │  meeting_notes · tasks       │
│  classify_change     │    │  pending_drafts · change_log │
│  generate_draft      │    └────────────────┬────────────┘
│  summarize_changes   │                     │
└──────────┬───────────┘                     ▼
           │                    ┌────────────────────────┐
           ▼                    │ Azure Database for      │
┌──────────────────────┐        │ PostgreSQL (Flexible)   │
│  OpenCode Go API     │        └────────────────────────┘
│  DeepSeek V4 Pro     │
│  (OpenAI-compatible) │
└──────────────────────┘
```

**Four layers with strict one-way dependencies:**
- **UI** — pure presentation, no business logic
- **PlannerService** — owns the workflow
- **PlannerAgent** — four LLM-backed tools with Pydantic-validated structured outputs
- **Repository layer** — typed CRUD over four PostgreSQL tables

Full design specification: [`docs/superpowers/specs/2026-05-01-sj-project-planner-agent-design.md`](docs/superpowers/specs/2026-05-01-sj-project-planner-agent-design.md)

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | OpenCode Go (DeepSeek V4 Pro/Flash) via OpenAI-compatible API |
| Storage | Azure Database for PostgreSQL Flexible Server (SQLAlchemy 2 + Alembic) |
| UI | Streamlit + Plotly |
| Deployment | Azure Container Apps + Azure Container Registry |
| Language | Python 3.12 |
| Testing | pytest (unit tests with mocked LLM + live integration tests) |
| CI | GitHub Actions (ruff + pytest on every push) |

---

## Dataset

Uses the official **CWB_SJ dataset** (CC0 license) from [github.com/DoreenSteven/CWB_SJ](https://github.com/DoreenSteven/CWB_SJ):
- `tasks_master.csv` → loaded as the baseline plan
- `meeting_notes.jsonl` → first 10 notes available to process through the agent
- `emails.csv` → first 5 emails available as email-type meeting notes

Click **Load sample dataset** in the sidebar to populate the app instantly for demo purposes.

---

## Run Locally

**Prerequisites:** Python 3.12, Docker Desktop, an OpenCode Go API key from [opencode.ai](https://opencode.ai)

```bash
# 1. Clone
git clone https://github.com/SamMorales-stack/CWB_Project.git
cd CWB_Project

# 2. Start local Postgres
docker compose up -d postgres

# 3. Python environment
python -m venv .venv
source .venv/Scripts/activate    # Git Bash on Windows
pip install -e ".[dev]"

# 4. Configure
cp .env.example .env
# Edit .env: set OPENCODE_API_KEY and DATABASE_URL

# 5. Run migrations
python -m alembic upgrade head

# 6. Launch
streamlit run src/planner/ui/app.py
```

Open http://localhost:8501, click **Load sample dataset** in the sidebar, then go to Inbox to process a meeting note.

---

## Deploy to Azure

Requires Azure CLI (`az login`) and an Azure subscription with Container Apps access.

```bash
export APP_NAME="sjplanner-<your-suffix>"   # globally unique
export LOCATION="eastasia"                  # match your subscription's allowed regions
export OPENCODE_API_KEY="your-opencode-key"
export PG_ADMIN_PASSWORD="A-strong-password-123!"

./infra/deploy.sh
```

The script provisions a resource group, ACR, PostgreSQL Flexible Server, Container Apps environment, and the app. Prints the live URL on completion.

---

## Tests

```bash
# Unit tests (mocked LLM, requires Postgres running)
python -m pytest -m "not live" -v

# Live integration tests (real LLM calls, small cost)
python -m pytest -m live -v
```

---

## AI Tool Usage Disclosure

Per the hackathon's Generative AI Tools policy, this submission used:

- **Claude Code (Anthropic, claude-sonnet-4-6)** — architecture design, implementation planning, and code generation throughout the project. See [`DEVLOG.md`](DEVLOG.md) for a full account of the development process.
- **OpenCode Go / DeepSeek V4 Pro** — the LLM powering the application's four agent tools at runtime.

No AI-generated assets contain sensitive, confidential, or proprietary information. All code was developed during the hackathon period (2 April – 3 May 2026).
