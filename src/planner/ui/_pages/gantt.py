"""Gantt page: Plotly timeline of tasks colored by status."""
from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from planner.db import session_scope
from planner.repositories import tasks_repo


def render() -> None:
    st.title("Gantt")
    st.caption("Visual timeline. Bars span from task creation to due date.")

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
        st.info("No tasks with due dates yet — Gantt cannot render.")
        return

    for r in plottable:
        if r["start"] is None or r["start"] >= r["finish"]:
            r["start"] = r["finish"] - pd.Timedelta(days=7)

    df = pd.DataFrame(plottable)
    df["Start"] = pd.to_datetime(df["start"])
    df["Finish"] = pd.to_datetime(df["finish"])

    fig = px.timeline(
        df, x_start="Start", x_end="Finish", y="title", color="status",
        hover_data=["owner"],
        color_discrete_map={
            "not_started": "#9B5DE5",
            "in_progress": "#00BBF9",
            "blocked": "#F15BB5",
            "done": "#3D155F",
        },
        labels={"title": "Task"},
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        paper_bgcolor="#1A1A2E",
        plot_bgcolor="#16213E",
        font_color="#E8EAF0",
    )
    fig.add_vline(
        x=pd.Timestamp(date.today()),
        line_dash="dash",
        line_color="#FEE440",
        annotation_text="today",
        annotation_position="top right",
        annotation_font_color="#FEE440",
    )
    st.plotly_chart(fig, use_container_width=True)
