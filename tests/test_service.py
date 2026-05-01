"""Tests for PlannerService using a mocked agent and a live database."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from planner.agent.schemas import DraftSummary, ExtractedItem, ProposedChange
from planner.repositories import change_log_repo, drafts_repo, tasks_repo
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
    agent.draft.return_value = DraftSummary(
        summary_md="1 new task proposed: Migrate database (Priya)."
    )
    agent.weekly_digest.return_value = DraftSummary(
        summary_md="## New work\n- Migrate database (Priya)"
    )
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

    service.apply_draft(draft_id=draft.id, decisions={0: "approve"}, approver="reviewer")

    all_tasks = tasks_repo.list_all(session)
    assert len(all_tasks) == 1
    assert all_tasks[0].title == "Migrate database"

    log = change_log_repo.list_recent(session, limit=10)
    assert len(log) == 1
    assert log[0].op == "create"
    assert log[0].after["title"] == "Migrate database"

    d = drafts_repo.get(session, draft.id)
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

    d = drafts_repo.get(session, draft.id)
    assert d.status == "rejected"
    assert tasks_repo.list_all(session) == []


def test_weekly_digest_returns_markdown(mock_agent, session):
    service = PlannerService(agent=mock_agent)
    result = service.weekly_digest()
    # With empty DB, should return a "no changes" string without calling the agent
    assert isinstance(result, str)
