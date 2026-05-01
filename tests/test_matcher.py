"""Tests for the candidate-match converter (mocks the repository)."""
from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from planner.agent.schemas import ExtractedItem
from planner.matcher import build_candidate_matches


def _fake_task(title: str, owner: str | None = None, status: str = "in_progress",
               due_date: date | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(), title=title, owner=owner, status=status, due_date=due_date,
    )


def test_build_candidate_matches_calls_repo_with_combined_query():
    fake_repo_results = [
        _fake_task("Migrate database", owner="Priya", due_date=date(2026, 5, 6)),
        _fake_task("Update dashboard skeleton", owner="Marco"),
    ]
    item = ExtractedItem(
        title="Postgres migration",
        owner="Priya",
        evidence_quote="Priya will own the Postgres migration.",
        confidence=0.9,
    )
    fake_repo = MagicMock()
    fake_repo.search_candidates.return_value = fake_repo_results

    with patch.dict("sys.modules", {"planner.repositories": MagicMock(tasks_repo=fake_repo)}):
        results = build_candidate_matches(MagicMock(), item=item, limit=3)

    fake_repo.search_candidates.assert_called_once()
    _, kwargs = fake_repo.search_candidates.call_args
    assert "Postgres migration" in kwargs["query"]
    assert "Priya" in kwargs["query"]
    assert kwargs["limit"] == 3
    assert len(results) == 2
    assert results[0].title == "Migrate database"
    assert all(r.task_id for r in results)


def test_build_candidate_matches_omits_owner_when_missing():
    item = ExtractedItem(
        title="Some task",
        evidence_quote="...",
        confidence=0.5,
    )
    fake_repo = MagicMock()
    fake_repo.search_candidates.return_value = []

    with patch.dict("sys.modules", {"planner.repositories": MagicMock(tasks_repo=fake_repo)}):
        build_candidate_matches(MagicMock(), item=item, limit=5)

    _, kwargs = fake_repo.search_candidates.call_args
    assert kwargs["query"] == "Some task"
