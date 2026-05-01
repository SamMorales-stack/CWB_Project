# Architecture

```mermaid
flowchart TB
    subgraph Browser
        U[User]
    end

    subgraph "Azure Container Apps"
        UI["Streamlit UI<br/>Inbox · Drafts · Tracker · Gantt · Change Log"]
        SVC["PlannerService<br/>orchestration"]
        AGENT["PlannerAgent<br/>extract · classify · draft · digest"]
        REPO["Repository layer<br/>meeting_notes · tasks · pending_drafts · change_log"]
    end

    subgraph "Azure Managed"
        AOAI[("Azure OpenAI<br/>gpt-4o + gpt-4o-mini")]
        PG[("Azure Database for PostgreSQL<br/>Flexible Server")]
    end

    U -->|HTTPS| UI
    UI --> SVC
    SVC --> AGENT
    SVC --> REPO
    AGENT --> AOAI
    REPO --> PG
```

## Layer responsibilities

The application is split into four units with strictly one-way dependencies. Each unit answers one question and depends only on the units beneath it.

- **Streamlit UI** (`planner.ui`) — pure presentation and user input. Imports nothing from the agent layer directly. Calls into `PlannerService` via plain Python function calls. Holds no business logic.
- **PlannerService** (`planner.service`) — owns the workflow: ingest a note, run the extract-classify-draft pipeline, await approval, commit approved changes, generate the weekly digest. Has no Streamlit imports and no LLM-vendor-specific code.
- **PlannerAgent** (`planner.agent`) — wraps the structured LLM tool calls. Defines four tools — `extract_tasks`, `classify_change`, `generate_draft`, `summarize_changes` — each a thin wrapper around an Azure OpenAI call validated against a Pydantic schema.
- **Repository layer** (`planner.repositories`) — typed CRUD per table. Pure data access, no LLM awareness.

## Data flow: one meeting note end-to-end

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Streamlit (Inbox)
    participant Svc as PlannerService
    participant Agent as PlannerAgent
    participant LLM as Azure OpenAI
    participant DB as PostgreSQL

    User->>UI: Paste meeting note + click Process
    UI->>Svc: ingest_note(text, metadata)
    Svc->>DB: INSERT meeting_notes
    Svc->>Agent: extract(note_text)
    Agent->>LLM: structured prompt (gpt-4o-mini)
    LLM-->>Agent: ExtractedItem[]
    loop per item
        Svc->>DB: search_candidates (fuzzy)
        DB-->>Svc: matching tasks
        Svc->>Agent: classify_change(item, candidates)
        Agent->>LLM: structured prompt (gpt-4o)
        LLM-->>Agent: ClassificationResult
    end
    Svc->>Agent: generate_draft(changes)
    Agent->>LLM: structured prompt (gpt-4o)
    LLM-->>Agent: DraftSummary
    Svc->>DB: INSERT pending_drafts (status='pending')
    DB-->>Svc: draft id
    Svc-->>UI: draft summary
    UI-->>User: "Draft created — review on Drafts page"

    User->>UI: Approve / Reject decisions
    UI->>Svc: apply_draft(draft_id, decisions)
    Svc->>DB: BEGIN TRANSACTION
    Note over Svc,DB: For each approved change:<br/>UPDATE/INSERT/DELETE on tasks<br/>+ INSERT change_log row<br/>(with before/after + evidence_quote)
    Svc->>DB: COMMIT
    Svc-->>UI: success
    UI-->>User: Tracker + Change Log updated
```

## Why this shape

- **Strict boundaries** make each unit independently testable. The UI mocks the service. The service mocks the agent. The agent layer is the only place that knows about LLMs. The repositories are the only place that knows about Postgres.
- **Single source of truth** — the `tasks` table is the canonical plan. The `change_log` is the auditable history of how it changed, with every row carrying the verbatim source `evidence_quote`. There is no plan edit anywhere in the system that does not point back to a meeting note.
- **Transactional commits** — `apply_draft` is all-or-nothing per draft. A half-applied plan update is worse than no update at all.
- **Stateless agent** — the `PlannerAgent` holds no instance state; every tool call is a fresh structured prompt. Retries and structured-output validation live in the client wrapper.
