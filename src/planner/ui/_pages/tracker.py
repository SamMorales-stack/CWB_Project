"""Tracker page: filterable view of the current plan."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from planner.db import session_scope
from planner.repositories import change_log_repo, tasks_repo

_STATUS_BG = {
    "not_started": ("rgba(155,93,229,0.15)", "#9B5DE5"),
    "in_progress":  ("rgba(0,187,249,0.18)",  "#00BBF9"),
    "blocked":      ("rgba(241,91,181,0.22)",  "#F15BB5"),
    "done":         ("rgba(155,93,229,0.08)",  "rgba(155,93,229,0.55)"),
}

_PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}


def _status_cell(val: str) -> str:
    bg, fg = _STATUS_BG.get(val, ("rgba(255,255,255,0.06)", "#E8EAF0"))
    return f"background-color: {bg}; color: {fg}; font-weight: 600"


def render() -> None:
    st.title("Tracker")
    st.caption("Current state of the plan. Updated whenever a draft is approved.")

    with session_scope() as s:
        tasks = tasks_repo.list_all(s)
        rows = [
            {
                "id": str(t.id),
                "title": t.title,
                "owner": t.owner or "",
                "due_date": t.due_date,
                "status": t.status,
                "priority": t.priority,
                "updated_at": t.updated_at,
            }
            for t in tasks
        ]
        recent_entries = change_log_repo.list_recent(s, limit=200)
        this_week = sum(
            1 for e in recent_entries
            if e.applied_at and e.applied_at.date() >= date.today() - timedelta(days=7)
        )

    if not rows:
        st.info(
            "No tasks yet. Process a note in the Inbox and approve a draft to populate the plan."
        )
        return

    df = pd.DataFrame(rows)
    today = date.today()
    df["overdue"] = df["due_date"].apply(lambda d: bool(d and d < today))
    df["due_soon"] = df["due_date"].apply(
        lambda d: bool(d and today <= d <= today + timedelta(days=3))
    )

    # ── Metric cards ─────────────────────────────────────────────────────────
    total = len(df)
    overdue_count = int(df["overdue"].sum())
    with session_scope() as s:
        from planner.repositories import drafts_repo
        pending_count = len(drafts_repo.list_pending(s))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Tasks", total)
    m2.metric(
        "Overdue", overdue_count,
        delta=f"{overdue_count} overdue" if overdue_count else None,
        delta_color="inverse",
    )
    m3.metric("Pending Drafts", pending_count)
    m4.metric("Applied This Week", this_week)

    st.markdown("---")

    # ── Urgent panel ──────────────────────────────────────────────────────────
    urgent = df[df["overdue"] | ((df["priority"] == "high") & (df["status"] != "done"))]
    if not urgent.empty:
        st.subheader("Urgent")
        st.dataframe(
            urgent[["title", "owner", "due_date", "status", "priority"]].style.map(
                _status_cell, subset=["status"]
            ),
            hide_index=True,
            use_container_width=True,
        )

    # ── All tasks ─────────────────────────────────────────────────────────────
    st.subheader("All tasks")
    col1, col2, col3 = st.columns(3)
    status_filter = col1.multiselect("Status", sorted(df["status"].unique()))
    owner_filter = col2.multiselect("Owner", sorted(o for o in df["owner"].unique() if o))
    only_open = col3.checkbox("Hide done", value=True)

    filtered = df.copy()
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if owner_filter:
        filtered = filtered[filtered["owner"].isin(owner_filter)]
    if only_open:
        filtered = filtered[filtered["status"] != "done"]

    filtered = filtered.copy()
    filtered["priority"] = filtered["priority"].map(lambda p: _PRIORITY_ICON.get(p, p))

    def _row_style(row):
        due = row.get("due_date")
        is_overdue = bool(due and due < today)
        is_due_soon = bool(due and today <= due <= today + timedelta(days=3))
        if is_overdue:
            return ["background-color: rgba(241,91,181,0.12)"] * len(row)
        if is_due_soon:
            return ["background-color: rgba(254,228,64,0.08)"] * len(row)
        if row.get("status") == "done":
            return ["opacity: 0.45"] * len(row)
        return [""] * len(row)

    show_cols = ["title", "owner", "due_date", "status", "priority", "updated_at"]
    st.dataframe(
        filtered[show_cols]
        .style.apply(_row_style, axis=1)
        .map(_status_cell, subset=["status"]),
        hide_index=True,
        use_container_width=True,
    )
