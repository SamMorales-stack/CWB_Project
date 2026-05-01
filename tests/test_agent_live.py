"""Live tests against real Azure OpenAI. Run with: pytest -m live -v

These tests cost a small amount of Azure credits (~$0.01) and require a
working .env with AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY set.
"""
from __future__ import annotations

import pytest

from planner.agent.planner_agent import PlannerAgent

pytestmark = pytest.mark.live

_NOTE_SPRINT = """
Sprint planning - 2026-04-29

Attendees: Alex (PM), Priya (Backend), Marco (Frontend)

Decisions:
- Priya will own the Postgres migration. Target ship date: 2026-05-08. High priority.
- Marco picks up the new dashboard skeleton. No firm date yet.
- The customer-export script that Alex started is now blocked on a billing-team API change.
""".strip()

_NOTE_FOLLOWUP = """
Subject: Re: Sprint planning follow-up
From: priya@sj.example
Date: 2026-04-30

Quick correction from yesterday: the Postgres migration target should be
2026-05-10, not 2026-05-08. I had a calendar conflict.
Please update the tracker.
""".strip()


def test_extract_finds_tasks_in_sprint_note():
    agent = PlannerAgent()
    items = agent.extract(
        note_text=_NOTE_SPRINT,
        source="meeting",
        meeting_date="2026-04-29",
        title="Sprint planning",
    )
    assert len(items) >= 2
    titles_lower = " ".join(i.title.lower() for i in items)
    assert "migration" in titles_lower or "postgres" in titles_lower
    assert all(i.evidence_quote.strip() for i in items), "every item must have an evidence quote"


def test_extract_finds_date_in_followup_email():
    agent = PlannerAgent()
    items = agent.extract(
        note_text=_NOTE_FOLLOWUP,
        source="email",
        meeting_date="2026-04-30",
        title="Sprint follow-up",
    )
    assert len(items) >= 1
    dates = [i.due_date.isoformat() for i in items if i.due_date]
    assert any(d == "2026-05-10" for d in dates), f"expected 2026-05-10 in {dates}"


def test_classify_change_detects_update(db_not_needed=None):
    from planner.agent import tools
    from planner.agent.schemas import CandidateMatch, ExtractedItem

    agent = PlannerAgent()
    item = ExtractedItem(
        title="Postgres migration",
        owner="Priya",
        due_date="2026-05-10",
        evidence_quote="the Postgres migration target should be 2026-05-10",
        confidence=0.9,
    )
    candidates = [
        CandidateMatch(
            task_id="00000000-0000-0000-0000-000000000001",
            title="Migrate database",
            owner="Priya",
            status="in_progress",
            due_date="2026-05-08",
        )
    ]
    result = tools.classify_change(item=item, candidates=candidates)
    assert result.op in ("update", "conflict"), f"expected update/conflict, got {result.op}"
    assert result.confidence > 0.5
