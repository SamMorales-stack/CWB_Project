# Pitch Video Script — SJ Project Planner Agent
## Target: 5 minutes | Delivered in English | Cover all judging criteria

---

### 0:00–0:30 — Hook + Problem

> "Project plans fall out of sync with reality — not because teams don't know what's happening,
> but because the decisions made in meetings and emails never make it back into the official tracker.
> Owners change. Deadlines shift. New tasks get agreed. And unless someone manually updates the plan,
> those decisions are invisible to everyone else.
>
> This is the SJ Project Planner Agent — an agentic AI that translates unstructured conversations
> into structured, auditable plan updates, while keeping a human firmly in control."

*(Show: a messy meeting-notes document next to a stale Gantt chart)*

---

### 0:30–1:00 — What it does in one sentence

> "Paste a meeting note. The agent extracts the tasks, owners, and dates discussed,
> compares them to the current plan, and proposes an update — never applies it silently.
> A human reviews each proposed change, approves, rejects, or resolves conflicts,
> and only then does the plan update."

*(Show: end-to-end flow diagram from docs/architecture.md)*

---

### 1:00–2:30 — Live demo (screen capture)

> "Here's the application running live.
>
> I'll click 'Load sample dataset' — this loads the official CWB_SJ dataset:
> the baseline plan from tasks_master.csv and 10 meeting notes from the project.
>
> The Tracker shows the baseline plan — 50+ tasks, owners, due dates, status, priorities.
> The Gantt gives us the visual timeline.
>
> Now let's process a meeting note. I'll go to Inbox, paste the notes from the
> 'Risk and Actions Review' meeting — the agent extracts what was discussed, runs
> classification to match items against the existing plan, and generates a draft.
>
> Opening the Drafts page. Three proposed changes:
> One is high-confidence — the agent is sure this is an update to an existing task.
> It's pre-checked for approval — that's our confidence-driven UX, reducing reviewer fatigue.
>
> One is low-confidence — flagged in red, requires an explicit click.
>
> One is a conflict — the agent found two candidate matching tasks and isn't sure which one.
> I get a side-by-side view: the agent's proposed item versus each candidate.
> I click Merge — the conflict is resolved.
>
> I click Apply Decisions. The plan updates atomically.
>
> Tracker now reflects the changes. Gantt updates. And in Change Log — every applied change
> with before/after snapshots and the exact quote from the source note that drove it.
> Every plan edit is traceable back to the meeting that created it.
>
> One click on 'Generate weekly digest' — the agent summarises the last seven days
> of changes into an executive-friendly report."

---

### 2:30–3:30 — Architecture

> "Under the hood: one container deployed to Azure Container Apps.
>
> Azure OpenAI powers the agent — GPT-4o for drafting and classification,
> GPT-4o-mini for extraction. Azure Database for PostgreSQL is the plan store.
>
> The application is built in four clean layers:
> Streamlit UI — presentation only, no business logic.
> PlannerService — owns the workflow.
> PlannerAgent — the four LLM-backed tools: extract, classify, draft, digest.
> Repository layer — typed CRUD over the four planner tables.
>
> Strict one-way dependencies. Each layer is independently testable.
> Every applied change is transactional — partial updates don't happen.
> Every change carries the evidence quote from the source text."

*(Show: architecture diagram — two minutes to let judges read it)*

---

### 3:30–4:30 — Judging criteria alignment

> "Technical Merit — clean four-layer architecture, Pydantic-validated structured
> LLM outputs, transactional commits with full audit logging, ruff + mypy + pytest
> CI on every commit.
>
> Innovation — confidence-driven approval UX, first-class conflict resolution with
> side-by-side merge/keep-separate, and evidence-quote pinning: every plan change
> points back to the exact sentence that drove it.
>
> Potential Impact — this directly solves what the problem statement describes:
> plans drift from reality because meeting-to-plan translation is manual.
> The audit trail and human-in-the-loop approval mean governance is maintained
> without replacing project controls.
>
> Feasibility — runs on Azure free-tier resources. One-command deploy via Azure
> Container Apps. Lightweight enough for a solo PM, structured enough for a PMO."

---

### 4:30–5:00 — Close

> "The repository, README, and architecture diagram are in the GitHub link below.
> The live demo is at the URL in the description.
>
> Built for the Microsoft Code Without Barriers Hackathon 2026.
> Azure OpenAI and Claude Code were used as development tools — both are disclosed
> in the README per the hackathon's Generative AI policy.
>
> Thank you."

---

## Recording notes

- **Tool:** OBS Studio (free) or Windows Game Bar (Win+G → Record)
- **Capture:** Full screen + microphone
- **Target:** 5:00 ± 15 seconds
- **Before recording:** load sample data, approve one draft so Tracker + Change Log are populated
- **Upload:** YouTube → Unlisted → paste URL into README and submission form
