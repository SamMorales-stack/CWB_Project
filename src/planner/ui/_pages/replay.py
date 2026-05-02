"""Replay page: step through meeting notes chronologically to see the plan evolve."""
from __future__ import annotations

import streamlit as st

from planner.db import session_scope
from planner.repositories import change_log_repo, meeting_notes_repo, tasks_repo
from planner.ui.styles import COLORS, empty_state, section_header


def _format_diff(before: dict | None, after: dict | None) -> str:
    if before is None and after is not None:
        return ", ".join(f"{k}={v!r}" for k, v in after.items() if v is not None)
    if before is None or after is None:
        return ""
    parts = []
    for k in sorted(set(before) | set(after)):
        b, a = before.get(k), after.get(k)
        if b != a:
            parts.append(f"**{k}:** `{b}` → `{a}`")
    return " · ".join(parts)


def render() -> None:
    # Header
    st.markdown(
        f"""
        <div style="margin-bottom:4px;">
            <div style="font-size:28px;font-weight:800;color:{COLORS['text']};letter-spacing:-0.02em;">
                Replay
            </div>
            <div style="font-size:14px;color:{COLORS['text_muted']};margin-top:6px;">
                Step through meeting notes in chronological order and see the changes
                each one contributed to the plan.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with session_scope() as s:
        notes = meeting_notes_repo.list_chronological(s)
        note_data = [
            {
                "id": n.id,
                "title": n.title,
                "source": n.source,
                "meeting_date": n.meeting_date,
                "content": n.content,
                "attendees": list(n.attendees or []),
            }
            for n in notes
        ]
        total_tasks = len(tasks_repo.list_all(s))

    if not note_data:
        empty_state(
            icon="🔄",
            title="No meeting notes loaded yet",
            subtitle="Click Load sample dataset in the sidebar first.",
        )
        return

    n_notes = len(note_data)

    # ── Navigation state ──────────────────────────────────────────────────────
    if "replay_idx" not in st.session_state:
        st.session_state["replay_idx"] = 0

    idx = st.session_state["replay_idx"]
    idx = max(0, min(idx, n_notes - 1))

    # ── Progress bar + controls ───────────────────────────────────────────────
    st.markdown(
        f"<div style='font-size:13px;color:rgba(255,255,255,0.5);margin-bottom:6px'>"
        f"Note {idx + 1} of {n_notes}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.progress((idx + 1) / n_notes)

    c_prev, c_next, c_jump = st.columns([1, 1, 4])
    if c_prev.button("← Prev", disabled=idx == 0, use_container_width=True):
        st.session_state["replay_idx"] = idx - 1
        st.rerun()
    if c_next.button("Next →", disabled=idx == n_notes - 1, use_container_width=True,
                     type="primary"):
        st.session_state["replay_idx"] = idx + 1
        st.rerun()

    jump_to = c_jump.selectbox(
        "Jump to note",
        options=range(n_notes),
        format_func=lambda i: f"{i + 1}. {note_data[i]['title']}",
        index=idx,
        label_visibility="collapsed",
    )
    if jump_to != idx:
        st.session_state["replay_idx"] = jump_to
        st.rerun()

    st.markdown("---")

    # ── Current note ──────────────────────────────────────────────────────────
    note = note_data[idx]
    meeting_date_str = (
        note["meeting_date"].strftime("%B %d, %Y") if note["meeting_date"] else "Unknown date"
    )
    source_icon = {"meeting": "🗣", "email": "📧", "chat": "💬"}.get(note["source"], "📄")

    col_note, col_changes = st.columns([1, 1])

    with col_note:
        st.subheader(f"{source_icon} {note['title']}")
        st.caption(f"{meeting_date_str} · {note['source']}")
        if note["attendees"]:
            st.caption("Attendees: " + ", ".join(note["attendees"]))

        with st.expander("Note content", expanded=False):
            st.text(note["content"][:2000] + ("…" if len(note["content"]) > 2000 else ""))

    with col_changes:
        # Fetch change_log entries for this note's draft
        with session_scope() as s:
            entries = change_log_repo.list_for_note(s, note["id"])
            changes = [
                {
                    "op": e.op,
                    "before": e.before,
                    "after": e.after,
                    "evidence": e.evidence_quote,
                    "applied_at": e.applied_at,
                }
                for e in entries
            ]

        if not changes:
            st.info("No approved changes from this note yet.")
        else:
            st.subheader(f"{len(changes)} change(s) applied")
            for ch in changes:
                op_icon = {"create": "🆕", "update": "✏️", "delete": "🗑"}.get(ch["op"], "•")
                diff_text = _format_diff(ch["before"], ch["after"])
                with st.expander(f"{op_icon} {ch['op'].upper()} — {diff_text[:60] or '(see detail)'}"):
                    if diff_text:
                        st.markdown(diff_text)
                    if ch["evidence"]:
                        st.markdown(f"> _{ch['evidence']}_")
                    if ch["applied_at"]:
                        st.caption(f"Applied {ch['applied_at'].strftime('%Y-%m-%d %H:%M')}")

    # ── Running totals footer ──────────────────────────────────────────────────
    st.markdown("---")
    notes_processed = sum(
        1 for n in note_data[:idx + 1]
    )
    st.caption(
        f"Plan snapshot: **{total_tasks}** total tasks in tracker · "
        f"**{notes_processed}** of {n_notes} notes stepped through"
    )
