"""Tracker page: filterable task view + bidirectional traceability + baseline diff."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from rapidfuzz import fuzz, process

from planner.db import session_scope
from planner.repositories import change_log_repo, tasks_repo

_STATUS_BG = {
    "not_started": ("rgba(155,93,229,0.15)", "#9B5DE5"),
    "in_progress":  ("rgba(0,187,249,0.18)",  "#00BBF9"),
    "blocked":      ("rgba(241,91,181,0.22)",  "#F15BB5"),
    "done":         ("rgba(155,93,229,0.08)",  "rgba(155,93,229,0.55)"),
}

_PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "med": "🟡", "low": "🟢"}

_BASELINE_URL = "https://raw.githubusercontent.com/DoreenSteven/CWB_SJ/main/tasks_master.csv"
_STATUS_MAP = {
    "not started": "not_started", "in progress": "in_progress",
    "blocked": "blocked", "completed": "done", "done": "done",
}


def _status_cell(val: str) -> str:
    bg, fg = _STATUS_BG.get(val, ("rgba(255,255,255,0.06)", "#E8EAF0"))
    return f"background-color: {bg}; color: {fg}; font-weight: 600"


@st.cache_data(ttl=3600)
def _fetch_baseline() -> list[dict]:
    import requests
    resp = requests.get(_BASELINE_URL, timeout=15)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = []
    for row in reader:
        from datetime import datetime
        due_raw = row.get("planned_due", "").strip()
        rows.append({
            "title": row.get("task_title", "").strip(),
            "owner": row.get("owner_name", "").strip() or None,
            "due_date": datetime.strptime(due_raw, "%Y-%m-%d").date() if due_raw else None,
            "status": _STATUS_MAP.get(row.get("status", "").strip().lower(), "not_started"),
            "priority": row.get("priority", "").strip().lower(),
        })
    return rows


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

    # ── Metric cards ──────────────────────────────────────────────────────────
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

    tab_tasks, tab_history, tab_baseline = st.tabs(
        ["Tasks", "Task History", "vs. Baseline"]
    )

    # ── Tab: Tasks ────────────────────────────────────────────────────────────
    with tab_tasks:
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

    # ── Tab: Task History (Bidirectional Traceability) ────────────────────────
    with tab_history:
        st.subheader("Task History")
        st.caption(
            "Select any task to see every change applied to it — "
            "traced back to the source meeting note."
        )

        task_titles = ["— select a task —"] + [r["title"] for r in rows]
        selected_title = st.selectbox("Task", task_titles, label_visibility="collapsed")

        if selected_title and selected_title != "— select a task —":
            selected_id = next(
                (r["id"] for r in rows if r["title"] == selected_title), None
            )
            if selected_id:
                with session_scope() as s:
                    entries = change_log_repo.list_for_task(s, uuid.UUID(selected_id))
                    history = [
                        {
                            "applied_at": e.applied_at,
                            "op": e.op,
                            "before": e.before,
                            "after": e.after,
                            "evidence": e.evidence_quote,
                            "approved_by": e.approved_by,
                            "draft_id": str(e.draft_id) if e.draft_id else None,
                        }
                        for e in entries
                    ]

                if not history:
                    st.info("No approved changes recorded for this task yet.")
                else:
                    st.markdown(f"**{len(history)} change(s)** recorded for **{selected_title}**")
                    for h in history:
                        when = h["applied_at"].strftime("%Y-%m-%d %H:%M") if h["applied_at"] else "—"
                        op_badge = {"create": "🆕 CREATE", "update": "✏️ UPDATE"}.get(
                            h["op"], h["op"].upper()
                        )
                        with st.expander(f"{op_badge} · {when} · by {h['approved_by']}"):
                            if h["before"] or h["after"]:
                                b = h["before"] or {}
                                a = h["after"] or {}
                                diffs = []
                                for k in sorted(set(b) | set(a)):
                                    bv, av = b.get(k), a.get(k)
                                    if bv != av:
                                        diffs.append(
                                            f"**{k}:** `{bv}` → `{av}`"
                                        )
                                if diffs:
                                    st.markdown("\n\n".join(diffs))
                            if h["evidence"]:
                                st.markdown(
                                    f"> _{h['evidence']}_"
                                )

    # ── Tab: vs. Baseline ─────────────────────────────────────────────────────
    with tab_baseline:
        st.subheader("vs. Baseline")
        st.caption(
            "Compares current tasks against the original `tasks_master.csv` from the CWB_SJ dataset. "
            "Highlights owner changes, date shifts > 7 days, and status changes."
        )

        try:
            baseline = _fetch_baseline()
        except Exception as exc:
            st.error(f"Could not fetch baseline: {exc}")
            return

        current = {r["title"]: r for r in rows}
        baseline_titles = [b["title"] for b in baseline]
        diffs = []

        for b in baseline:
            match_result = process.extractOne(
                b["title"], list(current.keys()), scorer=fuzz.partial_ratio
            )
            if match_result is None or match_result[1] < 75:
                diffs.append({
                    "baseline_title": b["title"],
                    "current_title": "— not found —",
                    "change": "MISSING from current plan",
                    "severity": "high",
                })
                continue

            cur = current[match_result[0]]
            changes = []

            if b["owner"] and cur["owner"] and b["owner"].lower() != cur["owner"].lower():
                changes.append(f"owner: {b['owner']} → {cur['owner']}")
            if b["due_date"] and cur["due_date"]:
                delta = abs((cur["due_date"] - b["due_date"]).days)
                if delta > 7:
                    sign = "+" if cur["due_date"] > b["due_date"] else "-"
                    changes.append(f"due: {b['due_date']} → {cur['due_date']} ({sign}{delta}d)")
            if b["status"] != cur["status"]:
                changes.append(f"status: {b['status']} → {cur['status']}")

            if changes:
                diffs.append({
                    "baseline_title": b["title"],
                    "current_title": match_result[0],
                    "change": "; ".join(changes),
                    "severity": "high" if any("owner" in c or "MISSING" in c for c in changes) else "med",
                })

        unchanged = len(baseline) - len(diffs)

        c1, c2, c3 = st.columns(3)
        c1.metric("Baseline tasks", len(baseline))
        c2.metric("Changed / missing", len(diffs))
        c3.metric("Unchanged", unchanged)

        if not diffs:
            st.success("Current plan matches the baseline exactly.")
        else:
            diff_df = pd.DataFrame(diffs)
            def _sev_style(row):
                if row.get("severity") == "high":
                    return ["background-color: rgba(241,91,181,0.12)"] * len(row)
                return ["background-color: rgba(254,228,64,0.06)"] * len(row)

            st.dataframe(
                diff_df[["baseline_title", "current_title", "change"]]
                .style.apply(_sev_style, axis=1),
                hide_index=True,
                use_container_width=True,
            )
