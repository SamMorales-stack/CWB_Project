"""Inbox page: paste/upload meeting notes and run the agent pipeline."""
from __future__ import annotations

from datetime import date

import streamlit as st

from planner.service import PlannerService


def render() -> None:
    st.title("Inbox")
    st.caption(
        "Paste a meeting note or upload a file. The agent extracts tasks, "
        "compares them to the current plan, and prepares a draft for review."
    )

    with st.form("ingest_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Title", value="")
            source = st.selectbox("Source type", ["meeting", "email", "chat"])
        with col2:
            meeting_date = st.date_input("Meeting date", value=date.today())
            attendees_raw = st.text_input("Attendees (comma-separated)", value="")

        uploaded = st.file_uploader("Upload a file (.txt, .md, .eml)", type=["txt", "md", "eml"])
        pasted = st.text_area("Or paste content here", height=240)

        submitted = st.form_submit_button("Process", type="primary")

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

    with st.spinner("Running the agent pipeline…"):
        service = PlannerService()
        note = service.ingest_note(
            text=text, source=source, title=title.strip(),
            meeting_date=meeting_date, attendees=attendees,
        )
        try:
            draft = service.run_pipeline(note_id=note.id)
        except Exception as exc:
            st.error(f"Pipeline failed: {exc}")
            return

    st.success(f"Draft created — {len(draft.proposed_changes)} proposed change(s).")
    st.session_state["last_draft_id"] = str(draft.id)
    st.markdown(f"**Summary:** {draft.summary_md}")
    st.info("Open the **Drafts** page in the sidebar to review and approve.")
