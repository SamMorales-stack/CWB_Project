"""Gantt page: Plotly timeline of tasks colored by status."""
from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from planner.db import session_scope
from planner.repositories import tasks_repo
from planner.ui.styles import COLORS, empty_state


def render() -> None:
    st.markdown(
        f"""
        <div style="margin-bottom:16px;">
            <div style="font-size:28px;font-weight:800;color:{COLORS['text']};letter-spacing:-0.02em;">
                Gantt
            </div>
            <div style="font-size:14px;color:{COLORS['text_muted']};margin-top:6px;">
                Visual timeline coloured by status. One row per unique task title.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with session_scope() as s:
        tasks = tasks_repo.list_all(s)
        rows = [
            {
                "title": t.title,
                "owner": t.owner or "—",
                "start": t.created_at.date() if t.created_at else None,
                "finish": t.due_date,
                "status": t.status,
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

    # Deduplicate: one row per title (keep latest finish date per title/status pair)
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
    df["Start"] = pd.to_datetime(df["start"])
    df["Finish"] = pd.to_datetime(df["finish"])

    # ── Filters ───────────────────────────────────────────────────────────────
    f1, f2, f3 = st.columns([2, 2, 1])
    status_opts = sorted(df["status"].unique())
    owner_opts  = sorted(o for o in df["owner"].unique() if o and o != "—")

    status_filter = f1.multiselect("Status", status_opts, default=status_opts,
                                   label_visibility="collapsed",
                                   placeholder="Filter by status…")
    owner_filter  = f2.multiselect("Owner", owner_opts,
                                   label_visibility="collapsed",
                                   placeholder="Filter by owner…")
    hide_done     = f3.checkbox("Hide done", value=False)

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

    # Sort by finish date so earliest deadlines appear at top
    filtered = filtered.sort_values("Finish")

    n_rows = len(filtered)
    # 30px per row, min 400, max 1400
    chart_height = max(400, min(1400, n_rows * 30 + 120))

    fig = px.timeline(
        filtered,
        x_start="Start",
        x_end="Finish",
        y="title",
        color="status",
        hover_data=["owner", "priority"],
        color_discrete_map={
            "not_started": "#64748B",
            "in_progress": "#2563EB",
            "blocked":     "#F87171",
            "done":        "#2DD4BF",
        },
        labels={"title": "", "status": "Status"},
        template="plotly_dark",
    )

    fig.update_yaxes(autorange="reversed", tickfont=dict(size=12))
    fig.update_layout(
        height=chart_height,
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["surface"],
        font_color=COLORS["text"],
        font_family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
        font_size=13,
        bargap=0.25,
        margin=dict(l=220, r=40, t=50, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=12),
            bgcolor="rgba(17,24,39,0.8)",
            bordercolor=COLORS["border"],
            borderwidth=1,
        ),
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

    today_str = date.today().isoformat()
    fig.add_shape(
        type="line",
        x0=today_str, x1=today_str,
        y0=0, y1=1, yref="paper",
        line=dict(dash="dash", color=COLORS["warning"], width=2),
    )
    fig.add_annotation(
        x=today_str, y=1.02, yref="paper",
        text="Today", showarrow=False,
        font=dict(color=COLORS["warning"], size=12),
        xanchor="left",
    )

    fig.update_traces(
        marker_line_width=0,
        opacity=0.90,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Owner: %{customdata[0]}<br>"
            "Priority: %{customdata[1]}<br>"
            "Start: %{base|%b %d, %Y}<br>"
            "Due: %{x|%b %d, %Y}<br>"
            "<extra></extra>"
        ),
    )

    st.caption(f"Showing {n_rows} tasks — use filters above to narrow the view")
    st.plotly_chart(fig, use_container_width=True)
