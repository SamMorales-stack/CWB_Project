"""Inbox page: paste/upload meeting notes and run the agent pipeline."""
from __future__ import annotations

from datetime import date

import streamlit as st

from planner.service import PlannerService
from planner.ui.styles import COLORS, ICONS


def render() -> None:
    # Header
    st.markdown(
        f"""
        <div style="margin-bottom:4px;">
            <div style="font-size:28px;font-weight:800;color:{COLORS['text']};letter-spacing:-0.02em;">
                Inbox
            </div>
            <div style="font-size:14px;color:{COLORS['text_muted']};margin-top:6px;">
                Paste a meeting note or upload a file. The agent extracts tasks,
                compares them to the current plan, and prepares a draft for review.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Form card
    st.markdown(
        f"""
        <div style="background:{COLORS['surface']};border:1px solid {COLORS['border']};
        border-radius:14px;padding:24px;margin-top:20px;">
        """,
        unsafe_allow_html=True,
    )

    with st.form("ingest_form", clear_on_submit=False):
        # Metadata row
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_secondary"]};'
                f'margin-bottom:4px;">Title</div>',
                unsafe_allow_html=True,
            )
            title = st.text_input("Title", value="", label_visibility="collapsed")
            st.markdown(
                f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_secondary"]};'
                f'margin-bottom:4px;margin-top:12px;">Source type</div>',
                unsafe_allow_html=True,
            )
            source = st.selectbox(
                "Source type",
                ["meeting", "email", "chat"],
                label_visibility="collapsed",
            )
        with col2:
            st.markdown(
                f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_secondary"]};'
                f'margin-bottom:4px;">Meeting date</div>',
                unsafe_allow_html=True,
            )
            meeting_date = st.date_input("Meeting date", value=date.today(), label_visibility="collapsed")
            st.markdown(
                f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_secondary"]};'
                f'margin-bottom:4px;margin-top:12px;">Attendees</div>',
                unsafe_allow_html=True,
            )
            attendees_raw = st.text_input(
                "Attendees (comma-separated)", value="", label_visibility="collapsed",
                placeholder="e.g. Alice, Bob, Charlie",
            )

        # Content area
        st.markdown(
            f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_secondary"]};'
            f'margin:16px 0 4px;">Content</div>',
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "Upload a file (.txt, .md, .eml)",
            type=["txt", "md", "eml"],
            label_visibility="collapsed",
        )

        pasted = st.text_area(
            "Or paste content here",
            height=200,
            placeholder="Paste your meeting notes, email, or chat transcript here...",
            label_visibility="collapsed",
        )

        st.markdown("</div>", unsafe_allow_html=True)

        # Submit button
        submitted = st.form_submit_button(
            f"{ICONS['success']} Process with Agent",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    text = ""
    if uploaded is not None:
        text = uploaded.read().decode("utf-8", errors="replace")
    if pasted.strip():
        text = pasted.strip()

    if not text:
        st.error("Please paste content or upload a file.")
        return
    if not title.strip():
        st.error("Please provide a title.")
        return

    attendees = [a.strip() for a in attendees_raw.split(",") if a.strip()]
    service = PlannerService()

    # Pipeline with styled status
    with st.status("Running agent pipeline…", expanded=True) as status:
        st.write("Saving note to database…")
        note = service.ingest_note(
            text=text, source=source, title=title.strip(),
            meeting_date=meeting_date, attendees=attendees,
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

    # Result card
    st.session_state["last_draft_id"] = str(draft.id)
    st.markdown(
        f"""
        <div style="background:{COLORS['surface']};border:1px solid {COLORS['success']}44;
        border-radius:12px;padding:20px;margin-top:16px;">
            <div style="font-size:13px;font-weight:700;color:{COLORS['success']};margin-bottom:8px;">
                {ICONS['success']} Draft Generated
            </div>
            <div style="font-size:14px;color:{COLORS['text']};">
                {draft.summary_md or "_(no summary)_"}
            </div>
            <div style="margin-top:12px;font-size:13px;color:{COLORS['text_secondary']};">
                Open <strong style="color:{COLORS['primary']};">Drafts</strong> in the sidebar to review and approve.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
