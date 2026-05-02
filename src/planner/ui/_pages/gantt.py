"""Gantt page: Plotly timeline of tasks colored by status."""
from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from planner.db import session_scope
from planner.repositories import tasks_repo
from planner.ui.styles import COLORS, ICONS, empty_state, section_header


def render() -> None:
    # Header
    st.markdown(
        f"""
        <div style="margin-bottom:4px;">
            <div style="font-size:28px;font-weight:800;color:{COLORS['text']};letter-spacing:-0.02em;">
                {ICONS['gantt']} Gantt
            </div>
            <div style="font-size:14px;color:{COLORS['text_muted']};margin-top:6px;max-width:640px;">
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
                "title": t.title,
                "owner": t.owner or "—",
                "start": t.created_at.date() if t.created_at else None,
                "finish": t.due_date,
                "status": t.status,
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

    for r in plottable:
        if r["start"] is None or r["start"] >= r["finish"]:
            r["start"] = r["finish"] - pd.Timedelta(days=7)

    df = pd.DataFrame(plottable)
    df["Start"] = pd.to_datetime(df["start"])
    df["Finish"] = pd.to_datetime(df["finish"])

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="title",
        color="status",
        hover_data=["owner"],
        color_discrete_map={
            "not_started": "#8B5CF6",
            "in_progress": "#06B6D4",
            "blocked": "#EF4444",
            "done": "#10B981",
        },
        labels={"title": "Task", "status": "Status"},
        template="plotly_dark",
    )

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["surface"],
        font_color=COLORS["text"],
        font_family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
        font_size=13,
        margin=dict(l=200, r=40, t=40, b=60),
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
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(size=11),
        ),
    )

    # Today's line
    fig.add_vline(
        x=date.today().isoformat(),
        line_dash="dash",
        line_color=COLORS["warning"],
        line_width=2,
        annotation_text="Today",
        annotation_position="top right",
        annotation_font_color=COLORS["warning"],
        annotation_font_size=12,
    )

    # Bars styling
    fig.update_traces(
        marker_line_width=0,
        opacity=0.92,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Owner: %{customdata[0]}<br>"
            "Start: %{x_start|%b %d, %Y}<br>"
            "End: %{x_end|%b %d, %Y}<br>"
            "<extra></extra>"
        ),
    )

    st.plotly_chart(fig, use_container_width=True)
