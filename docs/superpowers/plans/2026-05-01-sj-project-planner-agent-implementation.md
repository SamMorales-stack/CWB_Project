# SJ Project Planner Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a deployable Streamlit-based agentic AI assistant that ingests meeting notes, drafts structured plan updates with evidence quotes, and lets a human approve them — all backed by Azure OpenAI and Azure Database for PostgreSQL — in time for the Microsoft Code Without Barriers 2026 hackathon submission deadline (2026-05-03, 11:59 PM SGT).

**Architecture:** Single Streamlit container deployed to Azure Container Apps. Inside the process: `PlannerService` orchestrates a `PlannerAgent` (Azure OpenAI via the `openai` Python SDK with native tool-calling) and a typed repository layer over PostgreSQL. Strict one-way dependencies (UI → service → agent + repos → external). See `docs/superpowers/specs/2026-05-01-sj-project-planner-agent-design.md`.

**Tech Stack:** Python 3.12, Streamlit, SQLAlchemy 2.x + Alembic, openai (Azure mode), Pydantic v2, rapidfuzz, Plotly, pytest, Docker, Azure CLI, Azure Container Apps, Azure Database for PostgreSQL Flexible Server, Azure OpenAI (GPT-4o + GPT-4o-mini).

---

## Pre-flight: One-Time Setup (before Task 1)

These prerequisites are not "tasks" because they are environmental, not code. Complete them before starting Task 1.

1. **Install local tools**
   - Python 3.12 (`python --version` should report 3.12.x)
   - Docker Desktop for Windows (running, with Linux containers)
   - Azure CLI (`az --version`) — install from https://learn.microsoft.com/cli/azure/install-azure-cli-windows
   - Git (already installed in this environment)

2. **Azure account** — sign up for the Azure free trial at https://azure.microsoft.com/free (gives $200 credit). Verify with `az login` then `az account show`.

3. **Provision Azure OpenAI access** — apply at https://aka.ms/oai/access if not already approved. Then in the Azure Portal create an Azure OpenAI resource in a region that supports both `gpt-4o` and `gpt-4o-mini` (e.g., `eastus2` or `swedencentral`). Deploy two models inside it named exactly `gpt-4o` and `gpt-4o-mini`. Copy the endpoint URL and a key for later.

4. **Create local Azure resource group placeholder** — pick a globally-unique app name early, for example `sjplanner-<yourinitials><random4>`, e.g., `sjplanner-mm7f3k`. Use this consistently in commands later.

If any of step 1–3 fails, stop and resolve before starting Task 1 — the plan assumes these are working.

---

## File Structure Overview

```
D:\CWB\
├── docs/superpowers/
│   ├── specs/2026-05-01-sj-project-planner-agent-design.md       (already exists)
│   └── plans/2026-05-01-sj-project-planner-agent-implementation.md (this file)
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
├── .dockerignore
├── Dockerfile
├── docker-compose.yml                  (local dev: app + Postgres)
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
├── infra/
│   └── deploy.sh                       (Azure CLI provisioning script)
├── data/sample/
│   ├── meetings/                       (curated CWB_SJ-style notes)
│   └── baseline_tasks.json             (initial plan snapshot)
├── .github/workflows/ci.yml
├── src/planner/
│   ├── __init__.py
│   ├── config.py                       (env vars, settings)
│   ├── db.py                           (engine, Session)
│   ├── models.py                       (SQLAlchemy declarative models)
│   ├── service.py                      (PlannerService orchestration)
│   ├── matcher.py                      (fuzzy task matching)
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── meeting_notes_repo.py
│   │   ├── tasks_repo.py
│   │   ├── drafts_repo.py
│   │   └── change_log_repo.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── client.py                   (Azure OpenAI client wrapper)
│   │   ├── schemas.py                  (Pydantic schemas for structured outputs)
│   │   ├── prompts.py                  (prompt templates)
│   │   ├── tools.py                    (extract/classify/draft/summarize tools)
│   │   └── planner_agent.py            (high-level orchestrator)
│   └── ui/
│       ├── __init__.py
│       ├── app.py                      (Streamlit entry, sidebar nav)
│       ├── sample_data.py              (sample-data loader)
│       └── pages/
│           ├── __init__.py
│           ├── inbox.py
│           ├── drafts.py
│           ├── tracker.py
│           ├── gantt.py
│           └── change_log.py
└── tests/
    ├── __init__.py
    ├── conftest.py                     (fixtures: db, mock LLM)
    ├── test_repositories.py
    ├── test_matcher.py
    ├── test_service.py
    ├── test_agent_tools.py             (mocked LLM)
    ├── test_agent_live.py              (real Azure OpenAI; @pytest.mark.live)
    └── fixtures/
        └── sample_notes.py
```

---

## Tasks

---

### Task 1: Project scaffold

**Files:**
- Create: `D:\CWB\pyproject.toml`
- Create: `D:\CWB\.gitignore`
- Create: `D:\CWB\.env.example`
- Create: `D:\CWB\src\planner\__init__.py`
- Create: `D:\CWB\tests\__init__.py`
- Create: `D:\CWB\README.md` (skeleton; final polish in Task 38)

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "sj-planner-agent"
version = "0.1.0"
description = "SJ Project Planner Agent — agentic AI for meeting-to-plan translation"
requires-python = ">=3.12"
dependencies = [
    "streamlit>=1.36",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "psycopg[binary]>=3.1",
    "openai>=1.40",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "rapidfuzz>=3.9",
    "plotly>=5.22",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "ruff>=0.5",
    "mypy>=1.10",
    "types-python-dateutil",
]

[tool.pytest.ini_options]
markers = [
    "live: integration tests that hit real Azure OpenAI (slow, costs money)",
]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.mypy]
python_version = "3.12"
strict_optional = true
ignore_missing_imports = true

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: Create `.gitignore`**

```
# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
build/
dist/

# Virtual envs
.venv/
venv/
env/

# Environment
.env
.env.local

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Local data
*.sqlite
*.db
data/local/
```

- [ ] **Step 3: Create `.env.example`**

```
# Local development
DATABASE_URL=postgresql+psycopg://planner:planner@localhost:5432/planner

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT_MAIN=gpt-4o
AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4o-mini

# App
APP_NAME=SJ Project Planner Agent
LOG_LEVEL=INFO
```

- [ ] **Step 4: Create empty `__init__.py` files**

`D:\CWB\src\planner\__init__.py`:
```python
"""SJ Project Planner Agent."""
__version__ = "0.1.0"
```

`D:\CWB\tests\__init__.py`:
```python
```

- [ ] **Step 5: Create README skeleton**

`D:\CWB\README.md`:
```markdown
# SJ Project Planner Agent

Agentic AI assistant that converts unstructured project conversations into structured planning updates with a human-in-the-loop approval workflow.

Built for the Microsoft Code Without Barriers Hackathon 2026 — challenge: SJ Project Planner Agent.

## Status

Work in progress. Final README, architecture diagram, screenshots, deploy instructions, and AI-tool-usage disclosure will be filled in before submission.

## Live Demo

URL: _to be deployed_

## Pitch Video

URL: _to be recorded_

## License

Hackathon submission — all rights reserved by the author.
```

- [ ] **Step 6: Create Python virtual environment and install dependencies**

```bash
python -m venv .venv
source .venv/Scripts/activate  # Git Bash on Windows
pip install -e ".[dev]"
```

Expected: dependencies install without errors. If `psycopg[binary]` fails on Windows, run `pip install psycopg-binary` separately.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore .env.example src/ tests/ README.md
git commit -m "chore: bootstrap project scaffold"
```

---

### Task 2: Local Postgres via docker-compose

**Files:**
- Create: `D:\CWB\docker-compose.yml`

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: sjplanner-postgres
    environment:
      POSTGRES_DB: planner
      POSTGRES_USER: planner
      POSTGRES_PASSWORD: planner
    ports:
      - "5432:5432"
    volumes:
      - sjplanner-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U planner -d planner"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  sjplanner-pgdata:
```

- [ ] **Step 2: Start Postgres and verify**

```bash
docker compose up -d postgres
docker compose ps
```

Expected: container running, status `healthy` after ~10 seconds.

- [ ] **Step 3: Verify connectivity**

```bash
docker exec -it sjplanner-postgres psql -U planner -d planner -c "select version();"
```

Expected: prints PostgreSQL 16.x version line.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "chore: add local Postgres via docker-compose"
```

---

### Task 3: CI workflow

**Files:**
- Create: `D:\CWB\.github\workflows\ci.yml`

- [ ] **Step 1: Write CI workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: planner
          POSTGRES_USER: planner
          POSTGRES_PASSWORD: planner
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U planner -d planner"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+psycopg://planner:planner@localhost:5432/planner
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: mypy src
      - run: pytest -m "not live" -v
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add lint + test workflow"
```

(The workflow will fail on first push because no tests exist yet — that's fine, will pass after Task 7.)

---

### Task 4: Settings module

**Files:**
- Create: `D:\CWB\src\planner\config.py`

- [ ] **Step 1: Write `config.py`**

```python
"""Application settings loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_deployment_main: str = "gpt-4o"
    azure_openai_deployment_fast: str = "gpt-4o-mini"
    app_name: str = "SJ Project Planner Agent"
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

- [ ] **Step 2: Create local `.env` from example**

```bash
cp .env.example .env
```

Then edit `.env` to fill in the real Azure OpenAI endpoint and key from the Pre-flight setup. Do NOT commit `.env`.

- [ ] **Step 3: Smoke-test the import**

```bash
python -c "from planner.config import get_settings; print(get_settings().app_name)"
```

Expected: prints `SJ Project Planner Agent`.

- [ ] **Step 4: Commit**

```bash
git add src/planner/config.py
git commit -m "feat: add settings module with env-based config"
```

---

### Task 5: Database engine and session

**Files:**
- Create: `D:\CWB\src\planner\db.py`

- [ ] **Step 1: Write `db.py`**

```python
"""Database engine and session management."""
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from planner.config import get_settings


def _build_engine():
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


_engine = _build_engine()
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 2: Commit**

```bash
git add src/planner/db.py
git commit -m "feat: add database engine and session_scope context manager"
```

---

### Task 6: SQLAlchemy models

**Files:**
- Create: `D:\CWB\src\planner\models.py`

- [ ] **Step 1: Write the four models**

```python
"""SQLAlchemy declarative models for the four planner tables."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ARRAY, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class MeetingNote(Base):
    __tablename__ = "meeting_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meeting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    attendees: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="med")
    depends_on: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    source_note_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meeting_notes.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PendingDraft(Base):
    __tablename__ = "pending_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_note_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meeting_notes.id"), nullable=True
    )
    proposed_changes: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    summary_md: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")


class ChangeLogEntry(Base):
    __tablename__ = "change_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pending_drafts.id"), nullable=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )
    op: Mapped[str] = mapped_column(String(16), nullable=False)
    before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence_quote: Mapped[str] = mapped_column(Text, default="")
    approved_by: Mapped[str] = mapped_column(String(128), default="reviewer")
```

- [ ] **Step 2: Commit**

```bash
git add src/planner/models.py
git commit -m "feat: add SQLAlchemy models for the four planner tables"
```

---

### Task 7: Alembic setup and initial migration

**Files:**
- Create: `D:\CWB\alembic.ini`
- Create: `D:\CWB\alembic\env.py`
- Create: `D:\CWB\alembic\script.py.mako`
- Create: `D:\CWB\alembic\versions\0001_initial.py`

- [ ] **Step 1: Initialize alembic**

```bash
alembic init alembic
```

This creates `alembic.ini` and the `alembic/` directory. Then overwrite the generated files in steps 2–4.

- [ ] **Step 2: Configure `alembic.ini`** — find the `sqlalchemy.url` line and leave it blank; we set it from env in `env.py`. The line should read:

```
sqlalchemy.url =
```

- [ ] **Step 3: Replace `alembic/env.py`**

```python
"""Alembic environment using app settings + models metadata."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from planner.config import get_settings
from planner.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate the initial migration**

```bash
alembic revision --autogenerate -m "initial schema"
```

Expected: a file like `alembic/versions/<hash>_initial_schema.py` is created. Rename it to `0001_initial.py` and rename the revision id to `0001_initial` (and `down_revision = None`).

- [ ] **Step 5: Apply the migration**

```bash
alembic upgrade head
```

Expected: Postgres now has the four tables. Verify:

```bash
docker exec -it sjplanner-postgres psql -U planner -d planner -c "\dt"
```

Should show `meeting_notes`, `tasks`, `pending_drafts`, `change_log`, and `alembic_version`.

- [ ] **Step 6: Commit**

```bash
git add alembic.ini alembic/
git commit -m "feat: configure alembic with initial schema migration"
```

---

### Task 8: Test fixtures (conftest)

**Files:**
- Create: `D:\CWB\tests\conftest.py`
- Create: `D:\CWB\tests\fixtures\__init__.py`
- Create: `D:\CWB\tests\fixtures\sample_notes.py`

- [ ] **Step 1: Write `conftest.py` with DB fixture**

```python
"""Pytest fixtures for repository and service tests."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from planner.db import SessionLocal
from planner.models import Base, ChangeLogEntry, MeetingNote, PendingDraft, Task


@pytest.fixture(autouse=True)
def _truncate_tables():
    """Reset the four planner tables before each test."""
    with SessionLocal() as session:
        for model in (ChangeLogEntry, PendingDraft, Task, MeetingNote):
            session.query(model).delete()
        session.commit()
    yield


@pytest.fixture()
def session():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
```

- [ ] **Step 2: Write a small fixture of sample notes**

`D:\CWB\tests\fixtures\__init__.py`:
```python
```

`D:\CWB\tests\fixtures\sample_notes.py`:
```python
"""Reusable sample meeting-note content for tests."""

NOTE_SPRINT_PLANNING = """
Sprint planning - 2026-04-29

Attendees: Alex (PM), Priya (Backend), Marco (Frontend)

Decisions:
- Priya will own the Postgres migration. Target ship date: 2026-05-06.
- Marco picks up the new dashboard skeleton. No firm date yet.
- The customer-export script that Alex started last week is now blocked
  on a billing-team API change.
""".strip()

NOTE_FOLLOWUP_EMAIL = """
Subject: Re: Sprint planning follow-up
From: priya@sj.example
Date: 2026-04-30

Quick correction from yesterday: the Postgres migration target should be
2026-05-08, not 2026-05-06. I had a calendar conflict on the original
date. Please update the tracker.
""".strip()
```

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py tests/fixtures/
git commit -m "test: add db fixture and sample note fixtures"
```

---

### Task 9: meeting_notes repository (TDD)

**Files:**
- Create: `D:\CWB\src\planner\repositories\__init__.py`
- Create: `D:\CWB\src\planner\repositories\meeting_notes_repo.py`
- Create: `D:\CWB\tests\test_repositories.py`

- [ ] **Step 1: Write `__init__.py`**

`D:\CWB\src\planner\repositories\__init__.py`:
```python
"""Repository layer — pure CRUD over the planner tables."""
```

- [ ] **Step 2: Write the failing test**

`D:\CWB\tests\test_repositories.py`:
```python
"""Repository-layer tests."""
from __future__ import annotations

from datetime import date

from planner.repositories import meeting_notes_repo as notes_repo


def test_create_and_get_meeting_note(session):
    note = notes_repo.create(
        session,
        source="meeting",
        title="Sprint planning",
        content="Some discussion content.",
        meeting_date=date(2026, 4, 29),
        attendees=["Alex", "Priya"],
    )
    session.commit()

    fetched = notes_repo.get(session, note.id)
    assert fetched is not None
    assert fetched.title == "Sprint planning"
    assert fetched.attendees == ["Alex", "Priya"]


def test_list_meeting_notes_returns_newest_first(session):
    notes_repo.create(session, source="meeting", title="A", content="...", attendees=[])
    notes_repo.create(session, source="email", title="B", content="...", attendees=[])
    session.commit()

    results = notes_repo.list_recent(session, limit=10)
    assert [n.title for n in results] == ["B", "A"]
```

- [ ] **Step 3: Run the failing test**

```bash
pytest tests/test_repositories.py -v
```

Expected: ImportError or ModuleNotFoundError for `meeting_notes_repo`.

- [ ] **Step 4: Implement the repository**

`D:\CWB\src\planner\repositories\meeting_notes_repo.py`:
```python
"""CRUD for meeting_notes."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from planner.models import MeetingNote


def create(
    session: Session,
    *,
    source: str,
    title: str,
    content: str,
    meeting_date: date | None = None,
    attendees: list[str] | None = None,
) -> MeetingNote:
    note = MeetingNote(
        source=source,
        title=title,
        content=content,
        meeting_date=meeting_date,
        attendees=attendees or [],
    )
    session.add(note)
    session.flush()
    return note


def get(session: Session, note_id: uuid.UUID) -> MeetingNote | None:
    return session.get(MeetingNote, note_id)


def list_recent(session: Session, limit: int = 50) -> list[MeetingNote]:
    stmt = select(MeetingNote).order_by(MeetingNote.ingested_at.desc()).limit(limit)
    return list(session.scalars(stmt))
```

- [ ] **Step 5: Run the tests**

```bash
pytest tests/test_repositories.py -v
```

Expected: PASS, both tests green.

- [ ] **Step 6: Commit**

```bash
git add src/planner/repositories/ tests/test_repositories.py
git commit -m "feat(repo): add meeting_notes CRUD with tests"
```

---

### Task 10: tasks repository (TDD)

**Files:**
- Create: `D:\CWB\src\planner\repositories\tasks_repo.py`
- Modify: `D:\CWB\tests\test_repositories.py`

- [ ] **Step 1: Add failing tests to `tests/test_repositories.py`**

Append to the file:
```python
from datetime import date as _date  # noqa: E402

from planner.repositories import tasks_repo


def test_create_and_get_task(session):
    task = tasks_repo.create(
        session,
        title="Migrate database",
        owner="Priya",
        due_date=_date(2026, 5, 8),
        status="in_progress",
        priority="high",
    )
    session.commit()

    fetched = tasks_repo.get(session, task.id)
    assert fetched is not None
    assert fetched.owner == "Priya"
    assert fetched.status == "in_progress"


def test_update_task_fields(session):
    task = tasks_repo.create(session, title="Migrate database", owner="Priya")
    session.commit()

    tasks_repo.update(session, task.id, fields={"owner": "Marco", "status": "blocked"})
    session.commit()

    fetched = tasks_repo.get(session, task.id)
    assert fetched.owner == "Marco"
    assert fetched.status == "blocked"


def test_list_all_tasks(session):
    tasks_repo.create(session, title="A")
    tasks_repo.create(session, title="B")
    session.commit()

    assert {t.title for t in tasks_repo.list_all(session)} == {"A", "B"}


def test_search_by_title_fuzzy(session):
    tasks_repo.create(session, title="Migrate database")
    tasks_repo.create(session, title="Update dashboard skeleton")
    session.commit()

    matches = tasks_repo.search_candidates(session, query="db migration", limit=2)
    titles = [t.title for t in matches]
    assert "Migrate database" in titles
```

- [ ] **Step 2: Run the failing tests**

```bash
pytest tests/test_repositories.py -v
```

Expected: ImportError on `tasks_repo`.

- [ ] **Step 3: Implement `tasks_repo.py`**

`D:\CWB\src\planner\repositories\tasks_repo.py`:
```python
"""CRUD for tasks, plus a fuzzy candidate search."""
from __future__ import annotations

import uuid
from typing import Any

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from planner.models import Task


_ALLOWED_FIELDS = {
    "title", "description", "owner", "due_date",
    "status", "priority", "depends_on",
}


def create(session: Session, **fields: Any) -> Task:
    safe = {k: v for k, v in fields.items() if k in _ALLOWED_FIELDS}
    task = Task(**safe)
    session.add(task)
    session.flush()
    return task


def get(session: Session, task_id: uuid.UUID) -> Task | None:
    return session.get(Task, task_id)


def list_all(session: Session) -> list[Task]:
    return list(session.scalars(select(Task).order_by(Task.updated_at.desc())))


def update(session: Session, task_id: uuid.UUID, *, fields: dict[str, Any]) -> Task | None:
    task = session.get(Task, task_id)
    if task is None:
        return None
    for k, v in fields.items():
        if k in _ALLOWED_FIELDS:
            setattr(task, k, v)
    session.flush()
    return task


def delete(session: Session, task_id: uuid.UUID) -> bool:
    task = session.get(Task, task_id)
    if task is None:
        return False
    session.delete(task)
    session.flush()
    return True


def search_candidates(session: Session, *, query: str, limit: int = 5) -> list[Task]:
    """Return tasks whose title fuzzy-matches the query."""
    all_tasks = list_all(session)
    if not all_tasks:
        return []
    titles = [t.title for t in all_tasks]
    matches = process.extract(query, titles, scorer=fuzz.token_set_ratio, limit=limit)
    matched_titles = {m[0] for m in matches if m[1] >= 50}
    return [t for t in all_tasks if t.title in matched_titles]
```

- [ ] **Step 4: Run the tests**

```bash
pytest tests/test_repositories.py -v
```

Expected: all task-related tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/planner/repositories/tasks_repo.py tests/test_repositories.py
git commit -m "feat(repo): add tasks CRUD with fuzzy candidate search"
```

---

### Task 11: drafts repository (TDD)

**Files:**
- Create: `D:\CWB\src\planner\repositories\drafts_repo.py`
- Modify: `D:\CWB\tests\test_repositories.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_repositories.py`:
```python
from planner.repositories import drafts_repo  # noqa: E402


def test_create_and_get_draft(session):
    proposed = [
        {"op": "create", "fields": {"title": "Migrate db", "owner": "Priya"},
         "evidence_quote": "Priya will own the Postgres migration.", "confidence": 0.9},
    ]
    draft = drafts_repo.create(
        session,
        proposed_changes=proposed,
        summary_md="1 new task proposed.",
    )
    session.commit()

    fetched = drafts_repo.get(session, draft.id)
    assert fetched is not None
    assert fetched.status == "pending"
    assert fetched.proposed_changes[0]["op"] == "create"


def test_list_pending_drafts(session):
    drafts_repo.create(session, proposed_changes=[], summary_md="empty 1")
    drafts_repo.create(session, proposed_changes=[], summary_md="empty 2")
    session.commit()

    pending = drafts_repo.list_pending(session)
    assert len(pending) == 2


def test_set_draft_status(session):
    draft = drafts_repo.create(session, proposed_changes=[], summary_md="x")
    session.commit()

    drafts_repo.set_status(session, draft.id, "approved")
    session.commit()

    fetched = drafts_repo.get(session, draft.id)
    assert fetched.status == "approved"
```

- [ ] **Step 2: Run the failing tests**

```bash
pytest tests/test_repositories.py -v
```

Expected: ImportError on `drafts_repo`.

- [ ] **Step 3: Implement `drafts_repo.py`**

`D:\CWB\src\planner\repositories\drafts_repo.py`:
```python
"""CRUD for pending_drafts."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from planner.models import PendingDraft


def create(
    session: Session,
    *,
    proposed_changes: list[dict],
    summary_md: str,
    source_note_id: uuid.UUID | None = None,
) -> PendingDraft:
    draft = PendingDraft(
        proposed_changes=proposed_changes,
        summary_md=summary_md,
        source_note_id=source_note_id,
    )
    session.add(draft)
    session.flush()
    return draft


def get(session: Session, draft_id: uuid.UUID) -> PendingDraft | None:
    return session.get(PendingDraft, draft_id)


def list_pending(session: Session) -> list[PendingDraft]:
    stmt = (
        select(PendingDraft)
        .where(PendingDraft.status == "pending")
        .order_by(PendingDraft.created_at.desc())
    )
    return list(session.scalars(stmt))


def set_status(session: Session, draft_id: uuid.UUID, status: str) -> PendingDraft | None:
    draft = session.get(PendingDraft, draft_id)
    if draft is None:
        return None
    draft.status = status
    session.flush()
    return draft
```

- [ ] **Step 4: Run the tests**

```bash
pytest tests/test_repositories.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/planner/repositories/drafts_repo.py tests/test_repositories.py
git commit -m "feat(repo): add pending_drafts CRUD with tests"
```

---

### Task 12: change_log repository (TDD)

**Files:**
- Create: `D:\CWB\src\planner\repositories\change_log_repo.py`
- Modify: `D:\CWB\tests\test_repositories.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_repositories.py`:
```python
from planner.repositories import change_log_repo  # noqa: E402


def test_record_and_list_change_log(session):
    task = tasks_repo.create(session, title="X", owner="Priya")
    draft = drafts_repo.create(session, proposed_changes=[], summary_md="x")
    session.commit()

    change_log_repo.record(
        session,
        draft_id=draft.id,
        task_id=task.id,
        op="update",
        before={"owner": "Priya"},
        after={"owner": "Marco"},
        evidence_quote="Marco picks up the new dashboard skeleton.",
        approved_by="reviewer",
    )
    session.commit()

    entries = change_log_repo.list_recent(session, limit=10)
    assert len(entries) == 1
    assert entries[0].op == "update"
    assert entries[0].after == {"owner": "Marco"}


def test_list_within_window(session):
    task = tasks_repo.create(session, title="X")
    draft = drafts_repo.create(session, proposed_changes=[], summary_md="x")
    session.commit()
    change_log_repo.record(
        session, draft_id=draft.id, task_id=task.id, op="create",
        before=None, after={"title": "X"}, evidence_quote="...", approved_by="reviewer",
    )
    session.commit()

    from datetime import datetime, timedelta, timezone
    window_start = datetime.now(timezone.utc) - timedelta(days=7)
    entries = change_log_repo.list_since(session, since=window_start)
    assert len(entries) == 1
```

- [ ] **Step 2: Run the failing tests**

```bash
pytest tests/test_repositories.py -v
```

Expected: ImportError on `change_log_repo`.

- [ ] **Step 3: Implement `change_log_repo.py`**

`D:\CWB\src\planner\repositories\change_log_repo.py`:
```python
"""CRUD for change_log."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from planner.models import ChangeLogEntry


def record(
    session: Session,
    *,
    draft_id: uuid.UUID | None,
    task_id: uuid.UUID | None,
    op: str,
    before: dict | None,
    after: dict | None,
    evidence_quote: str,
    approved_by: str,
) -> ChangeLogEntry:
    entry = ChangeLogEntry(
        draft_id=draft_id,
        task_id=task_id,
        op=op,
        before=before,
        after=after,
        evidence_quote=evidence_quote,
        approved_by=approved_by,
    )
    session.add(entry)
    session.flush()
    return entry


def list_recent(session: Session, limit: int = 50) -> list[ChangeLogEntry]:
    stmt = select(ChangeLogEntry).order_by(ChangeLogEntry.applied_at.desc()).limit(limit)
    return list(session.scalars(stmt))


def list_since(session: Session, *, since: datetime) -> list[ChangeLogEntry]:
    stmt = (
        select(ChangeLogEntry)
        .where(ChangeLogEntry.applied_at >= since)
        .order_by(ChangeLogEntry.applied_at.desc())
    )
    return list(session.scalars(stmt))
```

- [ ] **Step 4: Run the tests**

```bash
pytest tests/test_repositories.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/planner/repositories/change_log_repo.py tests/test_repositories.py
git commit -m "feat(repo): add change_log CRUD with windowed query"
```

---

### Task 13: Pydantic schemas for structured LLM outputs

**Files:**
- Create: `D:\CWB\src\planner\agent\__init__.py`
- Create: `D:\CWB\src\planner\agent\schemas.py`

- [ ] **Step 1: Create the agent package**

`D:\CWB\src\planner\agent\__init__.py`:
```python
"""LLM agent layer."""
```

- [ ] **Step 2: Write the schemas**

`D:\CWB\src\planner\agent\schemas.py`:
```python
"""Pydantic schemas for structured LLM outputs."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


Status = Literal["not_started", "in_progress", "blocked", "done"]
Priority = Literal["low", "med", "high"]
Op = Literal["create", "update", "delete"]


class ExtractedItem(BaseModel):
    """A task-shaped item extracted from a meeting note."""
    title: str
    description: str | None = None
    owner: str | None = None
    due_date: date | None = None
    status: Status | None = None
    priority: Priority | None = None
    dependency_hints: list[str] = Field(default_factory=list)
    evidence_quote: str
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    items: list[ExtractedItem]


class CandidateMatch(BaseModel):
    task_id: str
    title: str
    owner: str | None = None
    status: Status | None = None
    due_date: date | None = None


class ClassificationResult(BaseModel):
    """Output of classify_change for one extracted item."""
    op: Literal["create", "update", "conflict"]
    target_task_id: str | None = None  # set when op == "update"
    candidate_task_ids: list[str] = Field(default_factory=list)  # set when op == "conflict"
    fields_to_change: dict = Field(default_factory=dict)
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class ProposedChange(BaseModel):
    """One proposed change attached to a draft."""
    op: Literal["create", "update", "conflict"]
    target_task_id: str | None = None
    candidate_task_ids: list[str] = Field(default_factory=list)
    fields: dict = Field(default_factory=dict)
    evidence_quote: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class DraftSummary(BaseModel):
    summary_md: str
```

- [ ] **Step 3: Smoke-test imports**

```bash
python -c "from planner.agent.schemas import ExtractedItem; print(ExtractedItem.model_json_schema()['title'])"
```

Expected: prints `ExtractedItem`.

- [ ] **Step 4: Commit**

```bash
git add src/planner/agent/
git commit -m "feat(agent): add pydantic schemas for structured LLM outputs"
```

---

### Task 14: Azure OpenAI client wrapper

**Files:**
- Create: `D:\CWB\src\planner\agent\client.py`

- [ ] **Step 1: Write the client module**

```python
"""Azure OpenAI client wrapper with structured-output helpers."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, TypeVar

from openai import AzureOpenAI
from pydantic import BaseModel

from planner.config import get_settings

T = TypeVar("T", bound=BaseModel)


@lru_cache(maxsize=1)
def get_client() -> AzureOpenAI:
    s = get_settings()
    # max_retries=3 gives us automatic exponential backoff on rate-limit
    # and transient errors (per design spec Section 6.1).
    return AzureOpenAI(
        api_key=s.azure_openai_api_key,
        api_version=s.azure_openai_api_version,
        azure_endpoint=s.azure_openai_endpoint,
        max_retries=3,
    )


def structured_completion(
    *,
    deployment: str,
    system: str,
    user: str,
    schema_model: type[T],
    temperature: float = 0.1,
) -> T:
    """Call Azure OpenAI with JSON-mode and parse into the given Pydantic model.

    Retries once with a stricter prompt on validation failure.
    """
    client = get_client()

    def _call(strict_note: str = "") -> str:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system + strict_note},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        return response.choices[0].message.content or "{}"

    raw = _call()
    try:
        data = json.loads(raw)
        return schema_model.model_validate(data)
    except Exception:
        retry = _call(
            strict_note=(
                "\n\nIMPORTANT: Your previous response was invalid JSON or did not match "
                "the required schema. Return ONLY a single JSON object that exactly matches "
                "the schema described in the user message. No prose, no markdown fences."
            )
        )
        data = json.loads(retry)
        return schema_model.model_validate(data)


def chat_completion(*, deployment: str, system: str, user: str, temperature: float = 0.3) -> str:
    """Plain chat completion returning the raw string response."""
    client = get_client()
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def schema_to_user_hint(schema_model: type[BaseModel]) -> str:
    """Render a JSON-schema hint suitable for inclusion in a user prompt."""
    schema = schema_model.model_json_schema()
    return f"\n\nRespond with a single JSON object matching this schema:\n{json.dumps(schema, indent=2)}"
```

- [ ] **Step 2: Commit**

```bash
git add src/planner/agent/client.py
git commit -m "feat(agent): add Azure OpenAI client with structured-output helper"
```

---

### Task 15: Prompts module

**Files:**
- Create: `D:\CWB\src\planner\agent\prompts.py`

- [ ] **Step 1: Write the prompts**

```python
"""Prompt templates for the planner agent's tools."""

EXTRACT_SYSTEM = """You are a project-controls assistant that extracts task-shaped items
from meeting notes, emails, and chat messages.

Rules:
- Extract one item per actionable task discussed.
- For each item, copy the EXACT verbatim sentence(s) from the source as the evidence_quote.
- If owner, due_date, status, or priority are not stated, leave them null.
- Do not invent owners or dates that are not present in the text.
- Confidence reflects how clearly the source states the item: 0.9+ for explicit
  decisions, 0.6-0.8 for clear implications, below 0.5 for vague mentions.
- Return ONLY a JSON object with an "items" array.
"""


EXTRACT_USER_TEMPLATE = """Source type: {source}
Meeting date: {meeting_date}
Title: {title}

Content:
\"\"\"
{content}
\"\"\"
"""


CLASSIFY_SYSTEM = """You are a project-controls assistant that decides whether an extracted
task-shaped item is:
  - "create" — a brand new task,
  - "update" — an update to one specific existing task,
  - "conflict" — ambiguous; could match more than one existing task or contradicts existing data.

Rules:
- Use task title, owner, and content semantics to judge similarity.
- For "update", set target_task_id to the matching task's id and put only the fields that
  changed in fields_to_change.
- For "conflict", list every candidate id you considered in candidate_task_ids and explain
  the ambiguity in the reason field.
- Return ONLY a JSON object matching the schema.
"""


CLASSIFY_USER_TEMPLATE = """Extracted item:
{item_json}

Candidate existing tasks:
{candidates_json}
"""


DRAFT_SYSTEM = """You are a project-controls assistant that writes a short executive-friendly
summary of proposed plan changes.

Rules:
- One short paragraph maximum.
- Lead with counts: how many new tasks, owner changes, date shifts, status changes,
  conflicts to resolve.
- Then call out the most impactful single change in one sentence.
- Use plain English. No bullet lists. No markdown headings.
- Return ONLY a JSON object with a "summary_md" field.
"""


DRAFT_USER_TEMPLATE = """Proposed changes (JSON):
{changes_json}
"""


DIGEST_SYSTEM = """You are a project-controls assistant writing a weekly executive digest of
plan changes.

Rules:
- Markdown output. Use a brief intro paragraph, then short headed sections for:
  "New work", "Date shifts", "Owner changes", "Resolved conflicts", "What needs attention".
- Skip any section that has no entries.
- Be specific: name the tasks and owners involved.
- Quote the evidence sparingly — only the single most telling phrase per item.
- Return ONLY a JSON object with a "summary_md" field.
"""


DIGEST_USER_TEMPLATE = """Window: last 7 days.

Change log entries (JSON):
{entries_json}
"""
```

- [ ] **Step 2: Commit**

```bash
git add src/planner/agent/prompts.py
git commit -m "feat(agent): add prompt templates for extract/classify/draft/digest"
```

---

### Task 16: Agent tools — extract_tasks (TDD with mocked LLM)

**Files:**
- Create: `D:\CWB\src\planner\agent\tools.py`
- Create: `D:\CWB\tests\test_agent_tools.py`

- [ ] **Step 1: Write the failing test with a mocked client**

`D:\CWB\tests\test_agent_tools.py`:
```python
"""Unit tests for agent tools using a mocked Azure OpenAI client."""
from __future__ import annotations

from unittest.mock import patch

from planner.agent import tools
from planner.agent.schemas import ExtractionResult


def test_extract_tasks_parses_items():
    fake_response = ExtractionResult(items=[
        {
            "title": "Migrate database",
            "owner": "Priya",
            "due_date": "2026-05-08",
            "status": "in_progress",
            "priority": "high",
            "dependency_hints": [],
            "evidence_quote": "Priya will own the Postgres migration.",
            "confidence": 0.92,
        }
    ])

    with patch("planner.agent.tools.structured_completion", return_value=fake_response) as m:
        items = tools.extract_tasks(
            note_text="Priya will own the Postgres migration.",
            source="meeting",
            meeting_date="2026-04-29",
            title="Sprint planning",
        )

    assert len(items) == 1
    assert items[0].title == "Migrate database"
    assert items[0].owner == "Priya"
    m.assert_called_once()
```

- [ ] **Step 2: Run the failing test**

```bash
pytest tests/test_agent_tools.py -v
```

Expected: ImportError on `tools.extract_tasks` or `structured_completion`.

- [ ] **Step 3: Implement `tools.py` with `extract_tasks`**

`D:\CWB\src\planner\agent\tools.py`:
```python
"""Agent tools — thin wrappers around prompted LLM calls."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from planner.agent.client import schema_to_user_hint, structured_completion, chat_completion
from planner.agent.prompts import (
    CLASSIFY_SYSTEM, CLASSIFY_USER_TEMPLATE,
    DIGEST_SYSTEM, DIGEST_USER_TEMPLATE,
    DRAFT_SYSTEM, DRAFT_USER_TEMPLATE,
    EXTRACT_SYSTEM, EXTRACT_USER_TEMPLATE,
)
from planner.agent.schemas import (
    CandidateMatch, ClassificationResult, DraftSummary,
    ExtractedItem, ExtractionResult,
)
from planner.config import get_settings


def extract_tasks(
    *, note_text: str, source: str, meeting_date: str, title: str,
) -> list[ExtractedItem]:
    """Extract task-shaped items from a meeting note."""
    s = get_settings()
    user = EXTRACT_USER_TEMPLATE.format(
        source=source, meeting_date=meeting_date, title=title, content=note_text,
    ) + schema_to_user_hint(ExtractionResult)
    result = structured_completion(
        deployment=s.azure_openai_deployment_fast,
        system=EXTRACT_SYSTEM,
        user=user,
        schema_model=ExtractionResult,
        temperature=0.1,
    )
    return result.items
```

- [ ] **Step 4: Run the test**

```bash
pytest tests/test_agent_tools.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/planner/agent/tools.py tests/test_agent_tools.py
git commit -m "feat(agent): add extract_tasks tool with mocked test"
```

---

### Task 17: Agent tools — classify_change (TDD with mocked LLM)

**Files:**
- Modify: `D:\CWB\src\planner\agent\tools.py`
- Modify: `D:\CWB\tests\test_agent_tools.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_agent_tools.py`:
```python
from planner.agent.schemas import CandidateMatch, ClassificationResult, ExtractedItem  # noqa: E402


def test_classify_change_returns_update():
    item = ExtractedItem(
        title="Postgres migration",
        owner="Priya",
        due_date="2026-05-08",
        evidence_quote="...",
        confidence=0.9,
    )
    candidates = [
        CandidateMatch(task_id="00000000-0000-0000-0000-000000000001",
                       title="Migrate database", owner="Priya", status="in_progress",
                       due_date="2026-05-06"),
    ]
    fake = ClassificationResult(
        op="update",
        target_task_id="00000000-0000-0000-0000-000000000001",
        fields_to_change={"due_date": "2026-05-08"},
        reason="Same owner and topic; only due date changed.",
        confidence=0.88,
    )

    with patch("planner.agent.tools.structured_completion", return_value=fake):
        result = tools.classify_change(item=item, candidates=candidates)

    assert result.op == "update"
    assert result.target_task_id == "00000000-0000-0000-0000-000000000001"
    assert result.fields_to_change == {"due_date": "2026-05-08"}
```

- [ ] **Step 2: Run the failing test**

```bash
pytest tests/test_agent_tools.py::test_classify_change_returns_update -v
```

Expected: AttributeError (`tools.classify_change` not defined).

- [ ] **Step 3: Add `classify_change` to `tools.py`**

Append to `src/planner/agent/tools.py`:
```python
def classify_change(
    *, item: ExtractedItem, candidates: list[CandidateMatch],
) -> ClassificationResult:
    """Decide whether the extracted item is create, update, or conflict."""
    s = get_settings()
    user = CLASSIFY_USER_TEMPLATE.format(
        item_json=item.model_dump_json(indent=2),
        candidates_json=json.dumps([c.model_dump(mode="json") for c in candidates], indent=2),
    ) + schema_to_user_hint(ClassificationResult)
    return structured_completion(
        deployment=s.azure_openai_deployment_main,
        system=CLASSIFY_SYSTEM,
        user=user,
        schema_model=ClassificationResult,
        temperature=0.1,
    )
```

- [ ] **Step 4: Run the test**

```bash
pytest tests/test_agent_tools.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/planner/agent/tools.py tests/test_agent_tools.py
git commit -m "feat(agent): add classify_change tool with mocked test"
```

---

### Task 18: Agent tools — generate_draft and summarize_changes (TDD with mocked LLM)

**Files:**
- Modify: `D:\CWB\src\planner\agent\tools.py`
- Modify: `D:\CWB\tests\test_agent_tools.py`

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_agent_tools.py`:
```python
from planner.agent.schemas import DraftSummary, ProposedChange  # noqa: E402


def test_generate_draft_returns_summary():
    changes = [
        ProposedChange(op="create", fields={"title": "Migrate db"},
                       evidence_quote="Priya will own the Postgres migration.",
                       confidence=0.9, reason="new task"),
    ]
    fake = DraftSummary(summary_md="1 new task proposed: database migration owned by Priya.")
    with patch("planner.agent.tools.structured_completion", return_value=fake):
        result = tools.generate_draft(changes=changes)
    assert "1 new task" in result.summary_md


def test_summarize_changes_returns_markdown():
    fake = DraftSummary(summary_md="## New work\n- Migrate db (Priya)")
    entries = [{
        "applied_at": "2026-04-30T10:00:00Z",
        "op": "create",
        "task_id": "id-1",
        "after": {"title": "Migrate db", "owner": "Priya"},
        "evidence_quote": "Priya will own the Postgres migration.",
    }]
    with patch("planner.agent.tools.structured_completion", return_value=fake):
        result = tools.summarize_changes(entries=entries)
    assert "## New work" in result.summary_md
```

- [ ] **Step 2: Run the failing tests**

```bash
pytest tests/test_agent_tools.py -v
```

Expected: AttributeError on `generate_draft` and `summarize_changes`.

- [ ] **Step 3: Add the two functions to `tools.py`**

Append to `src/planner/agent/tools.py`:
```python
def generate_draft(*, changes: list[ProposedChange]) -> DraftSummary:  # type: ignore[name-defined]
    """Compose an executive-friendly summary of the proposed changes."""
    from planner.agent.schemas import ProposedChange  # local import to avoid cycle  # noqa: F401
    s = get_settings()
    payload = [c.model_dump(mode="json") for c in changes]
    user = DRAFT_USER_TEMPLATE.format(changes_json=json.dumps(payload, indent=2)) + schema_to_user_hint(DraftSummary)
    return structured_completion(
        deployment=s.azure_openai_deployment_main,
        system=DRAFT_SYSTEM,
        user=user,
        schema_model=DraftSummary,
        temperature=0.3,
    )


def summarize_changes(*, entries: list[dict]) -> DraftSummary:
    """Compose a weekly executive digest from change_log entries."""
    s = get_settings()
    user = DIGEST_USER_TEMPLATE.format(entries_json=json.dumps(entries, indent=2, default=str)) + schema_to_user_hint(DraftSummary)
    return structured_completion(
        deployment=s.azure_openai_deployment_main,
        system=DIGEST_SYSTEM,
        user=user,
        schema_model=DraftSummary,
        temperature=0.4,
    )
```

Also add `ProposedChange` to the top-level imports at the top of `tools.py`:
```python
from planner.agent.schemas import (
    CandidateMatch, ClassificationResult, DraftSummary,
    ExtractedItem, ExtractionResult, ProposedChange,
)
```

(Replace the existing schemas import with this expanded one.)

- [ ] **Step 4: Run the tests**

```bash
pytest tests/test_agent_tools.py -v
```

Expected: PASS for all four agent-tool tests.

- [ ] **Step 5: Commit**

```bash
git add src/planner/agent/tools.py tests/test_agent_tools.py
git commit -m "feat(agent): add generate_draft and summarize_changes tools with mocked tests"
```

---

### Task 19: Matcher module (TDD)

**Files:**
- Create: `D:\CWB\src\planner\matcher.py`
- Create: `D:\CWB\tests\test_matcher.py`

- [ ] **Step 1: Write the failing test**

`D:\CWB\tests\test_matcher.py`:
```python
"""Tests for the candidate-match converter."""
from __future__ import annotations

from datetime import date

from planner.agent.schemas import ExtractedItem
from planner.matcher import build_candidate_matches
from planner.repositories import tasks_repo


def test_build_candidate_matches_returns_top_n_for_extracted_item(session):
    tasks_repo.create(session, title="Migrate database", owner="Priya")
    tasks_repo.create(session, title="Update dashboard skeleton", owner="Marco")
    tasks_repo.create(session, title="Customer export script", owner="Alex")
    session.commit()

    item = ExtractedItem(
        title="Postgres migration",
        owner="Priya",
        evidence_quote="Priya will own the Postgres migration.",
        confidence=0.9,
    )
    candidates = build_candidate_matches(session, item=item, limit=3)
    titles = [c.title for c in candidates]
    assert "Migrate database" in titles
    # All returned candidates carry an id string
    assert all(c.task_id for c in candidates)
```

- [ ] **Step 2: Run the failing test**

```bash
pytest tests/test_matcher.py -v
```

Expected: ImportError on `planner.matcher`.

- [ ] **Step 3: Implement `matcher.py`**

`D:\CWB\src\planner\matcher.py`:
```python
"""Convert tasks repository search hits into CandidateMatch objects for the LLM."""
from __future__ import annotations

from sqlalchemy.orm import Session

from planner.agent.schemas import CandidateMatch, ExtractedItem
from planner.repositories import tasks_repo


def build_candidate_matches(
    session: Session, *, item: ExtractedItem, limit: int = 5,
) -> list[CandidateMatch]:
    """Find existing tasks plausibly matching the extracted item."""
    query_parts = [item.title]
    if item.owner:
        query_parts.append(item.owner)
    query = " ".join(query_parts)
    candidates = tasks_repo.search_candidates(session, query=query, limit=limit)
    return [
        CandidateMatch(
            task_id=str(t.id),
            title=t.title,
            owner=t.owner,
            status=t.status,  # type: ignore[arg-type]
            due_date=t.due_date,
        )
        for t in candidates
    ]
```

- [ ] **Step 4: Run the test**

```bash
pytest tests/test_matcher.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/planner/matcher.py tests/test_matcher.py
git commit -m "feat: add candidate-match builder bridging repo and agent schemas"
```

---

### Task 20: PlannerAgent orchestrator

**Files:**
- Create: `D:\CWB\src\planner\agent\planner_agent.py`

- [ ] **Step 1: Write `planner_agent.py`**

```python
"""High-level agent that runs the extract → classify → draft pipeline."""
from __future__ import annotations

from sqlalchemy.orm import Session

from planner.agent import tools
from planner.agent.schemas import (
    DraftSummary, ExtractedItem, ExtractionResult, ProposedChange,
)
from planner.matcher import build_candidate_matches


class PlannerAgent:
    """Stateless orchestrator over agent tools."""

    def extract(
        self, *, note_text: str, source: str, meeting_date: str, title: str,
    ) -> list[ExtractedItem]:
        return tools.extract_tasks(
            note_text=note_text, source=source, meeting_date=meeting_date, title=title,
        )

    def classify_all(
        self, session: Session, *, items: list[ExtractedItem],
    ) -> list[ProposedChange]:
        proposed: list[ProposedChange] = []
        for item in items:
            candidates = build_candidate_matches(session, item=item, limit=5)
            cls = tools.classify_change(item=item, candidates=candidates)
            fields = (
                cls.fields_to_change
                if cls.op == "update"
                else item.model_dump(mode="json", exclude_none=True, exclude={"evidence_quote", "confidence"})
            )
            proposed.append(ProposedChange(
                op=cls.op,
                target_task_id=cls.target_task_id,
                candidate_task_ids=cls.candidate_task_ids,
                fields=fields,
                evidence_quote=item.evidence_quote,
                confidence=min(item.confidence, cls.confidence),
                reason=cls.reason,
            ))
        return proposed

    def draft(self, *, changes: list[ProposedChange]) -> DraftSummary:
        return tools.generate_draft(changes=changes)

    def weekly_digest(self, *, entries: list[dict]) -> DraftSummary:
        return tools.summarize_changes(entries=entries)
```

- [ ] **Step 2: Smoke-test import**

```bash
python -c "from planner.agent.planner_agent import PlannerAgent; print(PlannerAgent.__doc__)"
```

Expected: prints docstring.

- [ ] **Step 3: Commit**

```bash
git add src/planner/agent/planner_agent.py
git commit -m "feat(agent): add PlannerAgent orchestrator over the four tools"
```

---

### Task 21: PlannerService — ingest, run pipeline, apply draft (TDD)

**Files:**
- Create: `D:\CWB\src\planner\service.py`
- Create: `D:\CWB\tests\test_service.py`

- [ ] **Step 1: Write the failing test**

`D:\CWB\tests\test_service.py`:
```python
"""Tests for PlannerService end-to-end behavior with a mocked agent."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from planner.agent.schemas import (
    DraftSummary, ExtractedItem, ProposedChange,
)
from planner.repositories import (
    change_log_repo, drafts_repo, meeting_notes_repo, tasks_repo,
)
from planner.service import PlannerService


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.extract.return_value = [
        ExtractedItem(
            title="Migrate database",
            owner="Priya",
            due_date=date(2026, 5, 8),
            evidence_quote="Priya will own the Postgres migration.",
            confidence=0.92,
        )
    ]
    agent.classify_all.return_value = [
        ProposedChange(
            op="create",
            fields={"title": "Migrate database", "owner": "Priya", "due_date": "2026-05-08"},
            evidence_quote="Priya will own the Postgres migration.",
            confidence=0.92,
            reason="Brand new task with explicit owner.",
        )
    ]
    agent.draft.return_value = DraftSummary(summary_md="1 new task proposed: Migrate database (Priya).")
    agent.weekly_digest.return_value = DraftSummary(summary_md="## New work\n- Migrate database (Priya)")
    return agent


def test_ingest_and_run_pipeline_creates_draft(mock_agent, session):
    service = PlannerService(agent=mock_agent)
    note = service.ingest_note(
        text="Priya will own the Postgres migration.",
        source="meeting",
        title="Sprint planning",
        meeting_date=date(2026, 4, 29),
        attendees=["Alex", "Priya"],
    )
    draft = service.run_pipeline(note_id=note.id)

    assert draft.status == "pending"
    assert "1 new task" in draft.summary_md
    assert len(draft.proposed_changes) == 1
    assert draft.proposed_changes[0]["op"] == "create"


def test_apply_draft_creates_task_and_records_change(mock_agent, session):
    service = PlannerService(agent=mock_agent)
    note = service.ingest_note(
        text="Priya will own the Postgres migration.",
        source="meeting", title="Sprint planning",
        meeting_date=date(2026, 4, 29), attendees=["Alex", "Priya"],
    )
    draft = service.run_pipeline(note_id=note.id)

    decisions = {0: "approve"}
    service.apply_draft(draft_id=draft.id, decisions=decisions, approver="reviewer")

    with session as s:
        all_tasks = tasks_repo.list_all(s)
        assert len(all_tasks) == 1
        assert all_tasks[0].title == "Migrate database"

        log = change_log_repo.list_recent(s)
        assert len(log) == 1
        assert log[0].op == "create"
        assert log[0].after["title"] == "Migrate database"

        d = drafts_repo.get(s, draft.id)
        assert d.status == "approved"


def test_apply_draft_with_all_rejected_marks_rejected(mock_agent, session):
    service = PlannerService(agent=mock_agent)
    note = service.ingest_note(
        text="Priya will own the Postgres migration.",
        source="meeting", title="Sprint planning",
        meeting_date=date(2026, 4, 29), attendees=[],
    )
    draft = service.run_pipeline(note_id=note.id)
    service.apply_draft(draft_id=draft.id, decisions={0: "reject"}, approver="reviewer")
    with session as s:
        d = drafts_repo.get(s, draft.id)
        assert d.status == "rejected"
        assert tasks_repo.list_all(s) == []
```

- [ ] **Step 2: Run the failing test**

```bash
pytest tests/test_service.py -v
```

Expected: ImportError on `planner.service`.

- [ ] **Step 3: Implement `service.py`**

`D:\CWB\src\planner\service.py`:
```python
"""PlannerService: orchestrates ingest → extract → classify → draft → apply."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from planner.agent.planner_agent import PlannerAgent
from planner.agent.schemas import DraftSummary, ProposedChange
from planner.db import session_scope
from planner.models import PendingDraft, Task
from planner.repositories import (
    change_log_repo, drafts_repo, meeting_notes_repo, tasks_repo,
)


class PlannerService:
    def __init__(self, agent: PlannerAgent | None = None) -> None:
        self.agent = agent or PlannerAgent()

    # ---- ingest ----
    def ingest_note(
        self, *, text: str, source: str, title: str,
        meeting_date: date | None, attendees: list[str],
    ):
        with session_scope() as s:
            note = meeting_notes_repo.create(
                s, source=source, title=title, content=text,
                meeting_date=meeting_date, attendees=attendees,
            )
            s.expunge(note)
            return note

    # ---- pipeline ----
    def run_pipeline(self, *, note_id: uuid.UUID) -> PendingDraft:
        with session_scope() as s:
            note = meeting_notes_repo.get(s, note_id)
            if note is None:
                raise ValueError(f"meeting_note {note_id} not found")

            items = self.agent.extract(
                note_text=note.content,
                source=note.source,
                meeting_date=note.meeting_date.isoformat() if note.meeting_date else "",
                title=note.title,
            )

            changes: list[ProposedChange] = self.agent.classify_all(s, items=items)
            summary: DraftSummary = self.agent.draft(changes=changes)

            draft = drafts_repo.create(
                s,
                proposed_changes=[c.model_dump(mode="json") for c in changes],
                summary_md=summary.summary_md,
                source_note_id=note_id,
            )
            s.flush()
            s.expunge(draft)
            return draft

    # ---- apply ----
    def apply_draft(
        self, *, draft_id: uuid.UUID, decisions: dict[int, str], approver: str,
    ) -> None:
        """Apply the per-change decisions transactionally.

        decisions: mapping from change-index in draft.proposed_changes to one of
        'approve' or 'reject'. Indices not present default to 'reject'.
        """
        with session_scope() as s:
            draft = drafts_repo.get(s, draft_id)
            if draft is None:
                raise ValueError(f"draft {draft_id} not found")

            any_approved = False
            for idx, change in enumerate(draft.proposed_changes):
                decision = decisions.get(idx, "reject")
                if decision != "approve":
                    continue
                any_approved = True
                self._apply_one_change(s, draft_id=draft_id, change=change, approver=approver)

            drafts_repo.set_status(s, draft_id, "approved" if any_approved else "rejected")

    def _apply_one_change(
        self, session, *, draft_id: uuid.UUID, change: dict, approver: str,
    ) -> None:
        op = change["op"]
        fields = change.get("fields") or {}
        evidence = change.get("evidence_quote", "")

        if op == "create":
            new_task = tasks_repo.create(session, **_coerce_task_fields(fields))
            change_log_repo.record(
                session, draft_id=draft_id, task_id=new_task.id, op="create",
                before=None, after=_task_snapshot(new_task),
                evidence_quote=evidence, approved_by=approver,
            )
        elif op == "update":
            target_id = uuid.UUID(change["target_task_id"])
            existing = tasks_repo.get(session, target_id)
            if existing is None:
                return
            before = _task_snapshot(existing)
            tasks_repo.update(session, target_id, fields=_coerce_task_fields(fields))
            after = _task_snapshot(tasks_repo.get(session, target_id))
            change_log_repo.record(
                session, draft_id=draft_id, task_id=target_id, op="update",
                before=before, after=after,
                evidence_quote=evidence, approved_by=approver,
            )
        elif op == "conflict":
            # 'conflict' approval means the reviewer chose to MERGE into the first candidate.
            # If they wanted Keep Separate, the UI should rewrite this change to op="create"
            # before calling apply_draft.
            cand_ids = change.get("candidate_task_ids") or []
            if not cand_ids:
                return
            target_id = uuid.UUID(cand_ids[0])
            existing = tasks_repo.get(session, target_id)
            if existing is None:
                return
            before = _task_snapshot(existing)
            tasks_repo.update(session, target_id, fields=_coerce_task_fields(fields))
            after = _task_snapshot(tasks_repo.get(session, target_id))
            change_log_repo.record(
                session, draft_id=draft_id, task_id=target_id, op="update",
                before=before, after=after,
                evidence_quote=evidence, approved_by=approver,
            )

    # ---- weekly digest ----
    def weekly_digest(self) -> str:
        with session_scope() as s:
            since = datetime.now(timezone.utc) - timedelta(days=7)
            entries = change_log_repo.list_since(s, since=since)
            payload = [{
                "applied_at": e.applied_at.isoformat(),
                "op": e.op,
                "task_id": str(e.task_id) if e.task_id else None,
                "before": e.before,
                "after": e.after,
                "evidence_quote": e.evidence_quote,
                "approved_by": e.approved_by,
            } for e in entries]
            if not payload:
                return "_No applied changes in the last 7 days._"
            result = self.agent.weekly_digest(entries=payload)
            return result.summary_md


# ---- helpers ----

_TASK_FIELDS = {"title", "description", "owner", "due_date", "status", "priority"}


def _coerce_task_fields(fields: dict[str, Any]) -> dict[str, Any]:
    coerced: dict[str, Any] = {}
    for k, v in fields.items():
        if k not in _TASK_FIELDS:
            continue
        if k == "due_date" and isinstance(v, str) and v:
            coerced[k] = date.fromisoformat(v)
        else:
            coerced[k] = v
    return coerced


def _task_snapshot(task: Task | None) -> dict[str, Any] | None:
    if task is None:
        return None
    return {
        "title": task.title,
        "description": task.description,
        "owner": task.owner,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "status": task.status,
        "priority": task.priority,
    }
```

- [ ] **Step 4: Run the test**

```bash
pytest tests/test_service.py -v
```

Expected: PASS for all three service tests.

- [ ] **Step 5: Commit**

```bash
git add src/planner/service.py tests/test_service.py
git commit -m "feat: add PlannerService with ingest/pipeline/apply/digest flows"
```

---

### Task 22: Live agent integration tests

**Files:**
- Create: `D:\CWB\tests\test_agent_live.py`

- [ ] **Step 1: Write the live tests**

```python
"""Live tests against real Azure OpenAI. Run with: pytest -m live -v"""
from __future__ import annotations

import pytest

from planner.agent.planner_agent import PlannerAgent
from tests.fixtures.sample_notes import NOTE_FOLLOWUP_EMAIL, NOTE_SPRINT_PLANNING


pytestmark = pytest.mark.live


def test_extract_finds_tasks_in_sprint_planning_note():
    agent = PlannerAgent()
    items = agent.extract(
        note_text=NOTE_SPRINT_PLANNING,
        source="meeting",
        meeting_date="2026-04-29",
        title="Sprint planning",
    )
    assert len(items) >= 2
    titles_lower = " ".join(i.title.lower() for i in items)
    assert "migration" in titles_lower or "postgres" in titles_lower
    # Every extracted item should have a non-empty evidence quote
    assert all(i.evidence_quote.strip() for i in items)


def test_extract_finds_date_change_in_followup_email():
    agent = PlannerAgent()
    items = agent.extract(
        note_text=NOTE_FOLLOWUP_EMAIL,
        source="email",
        meeting_date="2026-04-30",
        title="Sprint planning follow-up",
    )
    # The follow-up explicitly states "2026-05-08" — it should appear in some item.
    dates = [i.due_date.isoformat() for i in items if i.due_date]
    assert any(d == "2026-05-08" for d in dates)
```

- [ ] **Step 2: Run the live tests (costs a few cents)**

```bash
pytest -m live -v
```

Expected: PASS. If they fail because Azure OpenAI is mis-configured, debug `.env` settings before continuing.

- [ ] **Step 3: Commit**

```bash
git add tests/test_agent_live.py
git commit -m "test: add live agent integration tests against Azure OpenAI"
```

---

### Task 23: Streamlit app skeleton

**Files:**
- Create: `D:\CWB\src\planner\ui\__init__.py`
- Create: `D:\CWB\src\planner\ui\app.py`

- [ ] **Step 1: Create UI package**

`D:\CWB\src\planner\ui\__init__.py`:
```python
"""Streamlit UI."""
```

- [ ] **Step 2: Write the app skeleton with sidebar nav**

`D:\CWB\src\planner\ui\app.py`:
```python
"""Streamlit entry point for the SJ Project Planner Agent."""
from __future__ import annotations

import streamlit as st

from planner.config import get_settings


def _check_health() -> dict[str, bool]:
    """Quick health check of Postgres + Azure OpenAI."""
    health = {"postgres": False, "azure_openai": False}
    try:
        from sqlalchemy import text
        from planner.db import SessionLocal
        with SessionLocal() as s:
            s.execute(text("select 1"))
            health["postgres"] = True
    except Exception:
        pass
    try:
        from planner.agent.client import get_client
        get_client()  # construction does not call the API; presence of config is enough
        health["azure_openai"] = True
    except Exception:
        pass
    return health


def main() -> None:
    st.set_page_config(page_title="SJ Project Planner", layout="wide")

    settings = get_settings()
    st.sidebar.title(settings.app_name)

    page = st.sidebar.radio(
        "Navigate",
        ["Inbox", "Drafts", "Tracker", "Gantt", "Change Log"],
        label_visibility="collapsed",
    )

    health = _check_health()
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Status**")
    st.sidebar.markdown(f"- Postgres: {'✅' if health['postgres'] else '❌'}")
    st.sidebar.markdown(f"- Azure OpenAI: {'✅' if health['azure_openai'] else '❌'}")
    st.sidebar.markdown("---")

    if st.sidebar.button("Generate sample data"):
        from planner.ui.sample_data import load_samples
        load_samples()
        st.sidebar.success("Sample data loaded.")

    if page == "Inbox":
        from planner.ui.pages.inbox import render
    elif page == "Drafts":
        from planner.ui.pages.drafts import render
    elif page == "Tracker":
        from planner.ui.pages.tracker import render
    elif page == "Gantt":
        from planner.ui.pages.gantt import render
    else:
        from planner.ui.pages.change_log import render

    render()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Add page-stubs so the imports succeed**

`D:\CWB\src\planner\ui\pages\__init__.py`:
```python
```

For each of the five pages, create a stub file that just renders a placeholder. We will fill them in in subsequent tasks.

`D:\CWB\src\planner\ui\pages\inbox.py`:
```python
import streamlit as st

def render() -> None:
    st.title("Inbox")
    st.info("Inbox page — implemented in Task 24.")
```

`D:\CWB\src\planner\ui\pages\drafts.py`:
```python
import streamlit as st

def render() -> None:
    st.title("Drafts")
    st.info("Drafts page — implemented in Tasks 25–27.")
```

`D:\CWB\src\planner\ui\pages\tracker.py`:
```python
import streamlit as st

def render() -> None:
    st.title("Tracker")
    st.info("Tracker page — implemented in Task 28.")
```

`D:\CWB\src\planner\ui\pages\gantt.py`:
```python
import streamlit as st

def render() -> None:
    st.title("Gantt")
    st.info("Gantt page — implemented in Task 29.")
```

`D:\CWB\src\planner\ui\pages\change_log.py`:
```python
import streamlit as st

def render() -> None:
    st.title("Change Log")
    st.info("Change Log page — implemented in Task 30.")
```

- [ ] **Step 4: Add a sample-data stub so the sidebar button does not crash**

`D:\CWB\src\planner\ui\sample_data.py`:
```python
"""Sample-data loader (filled in in Task 31)."""
def load_samples() -> None:
    pass
```

- [ ] **Step 5: Run the app locally**

```bash
streamlit run src/planner/ui/app.py
```

Expected: app opens at http://localhost:8501 with the five-page sidebar nav and status indicators (both should show ✅ if `.env` is configured and Docker Postgres is up). Click each page to confirm placeholders render.

- [ ] **Step 6: Commit**

```bash
git add src/planner/ui/
git commit -m "feat(ui): add Streamlit app skeleton with sidebar nav and health status"
```

---

### Task 24: Inbox page

**Files:**
- Modify: `D:\CWB\src\planner\ui\pages\inbox.py`

- [ ] **Step 1: Replace the inbox stub with the real page**

`D:\CWB\src\planner\ui\pages\inbox.py`:
```python
"""Inbox page: paste/upload meeting notes and run the pipeline."""
from __future__ import annotations

from datetime import date

import streamlit as st

from planner.service import PlannerService


def render() -> None:
    st.title("Inbox")
    st.caption("Paste a meeting note or upload a file. The agent will extract tasks, "
               "compare them to your current plan, and prepare a draft for review.")

    with st.form("ingest_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Title", value="")
            source = st.selectbox("Source type", ["meeting", "email", "chat"])
        with col2:
            meeting_date = st.date_input("Meeting date", value=date.today())
            attendees_raw = st.text_input("Attendees (comma-separated)", value="")

        uploaded = st.file_uploader("Upload a file (.txt, .md, .eml)", type=["txt", "md", "eml"])
        pasted = st.text_area("Or paste content", height=240)

        submitted = st.form_submit_button("Process", type="primary")

    if not submitted:
        return

    text = ""
    if uploaded is not None:
        text = uploaded.read().decode("utf-8", errors="replace")
    if pasted.strip():
        text = pasted.strip()

    if not text:
        st.error("Please paste content or upload a file.")
        return
    if not title.strip():
        st.error("Please provide a title.")
        return

    attendees = [a.strip() for a in attendees_raw.split(",") if a.strip()]

    with st.spinner("Ingesting and running the agent pipeline..."):
        service = PlannerService()
        note = service.ingest_note(
            text=text, source=source, title=title.strip(),
            meeting_date=meeting_date, attendees=attendees,
        )
        try:
            draft = service.run_pipeline(note_id=note.id)
        except Exception as exc:
            st.error(f"Pipeline failed: {exc}")
            return

    st.success(f"Draft created with {len(draft.proposed_changes)} proposed change(s).")
    st.session_state["last_draft_id"] = str(draft.id)
    st.markdown(f"**Summary:** {draft.summary_md}")
    st.info("Open the **Drafts** page to review and approve.")
```

- [ ] **Step 2: Re-run the app and smoke-test**

```bash
streamlit run src/planner/ui/app.py
```

Paste the `NOTE_SPRINT_PLANNING` content from the test fixtures and click Process. Expected: spinner, then "Draft created with N proposed change(s)" success message and a summary line.

- [ ] **Step 3: Commit**

```bash
git add src/planner/ui/pages/inbox.py
git commit -m "feat(ui): implement Inbox page — ingest + run pipeline"
```

---

### Task 25: Drafts page — list and detail view

**Files:**
- Modify: `D:\CWB\src\planner\ui\pages\drafts.py`

- [ ] **Step 1: Replace the drafts stub with list + detail layout**

```python
"""Drafts page: list pending drafts; show the selected draft's proposed changes."""
from __future__ import annotations

import uuid

import streamlit as st

from planner.db import session_scope
from planner.repositories import drafts_repo


def render() -> None:
    st.title("Drafts")
    st.caption("Review what the agent has proposed. Approve, reject, or edit per row.")

    with session_scope() as s:
        pending = drafts_repo.list_pending(s)
        # Detach from session for use after exit
        for d in pending:
            s.expunge(d)

    if not pending:
        st.info("No pending drafts. Process a note in the Inbox to create one.")
        return

    col_list, col_detail = st.columns([1, 3])

    with col_list:
        st.subheader("Pending")
        labels = [
            f"{d.created_at.strftime('%Y-%m-%d %H:%M')} — {len(d.proposed_changes)} change(s)"
            for d in pending
        ]
        # Default to last selected, otherwise first
        last = st.session_state.get("last_draft_id")
        default_idx = 0
        if last:
            for i, d in enumerate(pending):
                if str(d.id) == last:
                    default_idx = i
                    break
        idx = st.radio("Select a draft", options=range(len(labels)),
                       format_func=lambda i: labels[i], index=default_idx,
                       label_visibility="collapsed")
        selected = pending[idx]
        st.session_state["last_draft_id"] = str(selected.id)

    with col_detail:
        st.subheader("Draft summary")
        st.markdown(selected.summary_md or "_(no summary)_")
        st.subheader("Proposed changes")
        for i, change in enumerate(selected.proposed_changes):
            with st.expander(
                f"#{i+1} • {change['op'].upper()} • confidence {change.get('confidence', 0):.0%}",
                expanded=True,
            ):
                _render_change_row(i, change)


def _render_change_row(index: int, change: dict) -> None:
    st.markdown(f"**Reason:** {change.get('reason', '')}")
    st.markdown(f"**Evidence:** _{change.get('evidence_quote', '')}_")
    fields = change.get("fields") or {}
    if fields:
        st.markdown("**Fields:**")
        st.json(fields, expanded=False)
    if change["op"] == "update" and change.get("target_task_id"):
        st.caption(f"Target task: `{change['target_task_id']}`")
    if change["op"] == "conflict":
        st.warning(f"Conflict — {len(change.get('candidate_task_ids', []))} candidate(s).")
```

- [ ] **Step 2: Smoke-test in the browser**

Refresh the app and open Drafts. Expected: see the draft created in Task 24 with the change rows expanded.

- [ ] **Step 3: Commit**

```bash
git add src/planner/ui/pages/drafts.py
git commit -m "feat(ui): implement Drafts page list + detail view"
```

---

### Task 26: Drafts page — approve/reject with confidence-driven defaults

**Files:**
- Modify: `D:\CWB\src\planner\ui\pages\drafts.py`

- [ ] **Step 1: Add per-row decision controls and the apply button**

Replace the entire `render` function in `drafts.py` with the version below. Note the addition of the decisions form, confidence-driven defaults, and Apply Decisions button.

```python
"""Drafts page: list pending drafts; approve/reject changes with confidence-driven UX."""
from __future__ import annotations

import uuid

import streamlit as st

from planner.db import session_scope
from planner.repositories import drafts_repo
from planner.service import PlannerService

_HIGH_CONFIDENCE = 0.8


def render() -> None:
    st.title("Drafts")
    st.caption("High-confidence changes are pre-checked. Low-confidence changes are flagged "
               "and require your explicit approval.")

    with session_scope() as s:
        pending = drafts_repo.list_pending(s)
        for d in pending:
            s.expunge(d)

    if not pending:
        st.info("No pending drafts. Process a note in the Inbox to create one.")
        return

    col_list, col_detail = st.columns([1, 3])

    with col_list:
        st.subheader("Pending")
        labels = [
            f"{d.created_at.strftime('%Y-%m-%d %H:%M')} — {len(d.proposed_changes)} change(s)"
            for d in pending
        ]
        last = st.session_state.get("last_draft_id")
        default_idx = 0
        if last:
            for i, d in enumerate(pending):
                if str(d.id) == last:
                    default_idx = i
                    break
        idx = st.radio("Select a draft", options=range(len(labels)),
                       format_func=lambda i: labels[i], index=default_idx,
                       label_visibility="collapsed")
        selected = pending[idx]
        st.session_state["last_draft_id"] = str(selected.id)

    with col_detail:
        st.subheader("Draft summary")
        st.markdown(selected.summary_md or "_(no summary)_")
        st.subheader("Proposed changes")

        decisions: dict[int, str] = {}

        for i, change in enumerate(selected.proposed_changes):
            conf = float(change.get("confidence", 0))
            high = conf >= _HIGH_CONFIDENCE
            badge = "🟢 High" if high else ("🟡 Med" if conf >= 0.5 else "🔴 Low")
            with st.expander(
                f"#{i+1} • {change['op'].upper()} • {badge} ({conf:.0%})",
                expanded=not high,  # collapse high-conf rows by default to reduce noise
            ):
                cols = st.columns([1, 1, 3])
                # Pre-check approve only for high-confidence; conflicts are never pre-approved.
                default_approve = high and change["op"] != "conflict"
                with cols[0]:
                    approve = st.checkbox(
                        "Approve", key=f"approve_{selected.id}_{i}", value=default_approve,
                    )
                with cols[1]:
                    reject = st.checkbox(
                        "Reject", key=f"reject_{selected.id}_{i}", value=False,
                    )
                if approve and reject:
                    st.error("Pick approve OR reject, not both.")
                if approve:
                    decisions[i] = "approve"
                elif reject:
                    decisions[i] = "reject"

                st.markdown(f"**Reason:** {change.get('reason', '')}")
                st.markdown(f"**Evidence:** _{change.get('evidence_quote', '')}_")
                fields = change.get("fields") or {}
                if fields:
                    st.markdown("**Fields:**")
                    st.json(fields, expanded=False)
                if change["op"] == "update" and change.get("target_task_id"):
                    st.caption(f"Target task: `{change['target_task_id']}`")
                if change["op"] == "conflict":
                    st.warning(
                        f"⚠️ Conflict — agent found {len(change.get('candidate_task_ids', []))} "
                        "possible existing tasks. Use the Conflict view (next task)."
                    )

        st.markdown("---")
        c1, c2, c3 = st.columns([1, 1, 2])
        if c1.button("Approve all", key=f"approve_all_{selected.id}"):
            for i, ch in enumerate(selected.proposed_changes):
                if ch["op"] != "conflict":
                    decisions[i] = "approve"
                    st.session_state[f"approve_{selected.id}_{i}"] = True
                    st.session_state[f"reject_{selected.id}_{i}"] = False
            st.rerun()
        if c2.button("Reject all", key=f"reject_all_{selected.id}"):
            for i in range(len(selected.proposed_changes)):
                decisions[i] = "reject"
                st.session_state[f"reject_{selected.id}_{i}"] = True
                st.session_state[f"approve_{selected.id}_{i}"] = False
            st.rerun()

        if c3.button("Apply decisions", type="primary", key=f"apply_{selected.id}"):
            if not decisions:
                st.error("No decisions selected.")
                return
            try:
                PlannerService().apply_draft(
                    draft_id=selected.id, decisions=decisions, approver="reviewer",
                )
                st.success("Decisions applied. Tracker and Change Log are updated.")
                st.session_state.pop("last_draft_id", None)
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to apply: {exc}")
```

- [ ] **Step 2: Smoke-test**

Refresh, open Drafts, see the high-confidence row pre-checked, the low-confidence row not. Click Apply Decisions, then check the Tracker and Change Log pages — they should reflect the approved changes.

- [ ] **Step 3: Commit**

```bash
git add src/planner/ui/pages/drafts.py
git commit -m "feat(ui): add confidence-driven approve/reject and apply decisions"
```

---

### Task 27: Drafts page — first-class conflict resolution view

**Files:**
- Modify: `D:\CWB\src\planner\ui\pages\drafts.py`

- [ ] **Step 1: Replace the inline `Conflict` warning with a side-by-side view**

In `drafts.py`, replace the conflict warning block (the `if change["op"] == "conflict": st.warning(...)`) inside the change expander with a call to a new `_render_conflict_resolution` helper, and add the helper at the bottom of the file:

Within the expander loop, replace:
```python
if change["op"] == "conflict":
    st.warning(
        f"⚠️ Conflict — agent found {len(change.get('candidate_task_ids', []))} "
        "possible existing tasks. Use the Conflict view (next task)."
    )
```
with:
```python
if change["op"] == "conflict":
    _render_conflict_resolution(selected_id=selected.id, change_index=i, change=change)
```

Add at the bottom of the file:
```python
def _render_conflict_resolution(*, selected_id, change_index: int, change: dict) -> None:
    """Side-by-side view: agent's proposed item vs each existing-task candidate.

    The reviewer chooses Merge into a candidate (becomes an update) or
    Keep Separate (rewrites the change to op='create' so apply_draft will create a new task).
    """
    from planner.db import session_scope
    from planner.repositories import tasks_repo, drafts_repo

    candidates_ids = change.get("candidate_task_ids") or []
    st.error(f"⚠️ Conflict — {len(candidates_ids)} possible existing task(s). Resolve below.")
    with session_scope() as s:
        candidates = []
        for cid in candidates_ids:
            try:
                t = tasks_repo.get(s, uuid.UUID(cid))
                if t is not None:
                    candidates.append({
                        "id": str(t.id),
                        "title": t.title,
                        "owner": t.owner,
                        "due_date": t.due_date.isoformat() if t.due_date else None,
                        "status": t.status,
                    })
            except Exception:
                pass

    cols = st.columns([1] + [1] * len(candidates) if candidates else [1])
    with cols[0]:
        st.markdown("**Agent proposes:**")
        st.json(change.get("fields") or {}, expanded=True)

    for j, cand in enumerate(candidates):
        with cols[j + 1]:
            st.markdown(f"**Candidate #{j+1}:**")
            st.json(cand, expanded=True)
            if st.button(f"Merge into this one", key=f"merge_{selected_id}_{change_index}_{j}"):
                # Rewrite the change in-place: op=update, target_task_id=this candidate's id
                _rewrite_change(
                    draft_id=selected_id, change_index=change_index,
                    new_op="update", target_task_id=cand["id"],
                )
                st.rerun()

    if st.button(
        "Keep Separate (create a new task)",
        key=f"keep_separate_{selected_id}_{change_index}",
    ):
        _rewrite_change(
            draft_id=selected_id, change_index=change_index,
            new_op="create", target_task_id=None,
        )
        st.rerun()


def _rewrite_change(
    *, draft_id, change_index: int, new_op: str, target_task_id: str | None,
) -> None:
    from planner.db import session_scope
    from planner.repositories import drafts_repo

    with session_scope() as s:
        draft = drafts_repo.get(s, draft_id)
        if draft is None:
            return
        # Mutate the JSONB list in place
        changes = list(draft.proposed_changes)
        ch = dict(changes[change_index])
        ch["op"] = new_op
        ch["target_task_id"] = target_task_id
        ch["candidate_task_ids"] = []
        ch["reason"] = (ch.get("reason", "") + " [Reviewer resolved conflict.]").strip()
        changes[change_index] = ch
        draft.proposed_changes = changes
        s.flush()
```

- [ ] **Step 2: Smoke-test**

Create a note that re-mentions an already-existing task with slightly different wording (e.g., paste the followup email after creating the migration task from the sprint planning note). Open Drafts → confirm the conflict row shows side-by-side candidates. Click Merge → row becomes an update. Apply.

- [ ] **Step 3: Commit**

```bash
git add src/planner/ui/pages/drafts.py
git commit -m "feat(ui): add side-by-side conflict resolution with merge/keep separate"
```

---

### Task 28: Tracker page

**Files:**
- Modify: `D:\CWB\src\planner\ui\pages\tracker.py`

- [ ] **Step 1: Replace the tracker stub with the real page**

```python
"""Tracker page: filterable view of the current plan with urgent-tasks panel."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from planner.db import session_scope
from planner.repositories import tasks_repo


def render() -> None:
    st.title("Tracker")
    st.caption("The current state of the plan. Updated whenever a draft is approved.")

    with session_scope() as s:
        tasks = tasks_repo.list_all(s)
        rows = [{
            "id": str(t.id), "title": t.title, "owner": t.owner or "",
            "due_date": t.due_date, "status": t.status, "priority": t.priority,
            "updated_at": t.updated_at,
        } for t in tasks]

    if not rows:
        st.info("No tasks yet. Process a note in the Inbox and approve a draft to populate the plan.")
        return

    df = pd.DataFrame(rows)
    today = date.today()
    df["overdue"] = df["due_date"].apply(lambda d: bool(d and d < today))
    df["due_soon"] = df["due_date"].apply(lambda d: bool(d and today <= d <= today + timedelta(days=3)))

    # Urgent panel
    urgent = df[(df["overdue"]) | ((df["priority"] == "high") & (df["status"] != "done"))]
    if not urgent.empty:
        st.subheader("⚠️ Urgent")
        st.dataframe(
            urgent[["title", "owner", "due_date", "status", "priority"]],
            hide_index=True, use_container_width=True,
        )

    # Filters
    st.subheader("All tasks")
    col1, col2, col3 = st.columns(3)
    status_filter = col1.multiselect("Status", sorted(df["status"].unique()))
    owner_filter = col2.multiselect("Owner", sorted(df["owner"].unique()))
    only_open = col3.checkbox("Hide done", value=True)

    filtered = df.copy()
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if owner_filter:
        filtered = filtered[filtered["owner"].isin(owner_filter)]
    if only_open:
        filtered = filtered[filtered["status"] != "done"]

    def _row_style(row):
        if row["overdue"]:
            return ["background-color: #ffebee"] * len(row)
        if row["due_soon"]:
            return ["background-color: #fff3e0"] * len(row)
        if row["status"] == "done":
            return ["color: #999"] * len(row)
        return [""] * len(row)

    show_cols = ["title", "owner", "due_date", "status", "priority", "updated_at"]
    st.dataframe(
        filtered[show_cols].style.apply(_row_style, axis=1),
        hide_index=True, use_container_width=True,
    )
```

- [ ] **Step 2: Smoke-test** — refresh the Tracker page after applying a draft. Expected: urgent panel for overdue/high-priority, full table with color cues.

- [ ] **Step 3: Commit**

```bash
git add src/planner/ui/pages/tracker.py
git commit -m "feat(ui): implement Tracker page with filters, urgent panel, color cues"
```

---

### Task 29: Gantt page

**Files:**
- Modify: `D:\CWB\src\planner\ui\pages\gantt.py`

- [ ] **Step 1: Replace the gantt stub with a Plotly timeline**

```python
"""Gantt page: Plotly timeline of all tasks colored by status."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from planner.db import session_scope
from planner.repositories import tasks_repo


def render() -> None:
    st.title("Gantt")
    st.caption("Visual timeline. Bars span from created_at to due_date (or due_date - 7 days if no created bar to show).")

    with session_scope() as s:
        tasks = tasks_repo.list_all(s)

    if not tasks:
        st.info("No tasks yet.")
        return

    rows = []
    for t in tasks:
        if t.due_date is None:
            continue  # cannot place on a timeline without a due date
        start = (t.created_at.date() if t.created_at else (t.due_date - timedelta(days=7)))
        if start >= t.due_date:
            start = t.due_date - timedelta(days=1)
        rows.append({
            "Task": t.title,
            "Owner": t.owner or "—",
            "Start": pd.Timestamp(start),
            "Finish": pd.Timestamp(t.due_date),
            "Status": t.status,
        })

    if not rows:
        st.info("No tasks have due dates yet — Gantt cannot render.")
        return

    df = pd.DataFrame(rows)
    fig = px.timeline(
        df, x_start="Start", x_end="Finish", y="Task", color="Status",
        hover_data=["Owner"],
        color_discrete_map={
            "not_started": "#90caf9",
            "in_progress": "#42a5f5",
            "blocked": "#ef5350",
            "done": "#a5d6a7",
        },
    )
    fig.update_yaxes(autorange="reversed")
    fig.add_vline(x=pd.Timestamp(date.today()), line_dash="dash", line_color="black",
                  annotation_text="today", annotation_position="top right")
    st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 2: Smoke-test** — open Gantt; expected: bars per task colored by status with a "today" line.

- [ ] **Step 3: Commit**

```bash
git add src/planner/ui/pages/gantt.py
git commit -m "feat(ui): implement Gantt page using plotly timeline"
```

---

### Task 30: Change Log page with weekly digest

**Files:**
- Modify: `D:\CWB\src\planner\ui\pages\change_log.py`

- [ ] **Step 1: Replace the change_log stub**

```python
"""Change Log page: audit trail with diff view + weekly executive digest."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from planner.db import session_scope
from planner.repositories import change_log_repo
from planner.service import PlannerService


def render() -> None:
    st.title("Change Log")
    st.caption("Every applied change with before/after snapshots and the source evidence.")

    col_btn, _ = st.columns([1, 4])
    if col_btn.button("📰 Generate weekly digest"):
        with st.spinner("Summarising the last 7 days..."):
            try:
                summary = PlannerService().weekly_digest()
                st.session_state["weekly_digest_md"] = summary
            except Exception as exc:
                st.error(f"Digest failed: {exc}")
    if "weekly_digest_md" in st.session_state:
        st.markdown("### Weekly digest")
        st.markdown(st.session_state["weekly_digest_md"])
        st.markdown("---")

    with session_scope() as s:
        entries = change_log_repo.list_recent(s, limit=200)
        rows = []
        for e in entries:
            rows.append({
                "applied_at": e.applied_at,
                "op": e.op,
                "task_id": str(e.task_id) if e.task_id else "",
                "diff": _format_diff(e.before, e.after),
                "evidence": e.evidence_quote,
                "approved_by": e.approved_by,
            })

    if not rows:
        st.info("No applied changes yet.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, use_container_width=True)


def _format_diff(before: dict | None, after: dict | None) -> str:
    """Render a compact field-level diff as a single string."""
    if before is None and after is not None:
        return "+ " + ", ".join(f"{k}={v!r}" for k, v in after.items() if v is not None)
    if after is None and before is not None:
        return "− " + ", ".join(f"{k}={v!r}" for k, v in before.items() if v is not None)
    if before is None or after is None:
        return ""
    parts = []
    keys = set(before) | set(after)
    for k in sorted(keys):
        b, a = before.get(k), after.get(k)
        if b != a:
            parts.append(f"{k}: {b!r} → {a!r}")
    return "; ".join(parts)
```

- [ ] **Step 2: Smoke-test** — apply at least one draft, open Change Log; click Generate weekly digest and confirm a markdown summary appears.

- [ ] **Step 3: Commit**

```bash
git add src/planner/ui/pages/change_log.py
git commit -m "feat(ui): implement Change Log page with diff view and weekly digest button"
```

---

### Task 31: Sample-data loader

**Files:**
- Create: `D:\CWB\data\sample\meetings\01_sprint_planning.txt`
- Create: `D:\CWB\data\sample\meetings\02_followup_email.txt`
- Create: `D:\CWB\data\sample\meetings\03_status_check.txt`
- Modify: `D:\CWB\src\planner\ui\sample_data.py`

- [ ] **Step 1: Add three curated sample notes**

`D:\CWB\data\sample\meetings\01_sprint_planning.txt`:
```
Sprint planning - 2026-04-29

Attendees: Alex (PM), Priya (Backend), Marco (Frontend), Lin (QA)

Decisions:
- Priya will own the Postgres migration. Target ship date: 2026-05-06. High priority.
- Marco picks up the new dashboard skeleton. No firm date yet, but we want a demo by 2026-05-12.
- The customer-export script that Alex started last week is now blocked
  on a billing-team API change.
- Lin will write QA acceptance criteria for the migration. Due 2026-05-04.
```

`D:\CWB\data\sample\meetings\02_followup_email.txt`:
```
Subject: Re: Sprint planning follow-up
From: priya@sj.example
Date: 2026-04-30

Quick correction from yesterday: the Postgres migration target should be
2026-05-08, not 2026-05-06. I had a calendar conflict on the original
date. Please update the tracker.

Also flagging: Marco mentioned offline that the dashboard skeleton may slip
to 2026-05-15 if the design review happens late.
```

`D:\CWB\data\sample\meetings\03_status_check.txt`:
```
Status check - 2026-05-01

Attendees: Alex, Priya, Marco

- Postgres migration: in progress, on track for 2026-05-08.
- Dashboard skeleton: design review confirmed for 2026-05-05; date holds at 2026-05-15.
- Customer export script: still blocked. Alex pinged the billing team again.
- New action: Marco to draft the Gantt-view spec by 2026-05-07.
```

- [ ] **Step 2: Replace `sample_data.py` with a real loader**

```python
"""Loads curated sample meeting notes through the full agent pipeline."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from planner.service import PlannerService


_SAMPLES_DIR = Path(__file__).resolve().parents[3] / "data" / "sample" / "meetings"


_FILES = [
    ("01_sprint_planning.txt", "Sprint planning",       "meeting", date(2026, 4, 29), ["Alex", "Priya", "Marco", "Lin"]),
    ("02_followup_email.txt",  "Sprint planning follow-up", "email",   date(2026, 4, 30), ["Priya"]),
    ("03_status_check.txt",    "Status check",          "meeting", date(2026, 5, 1),  ["Alex", "Priya", "Marco"]),
]


def load_samples() -> None:
    """Ingest each sample note and run the pipeline. Drafts land in Pending."""
    service = PlannerService()
    for filename, title, source, mdate, attendees in _FILES:
        path = _SAMPLES_DIR / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        note = service.ingest_note(
            text=text, source=source, title=title,
            meeting_date=mdate, attendees=attendees,
        )
        try:
            service.run_pipeline(note_id=note.id)
        except Exception:
            # don't fail the whole load if one note errors
            continue
```

- [ ] **Step 3: Smoke-test** — click Generate Sample Data in the sidebar; expected: three pending drafts created, visible on the Drafts page.

- [ ] **Step 4: Commit**

```bash
git add data/sample/ src/planner/ui/sample_data.py
git commit -m "feat(ui): add sample-data loader for instant demo readiness"
```

---

### Task 32: Dockerfile and .dockerignore

**Files:**
- Create: `D:\CWB\Dockerfile`
- Create: `D:\CWB\.dockerignore`

- [ ] **Step 1: Write the `Dockerfile`**

```dockerfile
# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install -e .

EXPOSE 8501

# Run migrations on startup, then launch Streamlit.
CMD bash -lc "alembic upgrade head && streamlit run src/planner/ui/app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true"
```

- [ ] **Step 2: Write `.dockerignore`**

```
.git
.venv
__pycache__
*.pyc
.pytest_cache
.mypy_cache
.ruff_cache
.env
data/local
docs
tests
*.egg-info
build
dist
```

- [ ] **Step 3: Build the image locally**

```bash
docker build -t sjplanner:local .
```

Expected: build succeeds.

- [ ] **Step 4: Run the image against the local Postgres**

```bash
docker run --rm -p 8501:8501 \
  --env DATABASE_URL=postgresql+psycopg://planner:planner@host.docker.internal:5432/planner \
  --env AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT \
  --env AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY \
  --env AZURE_OPENAI_API_VERSION=2024-08-01-preview \
  --env AZURE_OPENAI_DEPLOYMENT_MAIN=gpt-4o \
  --env AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4o-mini \
  sjplanner:local
```

Open http://localhost:8501 — expected: same app as before, status indicators green.

- [ ] **Step 5: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "build: add Dockerfile and dockerignore for container deployment"
```

---

### Task 33: Azure provisioning script

**Files:**
- Create: `D:\CWB\infra\deploy.sh`

- [ ] **Step 1: Write the deployment script**

```bash
#!/usr/bin/env bash
# Provision Azure resources and deploy the SJ Planner Agent container.
#
# Required environment variables (set before running):
#   APP_NAME            unique short name, e.g. sjplanner-mm7f3k
#   LOCATION            e.g. eastus2
#   AOAI_ENDPOINT       https://<your-aoai>.openai.azure.com/
#   AOAI_KEY            azure openai key
#   PG_ADMIN_PASSWORD   admin password for the Postgres flexible server (16+ chars, mixed)
#
# Idempotent: re-running updates the container app to a new image version.

set -euo pipefail

: "${APP_NAME:?must set APP_NAME}"
: "${LOCATION:?must set LOCATION (e.g. eastus2)}"
: "${AOAI_ENDPOINT:?must set AOAI_ENDPOINT}"
: "${AOAI_KEY:?must set AOAI_KEY}"
: "${PG_ADMIN_PASSWORD:?must set PG_ADMIN_PASSWORD}"

RG="${APP_NAME}-rg"
ACR="${APP_NAME//-/}acr"  # ACR names cannot have dashes
ENV_NAME="${APP_NAME}-env"
PG_SERVER="${APP_NAME}-pg"
PG_DB="planner"
PG_ADMIN="planner_admin"
IMAGE_TAG="$(date +%Y%m%d%H%M%S)"

echo "==> Resource group"
az group create --name "$RG" --location "$LOCATION" --output none

echo "==> Container Registry"
az acr create --resource-group "$RG" --name "$ACR" --sku Basic --admin-enabled true --output none

echo "==> Build and push image"
az acr build --registry "$ACR" --image "sjplanner:$IMAGE_TAG" .

echo "==> Postgres Flexible Server (Burstable B1ms)"
az postgres flexible-server create \
    --resource-group "$RG" --name "$PG_SERVER" \
    --location "$LOCATION" \
    --admin-user "$PG_ADMIN" --admin-password "$PG_ADMIN_PASSWORD" \
    --sku-name Standard_B1ms --tier Burstable --storage-size 32 \
    --version 16 --yes --output none --public-access 0.0.0.0 || true
az postgres flexible-server db create --resource-group "$RG" --server-name "$PG_SERVER" --database-name "$PG_DB" --output none || true

PG_HOST="${PG_SERVER}.postgres.database.azure.com"
DATABASE_URL="postgresql+psycopg://${PG_ADMIN}:${PG_ADMIN_PASSWORD}@${PG_HOST}:5432/${PG_DB}?sslmode=require"

echo "==> Container Apps environment"
az containerapp env create --resource-group "$RG" --name "$ENV_NAME" --location "$LOCATION" --output none

ACR_LOGIN_SERVER="$(az acr show --name "$ACR" --query loginServer -o tsv)"
ACR_USERNAME="$(az acr credential show --name "$ACR" --query username -o tsv)"
ACR_PASSWORD="$(az acr credential show --name "$ACR" --query 'passwords[0].value' -o tsv)"

echo "==> Container App"
az containerapp create \
    --resource-group "$RG" --name "$APP_NAME" \
    --environment "$ENV_NAME" \
    --image "${ACR_LOGIN_SERVER}/sjplanner:${IMAGE_TAG}" \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_USERNAME" --registry-password "$ACR_PASSWORD" \
    --target-port 8501 --ingress external \
    --min-replicas 1 --max-replicas 1 \
    --secrets "pg-url=$DATABASE_URL" "aoai-key=$AOAI_KEY" \
    --env-vars \
        "DATABASE_URL=secretref:pg-url" \
        "AZURE_OPENAI_ENDPOINT=$AOAI_ENDPOINT" \
        "AZURE_OPENAI_API_KEY=secretref:aoai-key" \
        "AZURE_OPENAI_API_VERSION=2024-08-01-preview" \
        "AZURE_OPENAI_DEPLOYMENT_MAIN=gpt-4o" \
        "AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4o-mini" \
    --output none \
  || az containerapp update \
        --resource-group "$RG" --name "$APP_NAME" \
        --image "${ACR_LOGIN_SERVER}/sjplanner:${IMAGE_TAG}" \
        --output none

URL="$(az containerapp show --resource-group "$RG" --name "$APP_NAME" --query 'properties.configuration.ingress.fqdn' -o tsv)"
echo
echo "Live URL:  https://${URL}"
```

- [ ] **Step 2: Make it executable and commit**

```bash
chmod +x infra/deploy.sh
git add infra/deploy.sh
git commit -m "infra: add Azure provisioning + deploy script"
```

---

### Task 34: Provision Azure resources and deploy

**Files:** none (operational task)

- [ ] **Step 1: Authenticate**

```bash
az login
az account show
```

Expected: shows your Azure subscription.

- [ ] **Step 2: Set environment variables**

```bash
export APP_NAME="sjplanner-<your-suffix>"   # globally unique short name
export LOCATION="eastus2"
export AOAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT"
export AOAI_KEY="$AZURE_OPENAI_API_KEY"
export PG_ADMIN_PASSWORD="$(openssl rand -base64 18)Aa1!"   # robust random
echo "PG password: $PG_ADMIN_PASSWORD"   # save this somewhere safe
```

- [ ] **Step 3: Run the deploy script**

```bash
./infra/deploy.sh
```

Expected: provisions resource group, ACR, Postgres, Container Apps environment, and the app itself. Final line prints `Live URL: https://...`. Save this URL — it goes in the README and the submission.

If a step fails midway, re-run the script — every block is idempotent.

- [ ] **Step 4: Smoke-test the deployed app**

Open the live URL. Expected: the Streamlit app loads. Status indicators should both be green. Click Generate Sample Data — confirm drafts appear on the Drafts page.

- [ ] **Step 5: Commit a NOTES file with the live URL**

`D:\CWB\infra\DEPLOYED_URL.md`:
```markdown
# Deployed URL

Live: https://<your-app>.<region>.azurecontainerapps.io

Provisioned 2026-05-02. Region: eastus2.
```

```bash
git add infra/DEPLOYED_URL.md
git commit -m "docs: record the deployed Container Apps URL"
```

---

### Task 35: Architecture diagram

**Files:**
- Create: `D:\CWB\docs\architecture.md` (uses Mermaid; renders on GitHub)
- Create: `D:\CWB\docs\architecture.png` (exported PNG for the README)

- [ ] **Step 1: Write the Mermaid source**

`D:\CWB\docs\architecture.md`:
```markdown
# Architecture

```mermaid
flowchart TB
    subgraph Browser
        U[User]
    end

    subgraph "Azure Container Apps"
        UI[Streamlit UI<br/>Inbox | Drafts | Tracker | Gantt | Change Log]
        SVC[PlannerService<br/>orchestration]
        AGENT[PlannerAgent<br/>extract / classify / draft / digest]
        REPO[Repository layer]
    end

    subgraph "Azure Managed"
        AOAI[(Azure OpenAI<br/>gpt-4o + gpt-4o-mini)]
        PG[(Azure Database for PostgreSQL<br/>Flexible Server)]
    end

    U -->|HTTPS| UI
    UI --> SVC
    SVC --> AGENT
    SVC --> REPO
    AGENT --> AOAI
    REPO --> PG
```
```

- [ ] **Step 2: Export PNG**
Open `docs/architecture.md` on GitHub after the first push, screenshot the rendered diagram, and save as `docs/architecture.png`. Or use the Mermaid CLI if installed: `mmdc -i docs/architecture.md -o docs/architecture.png`.

- [ ] **Step 3: Commit**

```bash
git add docs/architecture.md docs/architecture.png
git commit -m "docs: add architecture diagram (mermaid + png)"
```

---

### Task 36: Capture screenshots

**Files:**
- Create: `D:\CWB\docs\screenshots\01-inbox.png`
- Create: `D:\CWB\docs\screenshots\02-drafts.png`
- Create: `D:\CWB\docs\screenshots\03-tracker.png`
- Create: `D:\CWB\docs\screenshots\04-gantt.png`
- Create: `D:\CWB\docs\screenshots\05-change-log.png`
- Create: `D:\CWB\docs\screenshots\06-conflict-resolution.png`

- [ ] **Step 1: Load sample data on the deployed app**
Open the live URL → click Generate Sample Data → approve the first draft so the Tracker is populated.

- [ ] **Step 2: Capture each screenshot**
Use Win+Shift+S to capture each page after triggering the relevant view. Save into `docs/screenshots/`.

- [ ] **Step 3: Commit**

```bash
git add docs/screenshots/
git commit -m "docs: capture screenshots for README and pitch"
```

---

### Task 37: README final polish

**Files:**
- Modify: `D:\CWB\README.md`

- [ ] **Step 1: Replace `README.md` with the full submission version**

```markdown
# SJ Project Planner Agent

> Agentic AI assistant that converts unstructured project conversations
> into structured, auditable planning updates with a human-in-the-loop
> approval workflow.
>
> Submission for the **Microsoft Code Without Barriers Hackathon 2026** —
> challenge: SJ Project Planner Agent.

## Live demo

🔗 **https://<your-app>.<region>.azurecontainerapps.io**

## Pitch video

🎬 **https://youtu.be/<your-video-id>** (5 min)

## What it does

Project plans drift out of sync with reality because decisions live in
meetings and emails, not in the tracker. This assistant ingests a
meeting note (or email, or chat snippet), extracts the task-shaped items
discussed, compares them to the current plan, and proposes a plan
update — never silently applies it. A human reviewer approves, rejects,
or merges proposed changes one by one. Every applied change carries an
**evidence quote** pointing back to the exact source text.

### Key features

- **Meeting-to-plan translation.** Extract tasks, owners, due dates,
  status signals, and dependency hints from natural-language notes.
- **Three-way classification.** Each extracted item is identified as a
  brand-new task, an update to an existing task, or a conflict needing
  clarification.
- **Plan Update Drafts.** Every run produces a draft you can review
  before any official tracker change.
- **Human-in-the-loop approval.** Per-row approve / reject / edit, with
  bulk controls.
- **First-class conflict resolution.** Side-by-side view of the proposed
  item against existing-task candidates, with Merge / Keep Separate.
- **Confidence-driven UX.** High-confidence changes are pre-checked;
  low-confidence ones are flagged and require explicit click.
- **Auditable Change Log.** Every applied change records the before /
  after snapshot and the source evidence.
- **Weekly executive digest.** One click summarises the last seven days
  of plan changes for stakeholder reporting.
- **Live Tracker + Gantt views.** Filterable table with overdue/urgent
  cues; Plotly timeline coloured by status with a "today" marker.

## Architecture

![Architecture](docs/architecture.png)

Single Streamlit container deployed to **Azure Container Apps**, backed
by **Azure Database for PostgreSQL Flexible Server** and **Azure OpenAI**
(GPT-4o for drafting / classification, GPT-4o-mini for extraction).

The application is split into four units with strict one-way
dependencies:

- `planner.ui` — Streamlit pages, no business logic
- `planner.service` — orchestrates the ingest → extract → classify →
  draft → apply pipeline; transactional commits
- `planner.agent` — LLM tool wrappers with Pydantic-validated structured
  outputs
- `planner.repositories` — typed CRUD over the four planner tables

See [`docs/superpowers/specs/2026-05-01-sj-project-planner-agent-design.md`](docs/superpowers/specs/2026-05-01-sj-project-planner-agent-design.md)
for the full design spec and
[`docs/architecture.md`](docs/architecture.md) for the diagram source.

## Screenshots

| Inbox | Drafts | Tracker |
|---|---|---|
| ![](docs/screenshots/01-inbox.png) | ![](docs/screenshots/02-drafts.png) | ![](docs/screenshots/03-tracker.png) |

| Gantt | Change Log | Conflict Resolution |
|---|---|---|
| ![](docs/screenshots/04-gantt.png) | ![](docs/screenshots/05-change-log.png) | ![](docs/screenshots/06-conflict-resolution.png) |

## Tech stack

| Layer | Technology |
|---|---|
| LLM | Azure OpenAI (GPT-4o + GPT-4o-mini), Microsoft Agent Framework patterns via the `openai` SDK with native tool-calling |
| Storage | Azure Database for PostgreSQL Flexible Server (with SQLAlchemy 2 + Alembic) |
| UI | Streamlit + Plotly |
| Deployment | Azure Container Apps + Azure Container Registry |
| Lang / runtime | Python 3.12 |
| Testing | pytest (unit + live, marked separately) |
| CI | GitHub Actions (lint, mypy, unit tests against ephemeral Postgres) |

## Run locally

Prerequisites: Python 3.12, Docker, an Azure OpenAI resource with
`gpt-4o` and `gpt-4o-mini` deployments.

```bash
# 1. Clone
git clone https://github.com/<your-handle>/<repo>.git
cd <repo>

# 2. Local Postgres
docker compose up -d postgres

# 3. Python env
python -m venv .venv
source .venv/Scripts/activate    # Git Bash on Windows
pip install -e ".[dev]"

# 4. Configure Azure OpenAI access
cp .env.example .env
# edit .env to fill in AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY

# 5. Apply migrations
alembic upgrade head

# 6. Run
streamlit run src/planner/ui/app.py
```

Open http://localhost:8501 and click **Generate sample data** in the
sidebar to populate the demo.

## Deploy to Azure

```bash
export APP_NAME="sjplanner-<your-suffix>"
export LOCATION="eastus2"
export AOAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT"
export AOAI_KEY="$AZURE_OPENAI_API_KEY"
export PG_ADMIN_PASSWORD="<a-strong-password>"

./infra/deploy.sh
```

The script provisions a resource group, ACR, Postgres Flexible Server,
Container Apps environment, and the app. It prints the live URL on
completion. Re-running deploys a fresh image.

## Tests

```bash
# Unit tests (mocked LLM, ephemeral Postgres)
pytest -m "not live" -v

# Live tests (real Azure OpenAI; small cost)
pytest -m live -v
```

## AI tool usage disclosure

Per the hackathon's Generative AI Tools rule, this submission was built
with the help of:

- **Claude Code (Anthropic)** — used for design, planning, and code
  generation across the entire project. The full design spec
  (`docs/superpowers/specs/2026-05-01-sj-project-planner-agent-design.md`)
  and implementation plan
  (`docs/superpowers/plans/2026-05-01-sj-project-planner-agent-implementation.md`)
  were collaboratively written with Claude.
- **Azure OpenAI (GPT-4o, GPT-4o-mini)** — runs inside the application
  itself as the LLM behind every agent tool.

No third-party AI-generated assets contain proprietary or confidential
information.

## License

Hackathon submission — all rights reserved by the author. The
underlying source code is provided for evaluation by the hackathon
judges.
```

- [ ] **Step 2: Replace placeholders**
Find every `<your-...>` placeholder and fill in real values (live URL, video URL once recorded, GitHub handle, repo name, suffix, password instructions).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: write submission-grade README with screenshots and disclosure"
```

---

### Task 38: Pitch video script and recording

**Files:**
- Create: `D:\CWB\docs\pitch_script.md`

- [ ] **Step 1: Write the script (5 minutes target, ~750 words)**

`D:\CWB\docs\pitch_script.md`:
```markdown
# Pitch Video Script — SJ Project Planner Agent (5 minutes)

Target length: 5:00. Delivered in English. Cover problem, solution,
key features, and the judging criteria explicitly.

## 0:00 – 0:30 — Hook & Problem

> Project plans drift out of sync with reality. Decisions get made in
> meetings and emails — new tasks, owner changes, date shifts — and
> unless someone manually updates the tracker, those decisions never
> reach the official schedule. The result is governance gaps,
> confused stakeholders, and rework.
>
> The SJ Project Planner Agent is an agentic AI assistant that
> translates unstructured conversation into structured plan updates,
> while keeping a human firmly in control.

(Show slide: problem statement bullet points overlaid on a stale Gantt chart.)

## 0:30 – 1:00 — What it does, in one sentence

> Paste a meeting note. The agent extracts the tasks, owners, and
> dates that were discussed, compares them to the current plan,
> and proposes an update — never applies it silently. A human
> reviews, approves, or rejects each change before it reaches the
> tracker.

(Show slide: end-to-end flow diagram from Inbox to Change Log.)

## 1:00 – 2:30 — Live demo

(Screen capture of the deployed app.)

> Here's the live application running on Azure Container Apps.
>
> I'll click Generate Sample Data — three meeting notes load, the
> agent runs the pipeline on each one.
>
> Let's open Drafts. The first draft has four proposed changes.
> Notice the agent has marked the high-confidence ones in green and
> pre-checked them for approval. The low-confidence change is in red
> and requires my explicit click. That's confidence-driven UX —
> reduces reviewer fatigue, surfaces uncertainty.
>
> Now look at this conflict — the agent isn't sure if "Postgres
> migration" matches an existing task. It opens a side-by-side view
> showing the proposed change against each candidate. I can Merge,
> or Keep Separate.
>
> I'll merge, then click Apply Decisions.
>
> Open the Tracker — the plan now reflects the approved changes,
> with overdue and high-priority items called out in the urgent
> panel.
>
> The Gantt page renders the timeline, colored by status.
>
> The Change Log records every applied change with before/after
> snapshots and the evidence quote from the source meeting note.
> Every plan edit traces back to the exact conversation that drove
> it. Click Generate Weekly Digest — the agent summarises the last
> seven days for stakeholder reporting.

## 2:30 – 3:30 — Architecture

> Under the hood: a single Streamlit container on Azure Container
> Apps, backed by Azure Database for PostgreSQL and Azure OpenAI.
>
> The application is split into four layers with strict one-way
> dependencies. The UI knows nothing about LLMs. The service
> orchestrates the workflow. The agent wraps four prompted tools
> with Pydantic-validated structured outputs. The repository layer
> handles persistence.
>
> Every plan change is transactional. Every committed change writes
> a before/after snapshot to the audit log. Every audit entry
> carries the evidence quote.

(Show architecture diagram for ~10 seconds.)

## 3:30 – 4:30 — How it scores against the judging criteria

> Technical Merit — clean four-layer architecture, structured-output
> LLM calls with schema validation, transactional commits with full
> audit logging, GitHub Actions CI.
>
> Innovation and Creativity — confidence-driven approval UX,
> first-class conflict resolution, and the evidence-quote pinning on
> every plan change. Every update is auditable back to the source.
>
> Potential Impact — directly addresses the meeting-to-plan
> translation gap that the problem statement identifies.
> Governance-grade audit trail. Lightweight enough for individual
> teams to adopt, structured enough for stakeholder reporting.
>
> Feasibility — runs on Azure free-tier resources, deployable in
> minutes, fits a small team or solo PM workflow.

## 4:30 – 5:00 — Close

> The repository, README, and architecture diagram are linked below.
> Live demo URL is in the description.
>
> Built solo for the Code Without Barriers Hackathon 2026 with
> Claude Code as the development collaborator and Azure OpenAI as
> the runtime LLM.
>
> Thank you.
```

- [ ] **Step 2: Record and upload**
Use OBS Studio (free) or Windows Game Bar (Win+G) to record. Capture screen + microphone. Aim for 5:00 ± 0:15. Upload as Unlisted on YouTube. Copy the URL into the README placeholder.

- [ ] **Step 3: Commit**

```bash
git add docs/pitch_script.md README.md
git commit -m "docs: add pitch video script and link the recorded video"
```

---

### Task 39: Final submission

**Files:** none (operational task)

- [ ] **Step 1: Final repo state check**

```bash
git status
git log --oneline | wc -l
```

Expected: clean working tree, 30+ commits.

- [ ] **Step 2: Push to GitHub**
Create a public repository on github.com, then:
```bash
git remote add origin https://github.com/<your-handle>/sj-planner-agent.git
git branch -M main
git push -u origin main
```

- [ ] **Step 3: Verify the deployed URL still works**
Open the live URL one more time. Click Generate Sample Data, walk through one approval, confirm Tracker updates. If broken, fix before submitting.

- [ ] **Step 4: Submit on the hackathon portal**
Provide:
- Project Description URL = the deployed app URL
- GitHub repository URL
- YouTube pitch video URL
- Solution Architecture (optional) = link to `docs/architecture.md` in the repo
- Demo Link (optional) = same as the project description URL

Submit before **2026-05-03, 11:59 PM SGT.**

---

## Day-2 Stretch (only if material slack appears)

If the entire scope above lands by Day 2 evening with hours to spare,
re-open these features from the spec and pick at most one to add:

- **Replay mode** — load the three sample notes in chronological
  order, animate the plan + Gantt evolving meeting-by-meeting. Add a
  page-level "Replay demo" button that calls `apply_draft` for each
  sample's first draft sequentially, with a `time.sleep(2)` between
  steps, while the Tracker auto-refreshes.
- **Bidirectional traceability** — make every Tracker row clickable;
  on click, show every change_log entry and meeting_note that touched
  the task in a side drawer.

Do **not** start either of these on Day 3 — Day 3 is reserved for
README, screenshots, video, and submission.
