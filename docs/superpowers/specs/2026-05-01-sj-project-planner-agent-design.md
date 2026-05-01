# SJ Project Planner Agent — Design Specification

**Date:** 2026-05-01
**Project:** Microsoft Code Without Barriers Hackathon 2026 — SJ Project Planner Agent challenge
**Author:** moralessam32 (solo submission)
**Submission deadline:** 2026-05-03, 11:59 PM SGT

---

## 1. Problem and Goal

In complex delivery environments, project plans drift out of sync with reality because the "truth" of what changed lives in meetings, emails, and informal updates. Decisions are made — new tasks, owner changes, date shifts, priority moves — but unless someone manually updates the tracker, those decisions never reach the official schedule. The result is weak governance visibility, mismatched stakeholder expectations, and rework.

The goal of this project is to build a lightweight agentic AI assistant that converts unstructured project conversations into structured planning updates while keeping a human firmly in control of the final decisions. The agent reduces the manual effort of plan maintenance without replacing project controls or human judgment.

The ultimate outcome is a system that translates day-to-day delivery conversations into structured, auditable plan updates, improving schedule reliability and ownership clarity while reducing the manual project-controls burden.

## 2. Scope

This specification covers a Minimum Viable Product targeting the basic functions defined in the problem statement, plus two of the listed advanced functions (Human-in-the-loop approval and Clarification Workflow), plus three small innovation features that materially raise the Innovation and Creativity score without expanding the build timeline beyond what is feasible for a solo developer in roughly two and a half days.

### 2.1 In Scope (Basic Functions)

- Extract tasks, owners, due dates, status signals, and dependency cues from meeting notes and email-style content.
- Consolidate extracted items into a structured tracker with a consistent schema: task title, owner, due date, status, source, and confidence.
- Classify each extracted item as a new task, an update to an existing task, or a potential conflict requiring human clarification.
- Generate a "Plan Update Draft" for review, including the proposed changes and the supporting evidence quoted from the source text.
- Provide a simple output view including a tracker table, a Gantt-style timeline, an urgent-tasks panel, and a list of upcoming deadlines.

### 2.2 In Scope (Advanced Functions)

- **Human-in-the-loop approval workflow.** Every proposed plan change is staged in a pending draft. A human reviewer approves, rejects, or edits each change before it is written to the official plan. Nothing reaches the live tracker without explicit approval.
- **Clarification workflow for conflicts and ambiguities.** When the agent cannot confidently determine whether an extracted item is new or refers to an existing task, it surfaces the ambiguity as a first-class conflict in the draft. The reviewer is shown a side-by-side comparison and chooses to merge, keep separate, or edit.

### 2.3 In Scope (Innovation Features)

- **Confidence-driven approval UX.** High-confidence proposed changes are pre-checked for approval; low-confidence changes are visually flagged and require an explicit click. This reduces reviewer fatigue and surfaces uncertainty rather than hiding it.
- **First-class conflict resolution flow.** Conflicts are not buried in a list — they get a dedicated side-by-side resolution view that shows the agent's reasoning and the existing-task candidate.
- **Weekly executive digest.** A button on the Change Log page asks the agent to read the last seven days of applied changes and produce an executive-friendly markdown summary of what materially changed in the plan.

### 2.4 Out of Scope

- Replay-mode demo animation and bidirectional task-to-source traceability are deferred to Day 2 if time permits; they are not part of the committed scope.
- Vector search, semantic retrieval, and document-database storage are deliberately omitted — the dataset is small enough that direct prompt inclusion is faster and simpler.
- Multi-user concurrent editing, undo for approved changes, browser-compatibility testing, load testing, and Power Automate or Power BI integrations are out of scope for the hackathon submission.

## 3. Hackathon Constraints That Shape The Design

Several hackathon rules and judging criteria directly influence design choices and are recorded here so future revisions retain the original rationale:

- Submissions must use Azure Services exclusively for cloud-based functionality. This makes the cloud component choices (PostgreSQL, OpenAI, Container Apps) effectively mandatory rather than preferred.
- Repositories with single commits or incomplete histories may be disqualified. The build approach must produce frequent, small, conventional commits across the hackathon period.
- Judges may evaluate based solely on submission materials — text descriptions, images, and videos — without testing the application. The README, screenshots, architecture diagram, and five-minute pitch video carry as much weight as the running code.
- Technical Merit is the tie-breaker. Architectural clarity, clean boundaries, and well-documented design choices score directly here.
- The Final Submission requires a public GitHub repository, a README, a live working environment URL, and a five-minute YouTube pitch video in English. Day 3 morning and afternoon must be reserved for video recording and submission polish.

## 4. Architecture

### 4.1 High-Level Shape

The system is a single Streamlit web application running in an Azure Container App. The Streamlit process hosts a sidebar-navigated UI for five pages and embeds a `PlannerService` that orchestrates a `PlannerAgent` built on the Microsoft Agent Framework. The agent uses Azure OpenAI as its language model and reads and writes through a thin repository layer to an Azure Database for PostgreSQL Flexible Server instance.

```
+-----------------------------------------------------------------+
|              Streamlit Web App (Azure Container Apps)           |
|     Pages: Inbox | Drafts | Tracker | Gantt | Change Log        |
+----------------------------+------------------------------------+
                             |
                             v
+-----------------------------------------------------------------+
|                          PlannerService                         |
|  ingest_note  |  run_pipeline  |  apply_draft  |  weekly_digest |
+----------+----------------------------------------+-------------+
           |                                        |
           v                                        v
+----------------------------+         +-----------------------------+
|  PlannerAgent              |         |  Repository Layer           |
|  (Microsoft Agent          |         |  meeting_notes / tasks /    |
|   Framework)               |         |  pending_drafts /           |
|  tools: extract_tasks,     |         |  change_log                 |
|         classify_change,   |         +--------------+--------------+
|         generate_draft,    |                        |
|         summarize_changes  |                        v
+-------------+--------------+         +-----------------------------+
              |                        | Azure Database for          |
              v                        | PostgreSQL Flexible Server  |
+-----------------------------+        +-----------------------------+
| Azure OpenAI                |
| GPT-4o (drafting, digest)   |
| GPT-4o-mini (extraction)    |
+-----------------------------+
```

### 4.2 Components and Boundaries

The system is intentionally split into four units with strictly one-way dependencies. This separation keeps each unit small enough to reason about, individually testable, and replaceable.

**Streamlit UI.** Pure presentation and user input. Imports nothing from the agent layer directly. Calls into `PlannerService` via plain Python function calls. Holds no business logic — every decision about what to do with user input lives in the service layer. This boundary means we could later replace Streamlit with FastAPI plus a React front end without touching the agent.

**PlannerService.** Owns the workflow: ingest a note, run the extract-classify-draft pipeline, await approval, commit approved changes, generate the weekly digest. Has no Streamlit imports and no LLM-vendor-specific code — it speaks to the agent through a stable interface and to storage through repository functions. This is the single layer that defines what the application does, in business-domain language.

**PlannerAgent.** Wraps the Microsoft Agent Framework. Defines the agent persona and registers four tools: `extract_tasks(note_text)`, `classify_change(extracted_item, candidate_matches)`, `generate_draft(classified_changes)`, and `summarize_changes(change_log_window)`. Each tool is a thin wrapper that prepares a prompt, calls Azure OpenAI with a JSON-schema-constrained response, validates the result, and returns typed Python data. The agent layer is the only place that knows about LLMs.

**Repository layer.** One Python module per table — `meeting_notes_repo.py`, `tasks_repo.py`, `drafts_repo.py`, `change_log_repo.py`. Pure CRUD via SQLAlchemy or asyncpg. No business logic and no LLM awareness. Storage can be swapped (e.g., SQLite for local dev) by changing the connection string.

### 4.3 Why This Shape

The four units have strict one-way dependencies: UI depends on service, service depends on agent and repositories, agent depends on Azure OpenAI, repositories depend on Postgres. Nothing reaches across these boundaries. Each unit answers a single question: the UI answers "how does the user see and act on the plan?", the service answers "what does the application do?", the agent answers "how do we use an LLM to do it?", and the repositories answer "how do we persist what we know?".

Smaller, well-bounded units are also easier to work with under time pressure. Edits stay focused, tests stay simple, and when something breaks during the demo, it is easy to find which layer is responsible.

## 5. Data Model

Four PostgreSQL tables form the entire persistent state.

### 5.1 `meeting_notes`

Stores the raw input — the unstructured conversational source. Each row is one ingested note.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `source` | TEXT | One of `meeting`, `email`, `chat` |
| `title` | TEXT | Short label, e.g., "Sprint planning 2026-05-01" |
| `content` | TEXT | Full raw text of the note |
| `meeting_date` | DATE | When the conversation happened |
| `attendees` | TEXT[] | Names captured at ingestion |
| `ingested_at` | TIMESTAMPTZ | DEFAULT now() |

### 5.2 `tasks`

The structured plan — the canonical "tracker." Every row is a current task in the official plan. Updates rewrite this table; the historical record of how it changed lives in `change_log`.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `title` | TEXT | |
| `description` | TEXT | Nullable, longer detail when extracted |
| `owner` | TEXT | Nullable until assigned |
| `due_date` | DATE | Nullable |
| `status` | TEXT | One of `not_started`, `in_progress`, `blocked`, `done` |
| `priority` | TEXT | One of `low`, `med`, `high` |
| `depends_on` | UUID[] | References other task ids |
| `source_note_id` | UUID FK | The note where this task originated |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

### 5.3 `pending_drafts`

The staging area for the human-in-the-loop workflow. Every time a meeting note is processed, the agent's proposed changes land here as a single draft awaiting review. A draft is atomic — the reviewer either applies the approved subset of changes or discards the draft.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `created_at` | TIMESTAMPTZ | |
| `source_note_id` | UUID FK | The note that produced this draft |
| `proposed_changes` | JSONB | List of change objects: `{op, task_id?, fields, evidence_quote, confidence, candidates?}` |
| `summary_md` | TEXT | Executive-friendly summary generated by the agent |
| `status` | TEXT | One of `pending`, `approved`, `rejected` |

JSONB is used for `proposed_changes` rather than a separate normalized table because drafts are atomic units — there is no use case for cross-row queries over individual proposed changes. Keeping them in a single column simplifies the read and write paths.

### 5.4 `change_log`

The auditable history of what was actually applied to the plan. One row per applied change, recording before and after snapshots and the human reviewer's decision context.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `applied_at` | TIMESTAMPTZ | |
| `draft_id` | UUID FK | Which draft this change came from |
| `task_id` | UUID FK | The task affected |
| `op` | TEXT | One of `create`, `update`, `delete` |
| `before` | JSONB | Snapshot of the task row before the change (null for `create`) |
| `after` | JSONB | Snapshot after the change (null for `delete`) |
| `evidence_quote` | TEXT | The exact source text supporting the change |
| `approved_by` | TEXT | Reviewer identifier |

Every applied change carries an `evidence_quote` pinning it back to the source text. This is the foundation of the auditability story — no plan edit exists without a traceable conversational origin.

## 6. Agent Workflow

The end-to-end flow when a user pastes or uploads a meeting note in the Inbox proceeds through six clearly bounded stages.

**Stage 1: Ingest.** The UI calls `PlannerService.ingest_note(text, metadata)`, which inserts a row into `meeting_notes` and returns the new note id. This stage has no LLM involvement and is fast.

**Stage 2: Extract.** The service calls `PlannerAgent.extract_tasks(note_text)`. The agent prompts GPT-4o-mini with a structured-output JSON schema and receives a list of extracted items, each with a title, optional owner, optional due date, optional status, optional priority, optional dependency cues, an evidence quote pulled verbatim from the source, and a confidence value between zero and one.

**Stage 3: Classify.** For each extracted item, the service calls `PlannerAgent.classify_change(item, candidate_matches)`. The service first loads candidate matches from the `tasks` table using a fuzzy match on title and owner, then passes the candidates to the agent. GPT-4o decides whether the item represents a `NEW` task, an `UPDATE` to a specific existing task, or a `CONFLICT` requiring clarification (for example, the new item plausibly matches more than one existing task, or contradicts an existing field). The classification result includes the chosen operation, the target task id when applicable, the fields to change, the confidence, and — for conflicts — the candidate task ids the reviewer needs to disambiguate.

**Stage 4: Draft.** With all classified changes in hand, the service calls `PlannerAgent.generate_draft(classified_changes)`. GPT-4o composes an executive-friendly markdown summary — for example, "3 new tasks proposed, 2 owner changes, 1 date shift, 1 ambiguity flagged for clarification." The service then inserts a row into `pending_drafts` with the proposed changes JSONB, the markdown summary, and `status = 'pending'`.

**Stage 5: Review (human-in-the-loop).** The UI's Drafts page renders the draft. The reviewer sees the summary, then a per-change table with operation, target task, field changes, evidence quote, and confidence. High-confidence changes are pre-checked for approval; low-confidence changes are visually flagged and require explicit interaction. Conflicts open a dedicated side-by-side resolution view showing the agent's reasoning, the existing candidate task, and Merge / Keep Separate / Edit controls. The reviewer can approve, reject, or edit each change individually, or use bulk approve and bulk reject controls.

**Stage 6: Commit.** When the reviewer clicks Apply Decisions, the service calls `apply_draft(draft_id, decisions)`. The service runs a single database transaction that, for each approved change, performs the appropriate insert, update, or delete on `tasks` and inserts a row into `change_log` with the before-and-after snapshots and the evidence quote. The draft's status is set to `approved` (or `rejected` if every change was rejected). The transaction is all-or-nothing — partial application is not supported, because a half-applied plan update is worse than no update at all.

### 6.1 Error Handling

Only the failures that can realistically happen in the live demo path are handled explicitly:

- If the LLM returns invalid JSON, the agent retries once with a stricter prompt. If the second attempt also fails, the service surfaces a user-facing error asking the user to try a shorter note or paste again.
- If Azure OpenAI returns a rate-limit or timeout response, the agent retries with exponential backoff up to three times before surfacing a user-facing error.
- If `classify_change` cannot confidently choose between multiple candidate tasks, the result is `op = CONFLICT` with the candidate ids attached. This is a normal path, not an error — the conflict is what the human is there to resolve.
- If the database transaction in Stage 6 fails, the entire transaction rolls back. The draft remains in `pending` status and the user can retry.

### 6.2 Deliberate Non-Handling

Several scenarios are intentionally not handled because they add complexity without serving the demo or the problem statement:

- There is no undo for approved changes. The `change_log` is the audit trail; correcting a mistaken approval means processing a new note (or directly editing in a future iteration).
- There is no concurrent-edit handling. The demo is single-user.
- Drafts are not partially persisted mid-review. If the browser closes, the draft remains in `pending` and the reviewer starts over.

## 7. UI Pages

Streamlit, a single application, sidebar navigation, five pages.

**Inbox.** A text area for pasting a meeting note, plus an upload control accepting `.txt`, `.md`, and `.eml` files. Metadata fields for title, meeting date, attendees, and source type. A Process button triggers ingest, extract, classify, and draft, then routes the user to the Drafts page with the new draft pre-selected.

**Drafts.** The headline feature. The left panel lists pending drafts newest-first with a one-line summary and change count. The right panel shows the selected draft's markdown summary, then a table of proposed changes with operation, target task, field-level changes, evidence quote, and confidence. Each row has approve, reject, and edit controls; the page footer has bulk approve, bulk reject, and apply-decisions buttons. Conflicts open the side-by-side resolution view inline.

**Tracker.** A filterable table of the current plan: task, owner, due date, status, priority, last updated. Filters cover status, owner, overdue, and due-this-week. Visual cues call out overdue (red), due within three days (amber), and done (grey). An urgent-tasks panel pinned at the top combines overdue and high-priority items.

**Gantt.** A Plotly timeline visualization, one row per task, colored by status, with a today marker line. Clicking a bar opens a task-detail side drawer.

**Change Log.** Reverse-chronological audit view from the `change_log` table. Each row shows timestamp, operation, target task, a colored inline diff of before-versus-after fields, the evidence quote, and the approver. Filters by date range and task. The page header includes a "Generate weekly digest" button that calls `summarize_changes` over the last seven days and renders the executive summary.

**Cross-cutting elements.** The sidebar shows live application status — Postgres connected, Azure OpenAI reachable — which doubles as a useful demo affordance. A "Generate Sample Data" button in the top-right loads the curated CWB_SJ dataset for instant demo readiness.

## 8. Testing Strategy

Testing is scaled to a 2.5-day solo build. The goal is enough coverage to catch regressions during the build, not comprehensive verification.

**Unit tests (pytest).** The repository layer and the `PlannerService` orchestration logic. The agent is mocked. Approximately 15 to 20 tests covering ingest, classification of NEW versus UPDATE branches, the draft commit transaction, and `change_log` insertion. These run on every push in CI.

**Live agent tests (pytest, marked `@pytest.mark.live`).** Five or six golden-path tests using fixtures from the CWB_SJ dataset and real Azure OpenAI calls. Assertions cover that extraction returns the expected count of tasks, that classification correctly identifies a known UPDATE versus a known NEW item, and that evidence quotes are present and non-empty. These run manually before the demo, not in CI.

**No automated UI tests.** Streamlit's testing tooling is awkward and the time is better invested in the demo video. Manual click-through is the verification path.

**Excluded:** load tests, security tests, and browser-compatibility tests are out of scope for a hackathon MVP.

## 9. Deployment

The application deploys as a single container to Azure Container Apps.

A single `Dockerfile` based on `python:3.12-slim` installs dependencies, copies the application code, and launches Streamlit. Provisioning is scripted in `infra/deploy.sh` using the Azure CLI: a resource group, an Azure Database for PostgreSQL Flexible Server (Burstable B1ms tier, approximately thirteen US dollars per month), an Azure OpenAI deployment with both GPT-4o-mini and GPT-4o, and a Container Apps environment hosting the application. Secrets — the Postgres connection string, the Azure OpenAI endpoint, and the Azure OpenAI key — are stored in Container Apps secrets, never in the repository. Public ingress is configured on port 8501. The deployed application surfaces on a `https://<app>.<region>.azurecontainerapps.io` URL, which is the URL submitted to the hackathon portal.

Total expected Azure cost across the build, demo, and immediate post-submission window is well within the two hundred dollar Azure free trial credit.

## 10. Repository Hygiene

The hackathon rules require a real, incremental commit history. The build approach uses conventional commits, kept small and frequent, targeting at least thirty commits across the two-and-a-half-day build. A minimal GitHub Actions workflow at `.github/workflows/ci.yml` runs unit tests, `ruff`, and `mypy` on every push — cheap to set up and a clear signal of "Submission Completeness." The `README.md` covers the problem, the architecture diagram, screenshots, local-run instructions, deployment instructions, the live demo URL, and an explicit AI-tool-disclosure section as required by the hackathon code of conduct.

## 11. Build Timeline

**Day 1 — Thursday, May 1.** Azure account and resource provisioning; repository scaffold; Postgres schema and repository layer; agent and tools; end-to-end extract-classify-draft pipeline working locally against a local Postgres instance.

**Day 2 — Friday, May 2.** Streamlit UI for all five pages; commit-and-approval flow; sample-data loader; confidence-driven approval UX; conflict-resolution view; weekly digest. Container build and deploy to Azure Container Apps. Smoke test on the deployed URL.

**Day 3 — Saturday, May 3.** README polish; screenshots; record the five-minute pitch video; final submission upload before 11:59 PM SGT. Day 3 is reserved for non-code submission deliverables only — any decision to promote a deferred feature (replay mode or bidirectional traceability) must be made and built during Day 2, not borrowed from Day 3.

## 12. Judging-Criteria Mapping

The design choices map back to the published judging criteria as follows.

**Technical Merit.** Clean four-layer architecture with strict one-way dependencies, structured-output LLM calls with JSON-schema validation, transactional commits with full audit logging, and a typed repository layer.

**Feasibility.** Lean Azure surface (four services), single-container deployment, conservative scope, and a build timeline that reserves the entire third day for non-code submission deliverables.

**Innovation and Creativity.** Confidence-driven approval UX, first-class conflict resolution flow, evidence-quote pinning on every plan change, and an agent-generated weekly executive digest.

**Potential Impact.** Direct alignment with the problem statement's core concern — that plans drift from reality because conversation-to-plan translation is manual. The audit trail and approval workflow address the governance dimension explicitly.

**Pitch Quality.** Reserved Day 3 time for video preparation; the demo path tells a single coherent story (paste a meeting note, see the agent propose changes, approve them, watch the plan and Gantt update, generate the executive digest).

**Submission Completeness.** Public GitHub repository with conventional commit history, comprehensive README, live deployed URL, recorded YouTube pitch video, optional architecture diagram, and explicit AI-tool-usage disclosure.
