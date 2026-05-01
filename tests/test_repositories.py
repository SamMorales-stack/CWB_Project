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


from datetime import date as _date

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


from planner.repositories import drafts_repo


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
