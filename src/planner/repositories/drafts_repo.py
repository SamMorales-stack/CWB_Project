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
