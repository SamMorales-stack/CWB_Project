"""Streamlit entry point for the SJ Project Planner Agent."""
from __future__ import annotations

import streamlit as st

from planner.config import get_settings


def _check_health() -> dict[str, bool]:
    health = {"postgres": False, "azure_openai": False}
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
        health["azure_openai"] = True
    except Exception:
        pass
    return health


def main() -> None:
    st.set_page_config(page_title="SJ Project Planner", layout="wide")

    settings = get_settings()
    st.sidebar.title(settings.app_name)

    page = st.sidebar.radio(
        "Navigate",
        ["Inbox", "Drafts", "Tracker", "Gantt", "Change Log"],
        label_visibility="collapsed",
    )

    health = _check_health()
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Status**")
    st.sidebar.markdown(f"- Postgres: {'✅' if health['postgres'] else '❌'}")
    st.sidebar.markdown(f"- Azure OpenAI: {'✅' if health['azure_openai'] else '❌'}")
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
