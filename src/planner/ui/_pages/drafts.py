"""Drafts page: review and approve proposed plan changes."""
from __future__ import annotations

import uuid

import streamlit as st

from planner.db import session_scope
from planner.repositories import drafts_repo, tasks_repo
from planner.service import PlannerService

_HIGH_CONFIDENCE = 0.8


def render() -> None:
    st.title("Drafts")
    st.caption(
        "High-confidence changes are pre-checked for approval. "
        "Low-confidence changes are flagged and require an explicit click."
    )

    with session_scope() as s:
        pending = drafts_repo.list_pending(s)
        # Snapshot to plain dicts before session closes
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
        st.info("No pending drafts. Process a note in the Inbox to create one.")
        return

    col_list, col_detail = st.columns([1, 3])

    with col_list:
        st.subheader("Pending")
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
        st.subheader("Draft summary")
        st.markdown(selected["summary_md"] or "_(no summary)_")
        st.subheader("Proposed changes")

        decisions: dict[int, str] = {}

        for i, change in enumerate(selected["proposed_changes"]):
            conf = float(change.get("confidence", 0))
            high = conf >= _HIGH_CONFIDENCE
            badge = "🟢 High" if high else ("🟡 Med" if conf >= 0.5 else "🔴 Low")

            with st.expander(
                f"#{i + 1} · {change['op'].upper()} · {badge} ({conf:.0%})",
                expanded=not high,
            ):
                col_approve, col_reject, _ = st.columns([1, 1, 3])
                default_approve = high and change["op"] != "conflict"
                approve = col_approve.checkbox(
                    "Approve", key=f"approve_{selected['id']}_{i}", value=default_approve,
                )
                reject = col_reject.checkbox(
                    "Reject", key=f"reject_{selected['id']}_{i}", value=False,
                )
                if approve and reject:
                    st.error("Pick approve OR reject, not both.")
                if approve:
                    decisions[i] = "approve"
                elif reject:
                    decisions[i] = "reject"

                st.markdown(f"**Reason:** {change.get('reason', '')}")
                st.markdown(f"**Evidence:** _{change.get('evidence_quote', '')}_")
                fields = change.get("fields") or {}
                if fields:
                    st.json(fields, expanded=False)
                if change["op"] == "update" and change.get("target_task_id"):
                    st.caption(f"Target task ID: `{change['target_task_id']}`")
                if change["op"] == "conflict":
                    _render_conflict_resolution(
                        draft_id=selected["id"],
                        change_index=i,
                        change=change,
                    )

        st.markdown("---")
        c1, c2, c3 = st.columns([1, 1, 2])
        if c1.button("Approve all", key=f"approve_all_{selected['id']}"):
            for i, ch in enumerate(selected["proposed_changes"]):
                if ch["op"] != "conflict":
                    st.session_state[f"approve_{selected['id']}_{i}"] = True
                    st.session_state[f"reject_{selected['id']}_{i}"] = False
            st.rerun()
        if c2.button("Reject all", key=f"reject_all_{selected['id']}"):
            for i in range(len(selected["proposed_changes"])):
                st.session_state[f"approve_{selected['id']}_{i}"] = False
                st.session_state[f"reject_{selected['id']}_{i}"] = True
            st.rerun()
        if c3.button("Apply decisions", type="primary", key=f"apply_{selected['id']}"):
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
    st.error(
        f"⚠️ Conflict — {len(cand_ids)} possible existing task(s). "
        "Pick the right one below, or create a new task."
    )

    with session_scope() as s:
        candidates = []
        for cid in cand_ids:
            try:
                t = tasks_repo.get(s, uuid.UUID(cid))
                if t is not None:
                    candidates.append({
                        "id": str(t.id), "title": t.title, "owner": t.owner or "—",
                        "due_date": t.due_date.isoformat() if t.due_date else "—",
                        "status": t.status,
                    })
            except Exception:
                pass

    fields = change.get("fields") or {}

    # Render as a clean comparison table
    st.markdown("**Proposed change vs. existing candidates:**")

    _card = lambda label, title, owner, due, status, bg="#1e1e2e": (  # noqa: E731
        f'<div style="background:{bg};border-radius:8px;padding:10px 14px;margin:4px 0">'
        f'<div style="font-size:11px;color:#aaa;margin-bottom:4px">{label}</div>'
        f'<div style="font-weight:600;font-size:14px;margin-bottom:6px">{title}</div>'
        f'<div style="font-size:12px;color:#ccc">👤 {owner}</div>'
        f'<div style="font-size:12px;color:#ccc">📅 {due}</div>'
        f'<div style="font-size:12px;color:#ccc">🔖 {status}</div>'
        f'</div>'
    )

    # Agent proposal card (full width)
    st.markdown(
        _card(
            "🤖 Agent proposes",
            fields.get("title", "—"),
            fields.get("owner", "—"),
            fields.get("due_date", "—"),
            fields.get("status", "—"),
            bg="#1a2a1a",
        ),
        unsafe_allow_html=True,
    )

    st.markdown("**Which existing task does this refer to?**")

    # Candidates in rows of up to 4
    chunk_size = 4
    for chunk_start in range(0, len(candidates), chunk_size):
        chunk = candidates[chunk_start:chunk_start + chunk_size]
        cols = st.columns(len(chunk))
        for k, (col, cand) in enumerate(zip(cols, chunk, strict=False)):
            j = chunk_start + k
            with col:
                st.markdown(
                    _card(
                        f"Candidate #{j + 1}",
                        cand["title"],
                        cand["owner"],
                        cand["due_date"],
                        cand["status"],
                    ),
                    unsafe_allow_html=True,
                )
                if st.button(f"Merge →#{j + 1}", key=f"merge_{draft_id}_{change_index}_{j}",
                             use_container_width=True):
                    _rewrite_change(
                        draft_id=draft_id, change_index=change_index,
                        new_op="update", target_task_id=cand["id"],
                    )
                    st.rerun()

    if st.button(
        "➕ Keep Separate (create a new task)",
        key=f"keep_sep_{draft_id}_{change_index}",
    ):
        _rewrite_change(
            draft_id=draft_id, change_index=change_index,
            new_op="create", target_task_id=None,
        )
        st.rerun()


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
