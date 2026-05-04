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
    empty_state,
)

_HIGH_CONFIDENCE = 0.8

# ── Op palette (local, matches design spec exactly) ───────────────────────────
_OP_COLOR = {
    "create": "#2DD4BF",
    "update": "#2563EB",
    "delete": "#F87171",
    "conflict": "#FBBF24",
}
_OP_LABEL = {
    "create": "CREATE",
    "update": "UPDATE",
    "delete": "DELETE",
    "conflict": "CONFLICT",
}


# ── Badge helpers ─────────────────────────────────────────────────────────────

def _op_badge_html(op: str) -> str:
    color = _OP_COLOR.get(op, COLORS["text_secondary"])
    label = _OP_LABEL.get(op, op.upper())
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:20px;'
        f'font-size:11px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;'
        f'background:{color}33;color:{color};border:1px solid {color}66;">'
        f'{label}</span>'
    )


def _conf_badge_html(conf: float) -> str:
    if conf >= 0.8:
        color = COLORS["success"]
        label = "High"
    elif conf >= 0.5:
        color = COLORS["warning"]
        label = "Medium"
    else:
        color = COLORS["error"]
        label = "Low"
    pct = int(conf * 100)
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:20px;'
        f'font-size:11px;font-weight:700;letter-spacing:0.05em;'
        f'background:{color}33;color:{color};border:1px solid {color}66;">'
        f'{label} ({pct}%)</span>'
    )


# ── Block quote helper (reason / evidence) ────────────────────────────────────

def _blockquote(heading: str, body: str, italic: bool = False) -> str:
    style_body = "font-style:italic;" if italic else ""
    return (
        f'<div style="background:{COLORS["bg"]};border-left:3px solid {COLORS["primary"]};'
        f'border-radius:0 6px 6px 0;padding:10px 14px;margin:10px 0;">'
        f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};'
        f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">{heading}</div>'
        f'<div style="font-size:13px;color:{COLORS["text"]};{style_body}">{body}</div>'
        f'</div>'
    )


# ── Main page ─────────────────────────────────────────────────────────────────

def render() -> None:
    # ── Page title ────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="margin-bottom:20px;">
            <div style="font-size:26px;font-weight:800;color:{COLORS['text']};
            letter-spacing:-0.02em;">Drafts</div>
            <div style="font-size:13px;color:{COLORS['text_muted']};margin-top:4px;">
                High-confidence changes are pre-checked for approval.
                Low-confidence changes are flagged and require an explicit decision.
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

    # ── Two-column layout ─────────────────────────────────────────────────────
    col_list, col_detail = st.columns([1, 3])

    # ── Left column: draft list ───────────────────────────────────────────────
    with col_list:
        st.markdown(
            f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;">PENDING</div>',
            unsafe_allow_html=True,
        )

        # Restore previously-selected draft
        last = st.session_state.get("last_draft_id")
        default_idx = 0
        if last:
            for i, d in enumerate(pending_data):
                if str(d["id"]) == last:
                    default_idx = i
                    break

        idx = st.radio(
            "Select a draft",
            options=range(len(pending_data)),
            format_func=lambda i: (
                f"{pending_data[i]['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
                f"{len(pending_data[i]['proposed_changes'])} change(s)"
            ),
            index=default_idx,
            label_visibility="collapsed",
        )

        selected = pending_data[idx]
        st.session_state["last_draft_id"] = str(selected["id"])

    # ── Right column: draft detail ────────────────────────────────────────────
    with col_detail:
        # DRAFT SUMMARY section
        st.markdown(
            f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">DRAFT SUMMARY</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="background:{COLORS["surface"]};border:1px solid {COLORS["border"]};'
            f'border-radius:12px;padding:20px;margin-bottom:20px;">'
            f'<div style="font-size:14px;color:{COLORS["text"]};">'
            f'{selected["summary_md"] or "<em style=\'color:" + COLORS["text_muted"] + "\';>(no summary)</em>"}'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # PROPOSED CHANGES section label
        n_changes = len(selected["proposed_changes"])
        st.markdown(
            f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">'
            f'PROPOSED CHANGES ({n_changes})</div>',
            unsafe_allow_html=True,
        )

        decisions: dict[int, str] = {}

        for i, change in enumerate(selected["proposed_changes"]):
            conf = float(change.get("confidence", 0))
            high = conf >= _HIGH_CONFIDENCE
            op = change["op"]
            is_conflict = op == "conflict"
            title_text = (change.get("fields") or {}).get("title", "") or change.get("title", "") or f"Change #{i + 1}"
            reason = change.get("reason", "")
            evidence = change.get("evidence_quote", "")

            # ── Flat card ─────────────────────────────────────────────────────
            # Build card header HTML
            conflict_bar = ""
            if is_conflict:
                cand_ids = change.get("candidate_task_ids") or []
                conflict_bar = (
                    f'<div style="background:{COLORS["warning"]}1A;'
                    f'border:1px solid {COLORS["warning"]}66;border-radius:8px;'
                    f'padding:12px;margin:12px 0;color:{COLORS["warning"]};'
                    f'font-size:13px;font-weight:600;">'
                    f'&#9888; Conflict &mdash; {len(cand_ids)} possible existing task(s). '
                    f'Pick the right one below, or create a new task.'
                    f'</div>'
                )

            reason_html = _blockquote("REASON", reason) if reason else ""
            evidence_html = (
                _blockquote("EVIDENCE QUOTE", f'&ldquo;{evidence}&rdquo;', italic=True)
                if evidence else ""
            )

            st.markdown(
                f'<div style="background:{COLORS["surface"]};border:1px solid {COLORS["border"]};'
                f'border-radius:12px;padding:20px;margin-bottom:4px;">'
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
                f'{_op_badge_html(op)}'
                f'{_conf_badge_html(conf)}'
                f'</div>'
                f'<div style="font-size:16px;font-weight:700;color:{COLORS["text"]};'
                f'margin-bottom:12px;">{title_text}</div>'
                f'{conflict_bar}'
                f'{reason_html}'
                f'{evidence_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Approve / Reject checkboxes live BELOW the HTML card
            default_approve = high and not is_conflict
            chk_col_approve, chk_col_reject, _ = st.columns([1, 1, 4])
            approve = chk_col_approve.checkbox(
                "Approve",
                key=f"approve_{selected['id']}_{i}",
                value=default_approve,
            )
            reject = chk_col_reject.checkbox(
                "Reject",
                key=f"reject_{selected['id']}_{i}",
                value=False,
            )
            if approve and reject:
                st.error("Pick Approve OR Reject, not both.")

            if approve:
                decisions[i] = "approve"
            elif reject:
                decisions[i] = "reject"

            # Extra spacer between cards
            st.markdown(
                '<div style="margin-bottom:8px;"></div>',
                unsafe_allow_html=True,
            )

            # Conflict resolution UI
            if is_conflict:
                _render_conflict_resolution(
                    draft_id=selected["id"],
                    change_index=i,
                    change=change,
                )

        # ── Bottom action bar ─────────────────────────────────────────────────
        st.markdown(
            f'<div style="height:1px;background:{COLORS["border"]};margin:24px 0 16px;"></div>',
            unsafe_allow_html=True,
        )

        bar_col1, bar_col2, bar_spacer, bar_col3 = st.columns([1, 1, 2, 1])

        if bar_col1.button(
            "Approve all",
            key=f"approve_all_{selected['id']}",
            use_container_width=True,
        ):
            for i, ch in enumerate(selected["proposed_changes"]):
                if ch["op"] != "conflict":
                    st.session_state[f"approve_{selected['id']}_{i}"] = True
                    st.session_state[f"reject_{selected['id']}_{i}"] = False
            st.rerun()

        if bar_col2.button(
            "Reject all",
            key=f"reject_all_{selected['id']}",
            use_container_width=True,
        ):
            for i in range(len(selected["proposed_changes"])):
                st.session_state[f"approve_{selected['id']}_{i}"] = False
                st.session_state[f"reject_{selected['id']}_{i}"] = True
            st.rerun()

        if bar_col3.button(
            "Apply decisions",
            type="primary",
            key=f"apply_{selected['id']}",
            use_container_width=True,
        ):
            if not decisions:
                st.error("No decisions selected.")
                return
            try:
                PlannerService().apply_draft(
                    draft_id=selected["id"],
                    decisions=decisions,
                    approver="reviewer",
                )
                st.success("Decisions applied — Tracker and Change Log are updated.")
                st.session_state.pop("last_draft_id", None)
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to apply: {exc}")


# ── Conflict resolution ───────────────────────────────────────────────────────

def _render_conflict_resolution(
    *, draft_id: uuid.UUID, change_index: int, change: dict,
) -> None:
    """Render conflict resolution: AGENT PROPOSES card + CANDIDATE cards with Merge/Keep buttons."""
    cand_ids = change.get("candidate_task_ids") or []

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

    # Agent proposes card
    st.markdown(
        f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin:12px 0 6px;">AGENT PROPOSES</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        _candidate_card(
            label="Agent proposes",
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
        for j, cand in enumerate(candidates):
            st.markdown(
                f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};'
                f'text-transform:uppercase;letter-spacing:0.08em;margin:12px 0 6px;">'
                f'CANDIDATE #{j + 1}</div>',
                unsafe_allow_html=True,
            )
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


# ── Candidate card helper ────────────────────────────────────────────────────

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
        f'<div style="font-size:12px;color:{COLORS["text_secondary"]}">&#128100; {owner}</div>'
        f'<div style="font-size:12px;color:{COLORS["text_secondary"]}">&#128197; {due}</div>'
        f'<div style="font-size:12px;color:{COLORS["text_secondary"]}">&#128278; {status}</div>'
        f'</div></div>'
    )


# ── Draft rewrite helper ──────────────────────────────────────────────────────

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
