"""Streamlit entry point for the SJ Project Planner Agent."""
from __future__ import annotations

import streamlit as st

from planner.config import get_settings


def _check_health() -> dict[str, bool]:
    health = {"postgres": False, "llm": False}
    try:
        from sqlalchemy import text

        from planner.db import SessionLocal
        with SessionLocal() as s:
            s.execute(text("select 1"))
            health["postgres"] = True
    except Exception:
        pass
    try:
        from planner.agent.client import get_client
        get_client()
        health["llm"] = True
    except Exception:
        pass
    return health


def _sidebar_stats() -> tuple[int, str]:
    """Return (total_tasks, last_change_label)."""
    try:
        from planner.db import session_scope
        from planner.repositories import change_log_repo, tasks_repo
        with session_scope() as s:
            count = len(tasks_repo.list_all(s))
            entries = change_log_repo.list_recent(s, limit=1)
            if entries:
                last = entries[0].applied_at
                label = last.strftime("%b %d, %H:%M") if last else "—"
            else:
                label = "—"
        return count, label
    except Exception:
        return 0, "—"


def main() -> None:
    st.set_page_config(page_title="SJ Project Planner", layout="wide", page_icon="📋")

    settings = get_settings()

    st.sidebar.markdown(
        f"<div style='padding:8px 4px 4px'>"
        f"<span style='font-size:22px'>📋</span> "
        f"<span style='font-weight:700;font-size:15px'>{settings.app_name}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    total_tasks, last_change = _sidebar_stats()
    st.sidebar.markdown(
        f"<div style='font-size:12px;color:rgba(232,234,240,0.5);padding:0 4px 12px'>"
        f"{total_tasks} tasks · last change {last_change}"
        f"</div>",
        unsafe_allow_html=True,
    )

    page = st.sidebar.radio(
        "Navigate",
        ["Inbox", "Drafts", "Tracker", "Gantt", "Change Log"],
        label_visibility="collapsed",
    )

    health = _check_health()
    st.sidebar.markdown("---")
    pg_icon = "✅" if health["postgres"] else "❌"
    llm_icon = "✅" if health["llm"] else "❌"
    st.sidebar.markdown(
        f"<div style='font-size:12px;color:rgba(232,234,240,0.45)'>"
        f"Postgres {pg_icon} &nbsp; LLM {llm_icon}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")

    n = st.sidebar.empty()
    if st.sidebar.button("Load sample dataset"):
        from planner.ui.sample_data import load_samples
        count = load_samples()
        n.success(f"Loaded {count} note(s).")

    if page == "Inbox":
        from planner.ui._pages.inbox import render
    elif page == "Drafts":
        from planner.ui._pages.drafts import render
    elif page == "Tracker":
        from planner.ui._pages.tracker import render
    elif page == "Gantt":
        from planner.ui._pages.gantt import render
    else:
        from planner.ui._pages.change_log import render

    render()


if __name__ == "__main__":
    main()
