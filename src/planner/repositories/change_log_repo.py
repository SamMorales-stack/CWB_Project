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


def list_for_task(session: Session, task_id: uuid.UUID) -> list[ChangeLogEntry]:
    stmt = (
        select(ChangeLogEntry)
        .where(ChangeLogEntry.task_id == task_id)
        .order_by(ChangeLogEntry.applied_at.desc())
    )
    return list(session.scalars(stmt))


def list_for_note(session: Session, note_id: uuid.UUID) -> list[ChangeLogEntry]:
    """All applied change_log entries from drafts that originated from a meeting note."""
    from planner.models import PendingDraft  # local import avoids circular

    stmt = (
        select(ChangeLogEntry)
        .join(PendingDraft, ChangeLogEntry.draft_id == PendingDraft.id)
        .where(PendingDraft.source_note_id == note_id)
        .order_by(ChangeLogEntry.applied_at.asc())
    )
    return list(session.scalars(stmt))


def list_since(session: Session, *, since: datetime) -> list[ChangeLogEntry]:
    stmt = (
        select(ChangeLogEntry)
        .where(ChangeLogEntry.applied_at >= since)
        .order_by(ChangeLogEntry.applied_at.desc())
    )
    return list(session.scalars(stmt))
