"""Tracker page: filterable view of the current plan."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from planner.db import session_scope
from planner.repositories import tasks_repo


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

    if not rows:
        st.info("No tasks yet. Process a note in the Inbox and approve a draft to populate the plan.")
        return

    df = pd.DataFrame(rows)
    today = date.today()
    df["overdue"] = df["due_date"].apply(lambda d: bool(d and d < today))
    df["due_soon"] = df["due_date"].apply(
        lambda d: bool(d and today <= d <= today + timedelta(days=3))
    )

    urgent = df[df["overdue"] | ((df["priority"] == "high") & (df["status"] != "done"))]
    if not urgent.empty:
        st.subheader("⚠️ Urgent")
        st.dataframe(
            urgent[["title", "owner", "due_date", "status", "priority"]],
            hide_index=True,
            use_container_width=True,
        )

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

    def _row_style(row):
        if row["overdue"]:
            return ["background-color: #ffebee"] * len(row)
        if row["due_soon"]:
            return ["background-color: #fff3e0"] * len(row)
        if row["status"] == "done":
            return ["color: #999"] * len(row)
        return [""] * len(row)

    show_cols = ["title", "owner", "due_date", "status", "priority", "updated_at"]
    st.dataframe(
        filtered[show_cols].style.apply(_row_style, axis=1),
        hide_index=True,
        use_container_width=True,
    )
