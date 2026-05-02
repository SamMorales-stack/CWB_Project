"""Loads the CWB_SJ dataset into the planner database for instant demo readiness.

Sources (CC0 licensed, https://github.com/DoreenSteven/CWB_SJ):
- tasks_master.csv      → baseline plan loaded directly into tasks table
- meeting_notes.jsonl   → first N notes ingested into meeting_notes table
- emails.csv            → first N emails ingested as email-type meeting notes
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from functools import lru_cache

import requests

from planner.db import session_scope
from planner.repositories import meeting_notes_repo, tasks_repo

_BASE = "https://raw.githubusercontent.com/DoreenSteven/CWB_SJ/main"
_MAX_NOTES = 10
_MAX_EMAILS = 5

_STATUS_MAP = {
    "not started": "not_started",
    "in progress": "in_progress",
    "blocked": "blocked",
    "completed": "done",
    "done": "done",
}
_PRIORITY_MAP = {"low": "low", "medium": "med", "high": "high"}


@lru_cache(maxsize=1)
def _fetch(url: str) -> str:
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.text


def load_samples() -> int:
    """Load CWB_SJ dataset. Returns number of meeting notes ingested."""
    _load_baseline_tasks()
    count = _load_meeting_notes()
    count += _load_emails()
    return count


def _load_baseline_tasks() -> None:
    """Import tasks_master.csv as the baseline plan (skips if tasks already exist)."""
    with session_scope() as s:
        if tasks_repo.list_all(s):
            return  # idempotent guard

    raw = _fetch(f"{_BASE}/tasks_master.csv")
    reader = csv.DictReader(io.StringIO(raw))

    with session_scope() as s:
        for row in reader:
            status_raw = row.get("status", "").strip().lower()
            priority_raw = row.get("priority", "").strip().lower()
            due_raw = row.get("planned_due", "").strip()

            tasks_repo.create(
                s,
                title=row.get("task_title", "").strip()[:256],
                owner=row.get("owner_name", "").strip() or None,
                due_date=datetime.strptime(due_raw, "%Y-%m-%d").date() if due_raw else None,
                status=_STATUS_MAP.get(status_raw, "not_started"),
                priority=_PRIORITY_MAP.get(priority_raw, "med"),
                description=row.get("notes", "").strip() or None,
            )


def _load_meeting_notes() -> int:
    raw = _fetch(f"{_BASE}/meeting_notes.jsonl")
    lines = [ln for ln in raw.splitlines() if ln.strip()][:_MAX_NOTES]
    count = 0
    with session_scope() as s:
        for line in lines:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            dt_raw = obj.get("meeting_datetime", "")
            try:
                meeting_date = datetime.fromisoformat(dt_raw).date() if dt_raw else None
            except ValueError:
                meeting_date = None
            attendees = [
                a.strip() for a in obj.get("attendees", "").split(";") if a.strip()
            ]
            meeting_notes_repo.create(
                s,
                source="meeting",
                title=obj.get("title", "Meeting notes").strip()[:256],
                content=obj.get("notes_text", "").strip(),
                meeting_date=meeting_date,
                attendees=attendees,
            )
            count += 1
    return count


def _load_emails() -> int:
    raw = _fetch(f"{_BASE}/emails.csv")
    reader = csv.DictReader(io.StringIO(raw))
    count = 0
    with session_scope() as s:
        for i, row in enumerate(reader):
            if i >= _MAX_EMAILS:
                break
            sent_raw = row.get("sent_datetime", "").strip()
            try:
                meeting_date = datetime.fromisoformat(sent_raw).date() if sent_raw else None
            except ValueError:
                meeting_date = None
            from_addr = row.get("from", "").strip()
            meeting_notes_repo.create(
                s,
                source="email",
                title=(row.get("subject", "Email").strip() or "Email")[:256],
                content=row.get("body", "").strip(),
                meeting_date=meeting_date,
                attendees=[from_addr] if from_addr else [],
            )
            count += 1
    return count
