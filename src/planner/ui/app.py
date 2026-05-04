"""Streamlit entry point for PlanForge by SJ."""
from __future__ import annotations

import streamlit as st

from planner.config import get_settings
from planner.ui.styles import (
    APP_NAME,
    APP_TAGLINE,
    COLORS,
    ICONS,
    connection_pill,
    inject_global_css,
    sj_logo_html,
)


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


def _start_webhook_once() -> None:
    """Start the webhook API server in a background thread (only once per process)."""
    if st.session_state.get("_webhook_started"):
        return
    try:
        from planner.webhook import start_in_background
        start_in_background(port=8502)
        st.session_state["_webhook_started"] = True
    except Exception:
        pass


def main() -> None:
    st.set_page_config(
        page_title="PlanForge",
        layout="wide",
        page_icon="📋",
        initial_sidebar_state="expanded",
    )

    inject_global_css()
    _ = get_settings()
    _start_webhook_once()

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        # SJ Logo + PlanForge branding
        st.markdown(
            f"""
            <div style="background:{COLORS['surface']};border:1px solid {COLORS['border']};
            border-radius:12px;padding:16px;margin-bottom:8px;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
                    {sj_logo_html(38)}
                    <div>
                        <div style="font-weight:800;font-size:16px;color:{COLORS['text']};
                        letter-spacing:-0.02em;">{APP_NAME}</div>
                        <div style="font-size:10px;color:{COLORS['text_muted']};
                        font-weight:700;text-transform:uppercase;letter-spacing:0.06em;
                        margin-top:-2px;">{APP_TAGLINE}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        total_tasks, last_change = _sidebar_stats()
        st.markdown(
            f"""
            <div style="display:flex;gap:8px;margin-bottom:16px;">
                <div style="flex:1;background:{COLORS['surface']};border:1px solid {COLORS['border']};
                border-radius:8px;padding:10px;text-align:center;">
                    <div style="font-size:20px;font-weight:800;color:{COLORS['primary']};">{total_tasks}</div>
                    <div style="font-size:10px;font-weight:700;color:{COLORS['text_muted']};
                    text-transform:uppercase;letter-spacing:0.05em;">Tasks</div>
                </div>
                <div style="flex:1;background:{COLORS['surface']};border:1px solid {COLORS['border']};
                border-radius:8px;padding:10px;text-align:center;">
                    <div style="font-size:11px;font-weight:600;color:{COLORS['text_secondary']};
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{last_change}</div>
                    <div style="font-size:10px;font-weight:700;color:{COLORS['text_muted']};
                    text-transform:uppercase;letter-spacing:0.05em;">Last Change</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Navigation
        st.markdown(
            f'<div style="font-size:10px;font-weight:700;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;letter-spacing:0.08em;margin:12px 0 6px 4px;">Navigation</div>',
            unsafe_allow_html=True,
        )
        _nav_icons = {
            "Inbox":      "⊞",
            "Drafts":     "⊡",
            "Tracker":    "☑",
            "Gantt":      "⊕",
            "Change Log": "⊙",
            "Replay":     "↺",
        }
        page = st.radio(
            "Navigate",
            ["Inbox", "Drafts", "Tracker", "Gantt", "Change Log", "Replay"],
            format_func=lambda p: f"{_nav_icons.get(p, '○')}  {p}",
            label_visibility="collapsed",
        )

        # ── Spacer pushes debug panel to bottom ──────────────────────────────
        st.markdown("<div style='flex:1;min-height:40px;'></div>", unsafe_allow_html=True)

        # ── Debug panel (collapsed by default) ───────────────────────────────
        debug_open = st.session_state.get("_debug_open", False)

        col_dbg, _ = st.columns([1, 3])
        if col_dbg.button(
            "⚙",
            key="debug_toggle",
            help="Developer tools",
            use_container_width=True,
        ):
            st.session_state["_debug_open"] = not debug_open
            st.rerun()

        if st.session_state.get("_debug_open", False):
            health = _check_health()
            st.markdown(
                f'<div style="background:{COLORS["surface_hi"]};border:1px solid {COLORS["border"]};'
                f'border-radius:10px;padding:14px;margin-top:6px;">'
                f'<div style="font-size:10px;font-weight:700;color:{COLORS["text_muted"]};'
                f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">System Status</div>',
                unsafe_allow_html=True,
            )
            pg_pill = connection_pill("Postgres", health["postgres"])
            llm_pill = connection_pill("LLM", health["llm"])
            st.markdown(
                f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;">'
                f'{pg_pill}{llm_pill}</div>',
                unsafe_allow_html=True,
            )
            n = st.empty()
            if st.button(
                "Load sample dataset",
                use_container_width=True,
                key="load_samples_debug",
            ):
                from planner.ui.sample_data import load_samples
                count = load_samples()
                n.success(f"Loaded {count} note(s).")
            st.markdown(
                f'<div style="font-size:10px;color:{COLORS["text_muted"]};margin-top:10px;">'
                f'Webhook: <code style="color:{COLORS["primary"]};">:8502/api/ingest</code>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    # ── Main Content ─────────────────────────────────────────────────────────
    if page == "Inbox":
        from planner.ui._pages.inbox import render
    elif page == "Drafts":
        from planner.ui._pages.drafts import render
    elif page == "Tracker":
        from planner.ui._pages.tracker import render
    elif page == "Gantt":
        from planner.ui._pages.gantt import render
    elif page == "Replay":
        from planner.ui._pages.replay import render
    else:
        from planner.ui._pages.change_log import render

    render()


if __name__ == "__main__":
    main()
