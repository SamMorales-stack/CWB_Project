"""Gantt page: Plotly timeline of tasks colored by status."""
from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from planner.db import session_scope
from planner.repositories import tasks_repo
from planner.ui.styles import COLORS, empty_state

_STATUS_LABELS = {
    "not_started": "Not Started",
    "in_progress": "In Progress",
    "blocked":     "Blocked",
    "done":        "Done",
}

_STATUS_COLORS = {
    "Not Started": "#64748B",
    "In Progress": "#2563EB",
    "Blocked":     "#EF4444",
    "Done":        "#2DD4BF",
}

_LEGEND_HTML = "".join(
    f'<span style="display:inline-flex;align-items:center;gap:6px;'
    f'padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;'
    f'border:1.5px solid {color};color:{color};background:{color}18;margin:0 4px;">'
    f'{label}</span>'
    for label, color in _STATUS_COLORS.items()
)


def render() -> None:
    st.markdown(
        f"""
        <div style="margin-bottom:16px;">
            <div style="font-size:28px;font-weight:800;color:{COLORS['text']};letter-spacing:-0.02em;">
                Gantt
            </div>
            <div style="font-size:14px;color:{COLORS['text_muted']};margin-top:6px;">
                Visual timeline. Bars span from task creation to due date.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with session_scope() as s:
        tasks = tasks_repo.list_all(s)
        rows = [
            {
                "title":    t.title,
                "owner":    t.owner or "—",
                "start":    t.created_at.date() if t.created_at else None,
                "finish":   t.due_date,
                "status":   t.status,
                "priority": t.priority,
            }
            for t in tasks
        ]

    plottable = [r for r in rows if r["finish"] is not None]
    if not plottable:
        empty_state(
            icon="📅",
            title="No tasks with due dates",
            subtitle="Tasks need due dates to appear on the Gantt chart.",
        )
        return

    # One row per title — keep latest finish date
    seen: dict[str, dict] = {}
    for r in plottable:
        key = r["title"]
        if key not in seen or r["finish"] > seen[key]["finish"]:
            seen[key] = r
    plottable = list(seen.values())

    for r in plottable:
        if r["start"] is None or r["start"] >= r["finish"]:
            r["start"] = r["finish"] - pd.Timedelta(days=7)

    df = pd.DataFrame(plottable)
    df["Start"]  = pd.to_datetime(df["start"])
    df["Finish"] = pd.to_datetime(df["finish"])

    # ── Filters ───────────────────────────────────────────────────────────────
    f1, f2, f3 = st.columns([2, 2, 1])
    all_statuses = sorted(df["status"].unique())
    all_owners   = sorted(o for o in df["owner"].unique() if o and o != "—")
    status_filter = f1.multiselect(
        "Status", all_statuses,
        format_func=lambda s: _STATUS_LABELS.get(s, s),
        default=all_statuses, label_visibility="collapsed",
        placeholder="Filter by status…",
    )
    owner_filter = f2.multiselect(
        "Owner", all_owners,
        label_visibility="collapsed", placeholder="Filter by owner…",
    )
    hide_done = f3.checkbox("Hide done", value=False)

    filtered = df.copy()
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if owner_filter:
        filtered = filtered[filtered["owner"].isin(owner_filter)]
    if hide_done:
        filtered = filtered[filtered["status"] != "done"]

    if filtered.empty:
        st.info("No tasks match the current filters.")
        return

    filtered = filtered.sort_values("Finish").copy()

    # Human-readable labels + date range text inside bars
    filtered["Status"]     = filtered["status"].map(_STATUS_LABELS)
    filtered["date_range"] = (
        filtered["Start"].dt.strftime("%b %d")
        + " – "
        + filtered["Finish"].dt.strftime("%b %d")
    )

    n_rows       = len(filtered)
    chart_height = max(380, min(1400, n_rows * 42 + 100))

    fig = px.timeline(
        filtered,
        x_start="Start",
        x_end="Finish",
        y="title",
        color="Status",
        text="date_range",
        hover_data=["owner", "priority"],
        color_discrete_map=_STATUS_COLORS,
        labels={"title": "", "Status": "Status"},
        template="plotly_dark",
    )

    fig.update_traces(
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(size=12, color="white", family="Inter, sans-serif"),
        marker_line_width=0,
        opacity=1.0,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Owner: %{customdata[0]}<br>"
            "Priority: %{customdata[1]}<br>"
            "Start: %{base|%b %d, %Y}<br>"
            "Due: %{x|%b %d, %Y}<br>"
            "<extra></extra>"
        ),
    )

    fig.update_yaxes(
        autorange="reversed",
        tickfont=dict(size=12),
        ticksuffix="  ",
    )
    fig.update_layout(
        height=chart_height,
        showlegend=False,
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["surface"],
        font_color=COLORS["text"],
        font_family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
        font_size=13,
        bargap=0.35,
        margin=dict(l=200, r=40, t=20, b=20),
        xaxis=dict(
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            linecolor=COLORS["border"],
        ),
    )

    # Solid TODAY line
    today_str = date.today().isoformat()
    fig.add_shape(
        type="line",
        x0=today_str, x1=today_str,
        y0=0, y1=1, yref="paper",
        line=dict(color=COLORS["warning"], width=2),
    )
    fig.add_annotation(
        x=today_str, y=1.0, yref="paper",
        text="TODAY", showarrow=False,
        font=dict(color=COLORS["warning"], size=11, family="Inter, sans-serif"),
        xanchor="left", yanchor="top",
        bgcolor=COLORS["bg"],
        borderpad=2,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Custom pill legend + task count
    st.markdown(
        f'<div style="text-align:center;margin-top:4px;">{_LEGEND_HTML}</div>'
        f'<div style="text-align:center;margin-top:10px;font-size:12px;'
        f'color:{COLORS["text_muted"]};">Showing {n_rows} tasks</div>',
        unsafe_allow_html=True,
    )
