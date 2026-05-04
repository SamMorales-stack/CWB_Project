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

# ── Design tokens ─────────────────────────────────────────────────────────────
_BG          = "#0B0F19"
_SURFACE     = "#111827"
_SURFACE_HI  = "#1F2937"
_BORDER      = "#374151"
_PRIMARY     = "#2563EB"
_TEXT        = "#F9FAFB"
_TEXT_SEC    = "#9CA3AF"
_TEXT_MUTED  = "#6B7280"
_SUCCESS     = "#2DD4BF"
_WARNING     = "#FBBF24"
_ERROR       = "#F87171"

_STATUS_LABELS = {
    "not_started": "Not Started",
    "in_progress": "In Progress",
    "blocked":     "On Hold",
    "done":        "Done",
}

_STATUS_COLOR = {
    "not_started": "#64748B",
    "in_progress": "#2563EB",
    "blocked":     "#F87171",
    "done":        "#2DD4BF",
}

_PRIORITY_COLOR = {
    "high":   "#F87171",
    "medium": "#FBBF24",
    "med":    "#FBBF24",
    "low":    "#9CA3AF",
}

_PRIORITY_LABEL = {
    "high":   "High",
    "medium": "Medium",
    "med":    "Medium",
    "low":    "Low",
}

# kept for Task History / vs. Baseline tabs
_STATUS_BG = {
    "Not Started": ("rgba(100,116,139,0.15)", "#64748B"),
    "In Progress":  ("rgba(37,99,235,0.15)",  "#2563EB"),
    "On Hold":      ("rgba(248,113,113,0.15)", "#F87171"),
    "Done":         ("rgba(45,212,191,0.12)",  "#2DD4BF"),
}

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


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert a #RRGGBB hex string to an rgba() CSS value."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _status_pill(status_key: str) -> str:
    """Return an HTML pill badge for a status key."""
    label = _STATUS_LABELS.get(status_key, status_key)
    color = _STATUS_COLOR.get(status_key, _TEXT_MUTED)
    bg    = _hex_to_rgba(color, 0.20)
    bd    = _hex_to_rgba(color, 0.40)
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:12px;'
        f'font-size:11px;font-weight:700;background:{bg};color:{color};'
        f'border:1px solid {bd};">{label}</span>'
    )


def _priority_html(priority_key: str) -> str:
    """Return colored priority text."""
    label = _PRIORITY_LABEL.get(priority_key, priority_key.capitalize() if priority_key else "—")
    color = _PRIORITY_COLOR.get(priority_key, _TEXT_MUTED)
    return f'<span style="color:{color};font-weight:600;font-size:13px;">{label}</span>'


def _fmt_due(due_date: date | None, today: date) -> str:
    """Format a due date, coloured red if overdue."""
    if not due_date:
        return f'<span style="color:{_TEXT_MUTED};">—</span>'
    label = due_date.strftime("%b %-d") if hasattr(due_date, "strftime") else str(due_date)
    # Windows strftime doesn't support %-d; use a fallback
    try:
        label = due_date.strftime("%b %-d")
    except ValueError:
        label = due_date.strftime("%b %d").replace(" 0", " ")
    color = _ERROR if due_date < today else _TEXT_SEC
    return f'<span style="color:{color};font-size:13px;">{label}</span>'


def _task_table_html(tasks_list: list[dict], today: date) -> str:
    """Build and return a full HTML table string for the given tasks."""
    th_style = (
        f"font-size:11px;text-transform:uppercase;font-weight:700;"
        f"color:{_TEXT_MUTED};background:{_SURFACE_HI};"
        f"padding:10px 16px;text-align:left;white-space:nowrap;"
    )
    table_style = (
        "width:100%;border-collapse:collapse;"
        "font-family:inherit;"
    )

    header = (
        f'<thead><tr>'
        f'<th style="{th_style}">TASK</th>'
        f'<th style="{th_style}">OWNER</th>'
        f'<th style="{th_style}">DUE</th>'
        f'<th style="{th_style}">STATUS</th>'
        f'<th style="{th_style}">PRIORITY</th>'
        f'</tr></thead>'
    )

    rows_html = []
    for t in tasks_list:
        is_done = t.get("status") == "done"
        row_opacity = "opacity:0.45;" if is_done else ""
        row_style = (
            f"background:{_SURFACE};border-bottom:1px solid {_BORDER};"
            f"{row_opacity}"
        )
        td_base = "padding:10px 16px;vertical-align:middle;"

        task_cell = (
            f'<td style="{td_base}font-size:13px;font-weight:600;color:{_TEXT};">'
            f'{t.get("title","")}</td>'
        )
        owner_val = t.get("owner") or "—"
        owner_cell = (
            f'<td style="{td_base}font-size:13px;color:{_TEXT_SEC};">'
            f'{owner_val}</td>'
        )
        due_cell   = f'<td style="{td_base}">{_fmt_due(t.get("due_date"), today)}</td>'
        status_cell = f'<td style="{td_base}">{_status_pill(t.get("status",""))}</td>'
        priority_cell = f'<td style="{td_base}">{_priority_html(t.get("priority",""))}</td>'

        rows_html.append(
            f'<tr style="{row_style}">'
            f'{task_cell}{owner_cell}{due_cell}{status_cell}{priority_cell}'
            f'</tr>'
        )

    body = f'<tbody>{"".join(rows_html)}</tbody>' if rows_html else (
        f'<tbody><tr><td colspan="5" style="padding:20px 16px;color:{_TEXT_MUTED};">'
        f'No tasks match the current filters.</td></tr></tbody>'
    )

    return (
        f'<div style="border:1px solid {_BORDER};border-radius:8px;overflow:hidden;">'
        f'<table style="{table_style}">{header}{body}</table>'
        f'</div>'
    )


def render() -> None:
    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown(
        f'<p style="font-size:26px;font-weight:800;color:{_TEXT};margin:0 0 4px 0;">Tracker</p>'
        f'<p style="font-size:13px;color:{_TEXT_MUTED};margin:0 0 24px 0;">'
        f'Current state of the plan. Updated whenever a draft is approved.</p>',
        unsafe_allow_html=True,
    )

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

    def _metric_card(label: str, value: int | str, value_color: str) -> str:
        return (
            f'<div style="background:{_SURFACE};border:1px solid {_BORDER};'
            f'border-radius:12px;padding:20px;">'
            f'<div style="font-size:11px;text-transform:uppercase;font-weight:700;'
            f'color:{_TEXT_MUTED};margin-bottom:8px;">{label}</div>'
            f'<div style="font-size:28px;font-weight:800;color:{value_color};">{value}</div>'
            f'</div>'
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(_metric_card("TOTAL TASKS",       total,         _PRIMARY), unsafe_allow_html=True)
    m2.markdown(_metric_card("OVERDUE",           overdue_count, _ERROR),   unsafe_allow_html=True)
    m3.markdown(_metric_card("PENDING DRAFTS",    pending_count, _WARNING), unsafe_allow_html=True)
    m4.markdown(_metric_card("APPLIED THIS WEEK", this_week,     _SUCCESS), unsafe_allow_html=True)

    tab_tasks, tab_history, tab_baseline = st.tabs(
        ["Tasks", "Task History", "vs. Baseline"]
    )

    # ── Tab: Tasks ────────────────────────────────────────────────────────────
    with tab_tasks:
        # ── Urgent Attention ──────────────────────────────────────────────────
        urgent_df = df[
            df["overdue"] | ((df["priority"] == "high") & (df["status"] != "done"))
        ]

        st.markdown(
            f'<p style="font-size:11px;text-transform:uppercase;font-weight:700;'
            f'color:{_TEXT_MUTED};margin:24px 0 10px 0;">URGENT ATTENTION</p>',
            unsafe_allow_html=True,
        )

        urgent_tasks = urgent_df.to_dict("records")
        st.markdown(_task_table_html(urgent_tasks, today), unsafe_allow_html=True)

        # ── Filter row ────────────────────────────────────────────────────────
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            st.markdown(
                f'<p style="font-size:11px;text-transform:uppercase;font-weight:700;'
                f'color:{_TEXT_MUTED};margin:0 0 4px 0;">STATUS</p>',
                unsafe_allow_html=True,
            )
            all_statuses = sorted(df["status"].unique())
            status_options = ["__all__"] + all_statuses
            status_filter = st.selectbox(
                "status_select",
                options=status_options,
                format_func=lambda s: "All statuses" if s == "__all__" else _STATUS_LABELS.get(s, s),
                label_visibility="collapsed",
                key="tracker_status_filter",
            )

        with col2:
            st.markdown(
                f'<p style="font-size:11px;text-transform:uppercase;font-weight:700;'
                f'color:{_TEXT_MUTED};margin:0 0 4px 0;">OWNER</p>',
                unsafe_allow_html=True,
            )
            all_owners = sorted(o for o in df["owner"].unique() if o)
            owner_options = ["__all__"] + all_owners
            owner_filter = st.selectbox(
                "owner_select",
                options=owner_options,
                format_func=lambda o: "All owners" if o == "__all__" else o,
                label_visibility="collapsed",
                key="tracker_owner_filter",
            )

        with col3:
            st.markdown(
                f'<p style="font-size:11px;text-transform:uppercase;font-weight:700;'
                f'color:{_TEXT_MUTED};margin:0 0 4px 0;">HIDE COMPLETED</p>',
                unsafe_allow_html=True,
            )
            hide_done = st.checkbox(
                "hide_done",
                value=True,
                label_visibility="collapsed",
                key="tracker_hide_done",
            )

        # ── All tasks table ───────────────────────────────────────────────────
        filtered = df.copy()
        if status_filter != "__all__":
            filtered = filtered[filtered["status"] == status_filter]
        if owner_filter != "__all__":
            filtered = filtered[filtered["owner"] == owner_filter]
        if hide_done:
            filtered = filtered[filtered["status"] != "done"]

        all_tasks = filtered.to_dict("records")
        st.markdown(_task_table_html(all_tasks, today), unsafe_allow_html=True)

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
                                        if k == "status":
                                            bv = _STATUS_LABELS.get(bv, bv)
                                            av = _STATUS_LABELS.get(av, av)
                                        diffs.append(f"**{k}:** `{bv}` → `{av}`")
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
                b_lbl = _STATUS_LABELS.get(b["status"], b["status"])
                c_lbl = _STATUS_LABELS.get(cur["status"], cur["status"])
                changes.append(f"status: {b_lbl} → {c_lbl}")

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
