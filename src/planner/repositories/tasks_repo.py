"""CRUD for tasks, plus a fuzzy candidate search."""
from __future__ import annotations

import uuid
from typing import Any

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from planner.models import Task


_ALLOWED_FIELDS = {
    "title", "description", "owner", "due_date",
    "status", "priority", "depends_on",
}


def create(session: Session, **fields: Any) -> Task:
    safe = {k: v for k, v in fields.items() if k in _ALLOWED_FIELDS}
    task = Task(**safe)
    session.add(task)
    session.flush()
    return task


def get(session: Session, task_id: uuid.UUID) -> Task | None:
    return session.get(Task, task_id)


def list_all(session: Session) -> list[Task]:
    return list(session.scalars(select(Task).order_by(Task.updated_at.desc())))


def update(session: Session, task_id: uuid.UUID, *, fields: dict[str, Any]) -> Task | None:
    task = session.get(Task, task_id)
    if task is None:
        return None
    for k, v in fields.items():
        if k in _ALLOWED_FIELDS:
            setattr(task, k, v)
    session.flush()
    return task


def delete(session: Session, task_id: uuid.UUID) -> bool:
    task = session.get(Task, task_id)
    if task is None:
        return False
    session.delete(task)
    session.flush()
    return True


def search_candidates(session: Session, *, query: str, limit: int = 5) -> list[Task]:
    """Return tasks whose title fuzzy-matches the query."""
    all_tasks = list_all(session)
    if not all_tasks:
        return []
    titles = [t.title for t in all_tasks]
    matches = process.extract(query, titles, scorer=fuzz.partial_ratio, limit=limit)
    matched_titles = {m[0] for m in matches if m[1] >= 50}
    return [t for t in all_tasks if t.title in matched_titles]
