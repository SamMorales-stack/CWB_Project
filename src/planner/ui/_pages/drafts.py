"""Drafts page: review and approve proposed plan changes."""
from __future__ import annotations

import uuid

import streamlit as st

from planner.db import session_scope
from planner.repositories import drafts_repo, tasks_repo
from planner.service import PlannerService
from planner.ui.styles import (
    COLORS,
    ICONS,
    confidence_badge,
    empty_state,
    op_badge,
    section_header,
)

_HIGH_CONFIDENCE = 0.8


def render() -> None:
    # Header
    st.markdown(
        f"""
        <div style="margin-bottom:4px;">
            <div style="font-size:28px;font-weight:800;color:{COLORS['text']};letter-spacing:-0.02em;">
                {ICONS['drafts']} Drafts
            </div>
            <div style="font-size:14px;color:{COLORS['text_muted']};margin-top:6px;max-width:640px;">
                High-confidence changes are pre-checked for approval.
                Low-confidence changes are flagged and require an explicit click.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with session_scope() as s:
        pending = drafts_repo.list_pending(s)
        pending_data = [
            {
                "id": d.id,
                "created_at": d.created_at,
                "proposed_changes": list(d.proposed_changes),
                "summary_md": d.summary_md,
            }
            for d in pending
        ]

    if not pending_data:
        empty_state(
            icon="📝",
            title="No pending drafts",
            subtitle="Process a note in the Inbox to create a draft for review.",
        )
        return

    col_list, col_detail = st.columns([1, 3])

    with col_list:
        section_header("Pending")
        labels = [
            f"{d['created_at'].strftime('%Y-%m-%d %H:%M')} — {len(d['proposed_changes'])} change(s)"
            for d in pending_data
        ]
        last = st.session_state.get("last_draft_id")
        default_idx = 0
        if last:
            for i, d in enumerate(pending_data):
                if str(d["id"]) == last:
                    default_idx = i
                    break
        idx = st.radio(
            "Select a draft",
            options=range(len(labels)),
            format_func=lambda i: labels[i],
            index=default_idx,
            label_visibility="collapsed",
        )
        selected = pending_data[idx]
        st.session_state["last_draft_id"] = str(selected["id"])

    with col_detail:
        # Summary card
        st.markdown(
            f"""
            <div style="background:{COLORS['surface']};border:1px solid {COLORS['border']};
            border-radius:12px;padding:18px;margin-bottom:20px;">
                <div style="font-size:12px;font-weight:700;color:{COLORS['text_secondary']};
                text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">
                    Draft Summary
                </div>
                <div style="font-size:14px;color:{COLORS['text']};">
                    {selected['summary_md'] or "_(no summary)_"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        section_header(
            f"Proposed Changes ({len(selected['proposed_changes'])})",
            "Review each change and choose to approve or reject.",
        )

        decisions: dict[int, str] = {}

        for i, change in enumerate(selected["proposed_changes"]):
            conf = float(change.get("confidence", 0))
            high = conf >= _HIGH_CONFIDENCE
            op = change["op"]
            is_conflict = op == "conflict"

            # Border color based on confidence / conflict
            if is_conflict:
                border_color = COLORS["warning"]
            elif high:
                border_color = f"{COLORS['success']}55"
            else:
                border_color = f"{COLORS['error']}55"

            with st.expander(
                f"#{i + 1}  {op_badge(op)}  &nbsp; {confidence_badge(conf)}",
                expanded=not high,
            ):
                # Decision controls
                col_approve, col_reject, _ = st.columns([1, 1, 3])
                default_approve = high and not is_conflict
                approve = col_approve.checkbox(
                    "Approve",
                    key=f"approve_{selected['id']}_{i}",
                    value=default_approve,
                )
                reject = col_reject.checkbox(
                    "Reject",
                    key=f"reject_{selected['id']}_{i}",
                    value=False,
                )
                if approve and reject:
                    st.error("Pick approve OR reject, not both.")
                if approve:
                    decisions[i] = "approve"
                elif reject:
                    decisions[i] = "reject"

                # Reason & Evidence
                reason = change.get("reason", "")
                evidence = change.get("evidence_quote", "")
                if reason:
                    st.markdown(
                        f"""
                        <div style="background:{COLORS['bg']};border-left:3px solid {COLORS['primary']};
                        border-radius:0 8px 8px 0;padding:10px 14px;margin:10px 0;">
                            <div style="font-size:11px;font-weight:700;color:{COLORS['text_muted']};
                            text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">
                                Reason
                            </div>
                            <div style="font-size:13px;color:{COLORS['text']};">{reason}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                if evidence:
                    st.markdown(
                        f"""
                        <div style="background:{COLORS['bg']};border-left:3px solid {COLORS['accent']};
                        border-radius:0 8px 8px 0;padding:10px 14px;margin:10px 0;">
                            <div style="font-size:11px;font-weight:700;color:{COLORS['text_muted']};
                            text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">
                                Evidence Quote
                            </div>
                            <div style="font-size:13px;color:{COLORS['text_secondary']};font-style:italic;">
                                "{evidence}"
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                fields = change.get("fields") or {}
                if fields:
                    st.markdown(
                        f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};'
                        f'text-transform:uppercase;letter-spacing:0.05em;margin:10px 0 6px;">Fields</div>',
                        unsafe_allow_html=True,
                    )
                    st.json(fields, expanded=False)

                if change["op"] == "update" and change.get("target_task_id"):
                    st.caption(f"Target task ID: `{change['target_task_id']}`")

                if is_conflict:
                    _render_conflict_resolution(
                        draft_id=selected["id"],
                        change_index=i,
                        change=change,
                    )

        # Bulk actions bar
        st.markdown("<div style='margin:24px 0;'></div>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="height:1px;background:{COLORS["border"]};margin:16px 0;"></div>',
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
        if c1.button(
            f"{ICONS['success']} Approve all",
            key=f"approve_all_{selected['id']}",
            use_container_width=True,
        ):
            for i, ch in enumerate(selected["proposed_changes"]):
                if ch["op"] != "conflict":
                    st.session_state[f"approve_{selected['id']}_{i}"] = True
                    st.session_state[f"reject_{selected['id']}_{i}"] = False
            st.rerun()
        if c2.button(
            f"{ICONS['error']} Reject all",
            key=f"reject_all_{selected['id']}",
            use_container_width=True,
        ):
            for i in range(len(selected["proposed_changes"])):
                st.session_state[f"approve_{selected['id']}_{i}"] = False
                st.session_state[f"reject_{selected['id']}_{i}"] = True
            st.rerun()
        if c4.button(
            f"{ICONS['success']} Apply decisions",
            type="primary",
            key=f"apply_{selected['id']}",
            use_container_width=True,
        ):
            if not decisions:
                st.error("No decisions selected.")
                return
            try:
                PlannerService().apply_draft(
                    draft_id=selected["id"], decisions=decisions, approver="reviewer",
                )
                st.success("Decisions applied — Tracker and Change Log are updated.")
                st.session_state.pop("last_draft_id", None)
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to apply: {exc}")


def _render_conflict_resolution(
    *, draft_id: uuid.UUID, change_index: int, change: dict,
) -> None:
    """Side-by-side table for conflict resolution: Merge or Keep Separate."""
    cand_ids = change.get("candidate_task_ids") or []
    st.markdown(
        f"""
        <div style="background:{COLORS['warning']}11;border:1px solid {COLORS['warning']}44;
        border-radius:10px;padding:14px;margin:12px 0;">
            <div style="font-size:13px;font-weight:700;color:{COLORS['warning']};margin-bottom:4px;">
                {ICONS['warning']} Conflict Detected
            </div>
            <div style="font-size:13px;color:{COLORS['text_secondary']};">
                {len(cand_ids)} possible existing task(s) found. Pick the right one below, or create a new task.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with session_scope() as s:
        candidates = []
        for cid in cand_ids:
            try:
                t = tasks_repo.get(s, uuid.UUID(cid))
                if t is not None:
                    candidates.append({
                        "id": str(t.id),
                        "title": t.title,
                        "owner": t.owner or "—",
                        "due_date": t.due_date.isoformat() if t.due_date else "—",
                        "status": t.status,
                    })
            except Exception:
                pass

    fields = change.get("fields") or {}

    # Agent proposal card
    st.markdown(
        f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_secondary"]};'
        f'margin:12px 0 6px;">Proposed Change</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        _candidate_card(
            label="🤖 Agent proposes",
            title=fields.get("title", "—"),
            owner=fields.get("owner", "—"),
            due=fields.get("due_date", "—"),
            status=fields.get("status", "—"),
            bg=f"{COLORS['success']}08",
            border=f"{COLORS['success']}44",
        ),
        unsafe_allow_html=True,
    )

    if candidates:
        st.markdown(
            f'<div style="font-size:12px;font-weight:700;color:{COLORS["text_secondary"]};'
            f'margin:16px 0 8px;">Which existing task does this refer to?</div>',
            unsafe_allow_html=True,
        )

        chunk_size = 3
        for chunk_start in range(0, len(candidates), chunk_size):
            chunk = candidates[chunk_start:chunk_start + chunk_size]
            cols = st.columns(len(chunk))
            for k, (col, cand) in enumerate(zip(cols, chunk, strict=False)):
                j = chunk_start + k
                with col:
                    st.markdown(
                        _candidate_card(
                            label=f"Candidate #{j + 1}",
                            title=cand["title"],
                            owner=cand["owner"],
                            due=cand["due_date"],
                            status=cand["status"],
                        ),
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        f"{ICONS['merge']} Merge → #{j + 1}",
                        key=f"merge_{draft_id}_{change_index}_{j}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        _rewrite_change(
                            draft_id=draft_id,
                            change_index=change_index,
                            new_op="update",
                            target_task_id=cand["id"],
                        )
                        st.rerun()

    if st.button(
        f"{ICONS['separate']} Keep Separate (create new task)",
        key=f"keep_sep_{draft_id}_{change_index}",
        use_container_width=True,
    ):
        _rewrite_change(
            draft_id=draft_id,
            change_index=change_index,
            new_op="create",
            target_task_id=None,
        )
        st.rerun()


def _candidate_card(
    label: str,
    title: str,
    owner: str,
    due: str,
    status: str,
    bg: str | None = None,
    border: str | None = None,
) -> str:
    bg = bg or COLORS["surface_hi"]
    border = border or COLORS["border"]
    return (
        f'<div style="background:{bg};border:1px solid {border};'
        f'border-radius:10px;padding:12px 14px;margin:4px 0;">'
        f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};'
        f'margin-bottom:6px;text-transform:uppercase;letter-spacing:0.05em;">{label}</div>'
        f'<div style="font-weight:700;font-size:14px;color:{COLORS["text"]};margin-bottom:8px;">'
        f'{title}</div>'
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;">'
        f'<div style="font-size:12px;color:{COLORS["text_secondary"]}">👤 {owner}</div>'
        f'<div style="font-size:12px;color:{COLORS["text_secondary"]}">📅 {due}</div>'
        f'<div style="font-size:12px;color:{COLORS["text_secondary"]}">🔖 {status}</div>'
        f'</div></div>'
    )


def _rewrite_change(
    *, draft_id: uuid.UUID, change_index: int, new_op: str, target_task_id: str | None,
) -> None:
    from planner.repositories import drafts_repo as dr

    with session_scope() as s:
        draft = dr.get(s, draft_id)
        if draft is None:
            return
        changes = list(draft.proposed_changes)
        ch = dict(changes[change_index])
        ch["op"] = new_op
        ch["target_task_id"] = target_task_id
        ch["candidate_task_ids"] = []
        ch["reason"] = (ch.get("reason", "") + " [Reviewer resolved conflict.]").strip()
        changes[change_index] = ch
        draft.proposed_changes = changes
