"""Pytest fixtures for repository and service tests."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from planner.db import SessionLocal
from planner.models import ChangeLogEntry, MeetingNote, PendingDraft, Task


@pytest.fixture(autouse=True)
def _truncate_tables():
    """Reset the four planner tables before each test."""
    with SessionLocal() as session:
        for model in (ChangeLogEntry, PendingDraft, Task, MeetingNote):
            session.execute(text(f"DELETE FROM {model.__tablename__}"))  # noqa: S608
        session.commit()
    yield


@pytest.fixture()
def session():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
