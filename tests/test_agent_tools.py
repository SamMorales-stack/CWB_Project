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


from planner.agent.schemas import CandidateMatch, ClassificationResult, ExtractedItem  # noqa: E402, F811


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
