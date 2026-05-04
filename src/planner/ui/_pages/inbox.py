"""Inbox page: paste/upload meeting notes and run the agent pipeline."""
from __future__ import annotations

from datetime import date

import streamlit as st

from planner.service import PlannerService
from planner.ui.styles import COLORS, ICONS

_LABEL_STYLE = (
    f"font-size:11px;font-weight:700;text-transform:uppercase;"
    f"letter-spacing:0.06em;color:{COLORS['text_secondary']};margin-bottom:4px;"
)


def _label(text: str, top_margin: str = "0") -> None:
    st.markdown(
        f'<div style="{_LABEL_STYLE}margin-top:{top_margin};">{text}</div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="margin-bottom:20px;">
            <div style="font-size:26px;font-weight:800;color:{COLORS['text']};
                        letter-spacing:-0.02em;line-height:1.2;">
                Inbox
            </div>
            <div style="font-size:13px;color:{COLORS['text_secondary']};margin-top:6px;
                        line-height:1.6;max-width:680px;">
                Paste a meeting note or upload a file. The agent extracts tasks,
                compares them to the current plan, and prepares a draft for review.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("ingest_form", clear_on_submit=False):

        # ── Row 1: Title | Meeting Date ───────────────────────────────────────
        col1, col2 = st.columns(2)
        with col1:
            _label("Title")
            title = st.text_input(
                "Title",
                value="",
                placeholder="e.g. Weekly Standup Notes",
                label_visibility="collapsed",
            )
        with col2:
            _label("Meeting Date")
            meeting_date = st.date_input(
                "Meeting date",
                value=date.today(),
                label_visibility="collapsed",
            )

        # ── Row 2: Source Type | Attendees ────────────────────────────────────
        col3, col4 = st.columns(2)
        with col3:
            _label("Source Type", top_margin="12px")
            source = st.selectbox(
                "Source type",
                ["meeting", "email", "chat"],
                label_visibility="collapsed",
            )
        with col4:
            _label("Attendees", top_margin="12px")
            attendees_raw = st.text_input(
                "Attendees",
                value="",
                placeholder="e.g. Alice, Bob, Charlie",
                label_visibility="collapsed",
            )

        # ── Content textarea ──────────────────────────────────────────────────
        _label("Content", top_margin="16px")
        pasted = st.text_area(
            "Content",
            height=180,
            placeholder="Paste your meeting notes, email, or chat transcript here...",
            label_visibility="collapsed",
        )

        # ── Submit button ─────────────────────────────────────────────────────
        submitted = st.form_submit_button(
            "Process with Agent",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    # ── Validation ────────────────────────────────────────────────────────────
    text = pasted.strip()

    if not text:
        st.error("Please paste content or upload a file.")
        return
    if not title.strip():
        st.error("Please provide a title.")
        return

    attendees = [a.strip() for a in attendees_raw.split(",") if a.strip()]
    service = PlannerService()

    # ── Pipeline with styled status ───────────────────────────────────────────
    with st.status("Running agent pipeline…", expanded=True) as status:
        st.write("Saving note to database…")
        note = service.ingest_note(
            text=text,
            source=source,
            title=title.strip(),
            meeting_date=meeting_date,
            attendees=attendees,
        )
        st.write(f"Note saved · extracting tasks from {len(text):,} characters…")
        try:
            draft = service.run_pipeline(note_id=note.id)
        except Exception as exc:
            status.update(label="Pipeline failed", state="error")
            st.error(f"Pipeline failed: {exc}")
            return
        n = len(draft.proposed_changes)
        st.write(f"Classified {n} change(s) · draft ready for review.")
        status.update(label=f"Done — {n} proposed change(s)", state="complete")

    # ── Result card ───────────────────────────────────────────────────────────
    st.session_state["last_draft_id"] = str(draft.id)
    st.markdown(
        f"""
        <div style="background:{COLORS['surface']};border:1px solid {COLORS['success']}44;
                    border-radius:12px;padding:20px;margin-top:16px;">
            <div style="font-size:13px;font-weight:700;color:{COLORS['success']};
                        margin-bottom:8px;">
                {ICONS['success']} Draft Generated
            </div>
            <div style="font-size:14px;color:{COLORS['text']};">
                {draft.summary_md or "_(no summary)_"}
            </div>
            <div style="margin-top:12px;font-size:13px;color:{COLORS['text_secondary']};">
                Open <strong style="color:{COLORS['primary']};">Drafts</strong>
                in the sidebar to review and approve.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
