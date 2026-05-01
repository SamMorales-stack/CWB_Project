"""CRUD for meeting_notes."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

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
        ingested_at=datetime.now(UTC),
    )
    session.add(note)
    session.flush()
    return note


def get(session: Session, note_id: uuid.UUID) -> MeetingNote | None:
    return session.get(MeetingNote, note_id)


def list_recent(session: Session, limit: int = 50) -> list[MeetingNote]:
    stmt = select(MeetingNote).order_by(MeetingNote.ingested_at.desc()).limit(limit)
    return list(session.scalars(stmt))
