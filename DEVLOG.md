# Development Log — SJ Project Planner Agent

**Hackathon:** Microsoft Code Without Barriers 2026 (ID8NXT)
**Challenge:** SJ Project Planner Agent
**Participant:** moralessam32 (solo submission)
**Deadline:** 2026-05-03, 11:59 PM SGT
**Built:** 2026-05-01 to 2026-05-02

---

## What We Built

A full-stack agentic AI assistant that converts unstructured meeting notes, emails, and project conversations into structured, auditable plan updates — with a human-in-the-loop approval workflow at its core.

**Live demo:** _see README.md_
**GitHub:** https://github.com/SamMorales-stack/CWB_Project

---

## Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| UI framework | Streamlit | Fastest path to a working 5-page app with filters, charts, and forms |
| LLM provider | OpenCode Go (DeepSeek V4) | Azure OpenAI blocked by student subscription quota; Gemini free tier restricted for Pro accounts; OpenCode Go has generous paid-tier access |
| Database | Azure PostgreSQL Flexible Server (B1ms) | Required by hackathon Azure-cloud rule; fits within $100 student credits |
| Deployment | Azure Container Apps | Single-container deploy, public HTTPS URL, scales to zero |
| Agent pattern | Single orchestrator + 4 tools | Lean enough to build in 2 days solo; avoids multi-agent debugging overhead |
| Structured output | JSON-mode via OpenAI-compatible SDK | Works across all providers (Azure OpenAI, Gemini, Groq, OpenCode) |

---

## LLM Provider Journey

The app was designed for Azure OpenAI but the Azure for Students subscription blocked model deployment in every available region due to subscription policy restrictions. We cycled through:

1. **Azure OpenAI** → `InvalidTemplateDeployment` in all regions (East US 2, Sweden Central, Japan East, East Asia)
2. **Google Gemini (AI Studio)** → Free tier quota set to 0 for Google One Pro accounts
3. **Groq (Llama 3.3 70B)** → Code prepared but user preferred to try Gemini models first
4. **Gemini 3.1 Flash Lite Preview** → Same quota wall (Pro account restriction)
5. **OpenCode Go (DeepSeek V4)** → ✅ Working — OpenAI-compatible endpoint, generous limits

All providers use the same 2-line code change (base_url + api_key) thanks to the OpenAI-SDK-compatible abstraction in `planner/agent/client.py`.

---

## Key Features Implemented

### Basic Functions (all required)
- ✅ Extract tasks, owners, due dates, status signals from meeting notes
- ✅ Structured tracker with consistent schema (title, owner, due_date, status, priority, source, confidence)
- ✅ Three-way classification: NEW task / UPDATE existing / CONFLICT requiring clarification
- ✅ Plan Update Draft with evidence quotes from source text
- ✅ Dashboard with tracker table, Gantt chart, urgent tasks panel

### Advanced Functions
- ✅ Human-in-the-loop approval workflow (approve/reject/edit per change, bulk actions)
- ✅ First-class conflict resolution (side-by-side candidate comparison, Merge / Keep Separate)

### Innovation Features
- ✅ Confidence-driven UX (high-confidence changes pre-checked, low-confidence flagged red)
- ✅ Evidence-quote pinning — every plan change traceable to the exact source sentence
- ✅ Weekly executive digest (one-click summary of the last 7 days of plan changes)

---

## Dataset

Uses the official CWB_SJ dataset (CC0 license) from https://github.com/DoreenSteven/CWB_SJ:
- `tasks_master.csv` → loaded as the baseline plan (~50 tasks)
- `meeting_notes.jsonl` → first 10 notes available for processing
- `emails.csv` → first 5 emails available for processing

---

## Commit History Summary

| Phase | Tasks | Commits |
|---|---|---|
| Design & planning | Spec + implementation plan | 2 |
| Foundation | Scaffold, settings, DB engine, models, Alembic, CI | 6 |
| Repository layer | 4 repos (TDD), conftest, fixtures | 7 |
| Agent foundation | Schemas, client, prompts | 3 |
| Agent tools | extract, classify, draft, summarize (TDD) | 5 |
| Orchestration | Matcher, PlannerAgent, PlannerService | 3 |
| UI | App skeleton + 5 pages | 8 |
| Dataset & deployment | Sample loader, Dockerfile, deploy script | 3 |
| Polish & fixes | Tracker bug fix, conflict UI improvement | 2 |
| LLM provider switches | Azure → Gemini → OpenCode | 4 |
| **Total** | | **~45 commits** |

---

## AI Tool Usage Disclosure

Per hackathon rules, this submission was built with:

- **Claude Code (Anthropic, claude-sonnet-4-6)** — primary development collaborator. Used for: architecture design, implementation planning, code generation across all layers (models, repositories, agent tools, Streamlit UI, deployment scripts), bug fixing, and documentation. The design spec (`docs/superpowers/specs/`) and implementation plan (`docs/superpowers/plans/`) were collaboratively produced.
- **OpenCode Go / DeepSeek V4 Pro** — runs inside the application as the LLM powering all four agent tools (extract, classify, draft, digest).

No third-party AI-generated assets contain sensitive, confidential, or proprietary information. All code was developed during the hackathon period (April 2 – May 3, 2026).
