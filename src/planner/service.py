"""PlannerService: orchestrates ingest → extract → classify → draft → apply."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from planner.agent.planner_agent import PlannerAgent
from planner.agent.schemas import DraftSummary, ProposedChange
from planner.db import session_scope
from planner.models import Task
from planner.repositories import (
    change_log_repo,
    drafts_repo,
    meeting_notes_repo,
    tasks_repo,
)


@dataclass
class _NoteView:
    """Detached view of a MeetingNote (safe to use after session closes)."""

    id: uuid.UUID
    source: str
    title: str
    content: str
    meeting_date: date | None
    attendees: list[str]
    ingested_at: datetime


@dataclass
class _DraftView:
    """Detached view of a PendingDraft (safe to use after session closes)."""

    id: uuid.UUID
    status: str
    summary_md: str
    proposed_changes: list[dict]
    source_note_id: uuid.UUID | None
    created_at: datetime


class PlannerService:
    def __init__(self, agent: PlannerAgent | None = None) -> None:
        self.agent = agent or PlannerAgent()

    def ingest_note(
        self,
        *,
        text: str,
        source: str,
        title: str,
        meeting_date: date | None,
        attendees: list[str],
    ) -> _NoteView:
        with session_scope() as s:
            note = meeting_notes_repo.create(
                s,
                source=source,
                title=title,
                content=text,
                meeting_date=meeting_date,
                attendees=attendees,
            )
            return _NoteView(
                id=note.id,
                source=note.source,
                title=note.title,
                content=note.content,
                meeting_date=note.meeting_date,
                attendees=list(note.attendees),
                ingested_at=note.ingested_at,
            )

    def run_pipeline(self, *, note_id: uuid.UUID) -> _DraftView:
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
            return _DraftView(
                id=draft.id,
                status=draft.status,
                summary_md=draft.summary_md,
                proposed_changes=list(draft.proposed_changes),
                source_note_id=draft.source_note_id,
                created_at=draft.created_at,
            )

    def apply_draft(
        self,
        *,
        draft_id: uuid.UUID,
        decisions: dict[int, str],
        approver: str,
    ) -> None:
        with session_scope() as s:
            draft = drafts_repo.get(s, draft_id)
            if draft is None:
                raise ValueError(f"draft {draft_id} not found")

            any_approved = False
            for idx, change in enumerate(draft.proposed_changes):
                if decisions.get(idx, "reject") != "approve":
                    continue
                any_approved = True
                self._apply_one_change(s, draft_id=draft_id, change=change, approver=approver)

            drafts_repo.set_status(s, draft_id, "approved" if any_approved else "rejected")

    def _apply_one_change(
        self,
        session: Any,
        *,
        draft_id: uuid.UUID,
        change: dict,
        approver: str,
    ) -> None:
        op = change["op"]
        fields = change.get("fields") or {}
        evidence = change.get("evidence_quote", "")

        if op == "create":
            new_task = tasks_repo.create(session, **_coerce_task_fields(fields))
            change_log_repo.record(
                session,
                draft_id=draft_id,
                task_id=new_task.id,
                op="create",
                before=None,
                after=_task_snapshot(new_task),
                evidence_quote=evidence,
                approved_by=approver,
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
                session,
                draft_id=draft_id,
                task_id=target_id,
                op="update",
                before=before,
                after=after,
                evidence_quote=evidence,
                approved_by=approver,
            )
        elif op == "conflict":
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
                session,
                draft_id=draft_id,
                task_id=target_id,
                op="update",
                before=before,
                after=after,
                evidence_quote=evidence,
                approved_by=approver,
            )

    def weekly_digest(self) -> str:
        with session_scope() as s:
            since = datetime.now(UTC) - timedelta(days=7)
            entries = change_log_repo.list_since(s, since=since)
            if not entries:
                return "_No applied changes in the last 7 days._"
            payload = [
                {
                    "applied_at": e.applied_at.isoformat(),
                    "op": e.op,
                    "task_id": str(e.task_id) if e.task_id else None,
                    "before": e.before,
                    "after": e.after,
                    "evidence_quote": e.evidence_quote,
                    "approved_by": e.approved_by,
                }
                for e in entries
            ]
            result = self.agent.weekly_digest(entries=payload)
            return result.summary_md


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
