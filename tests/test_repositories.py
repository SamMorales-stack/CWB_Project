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
