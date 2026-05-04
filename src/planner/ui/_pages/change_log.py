"""Change Log page: audit trail with diff view and weekly digest."""
from __future__ import annotations

import streamlit as st

from planner.db import session_scope
from planner.repositories import change_log_repo
from planner.service import PlannerService
from planner.ui.styles import COLORS, OP_LABELS, OP_PALETTE, empty_state

# ── Status label mapping ───────────────────────────────────────────────────

_STATUS_LABELS = {
    "not_started": "Not Started",
    "in_progress": "In Progress",
    "blocked": "On Hold",
    "done": "Done",
}


def _fmt_val(key: str, val: object) -> str:
    if key == "status" and isinstance(val, str):
        return _STATUS_LABELS.get(val, val)
    return str(val) if val is not None else "—"


def _format_diff(before: dict | None, after: dict | None) -> str:
    if before is None and after is not None:
        return "+ " + ", ".join(
            f"{k}={_fmt_val(k, v)}" for k, v in after.items() if v is not None
        )
    if after is None and before is not None:
        return "- " + ", ".join(
            f"{k}={_fmt_val(k, v)}" for k, v in before.items() if v is not None
        )
    if before is None or after is None:
        return ""
    parts = []
    for k in sorted(set(before) | set(after)):
        b, a = before.get(k), after.get(k)
        if b != a:
            parts.append(f"{k}: {_fmt_val(k, b)} → {_fmt_val(k, a)}")
    return "; ".join(parts)


def _op_badge(op: str) -> str:
    """Pill badge for an operation type."""
    color = OP_PALETTE.get(op, COLORS["text_secondary"])
    label = OP_LABELS.get(op, op.upper()).upper()
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:20px;'
        f'font-size:11px;font-weight:700;background:{color}33;color:{color};'
        f'border:1px solid {color}55;letter-spacing:0.04em;">'
        f'{label}</span>'
    )


def _timeline_entry(time_str: str, op: str, diff: str, evidence: str, approved_by: str) -> str:
    """Render a single timeline item as HTML."""
    dot_color = OP_PALETTE.get(op, COLORS["text_secondary"])
    evidence_text = f"“{evidence}”" if evidence and evidence != "—" else evidence
    return (
        f'<div style="display:flex;gap:16px;margin:0 0 0 0;">'
        f'  <div style="display:flex;flex-direction:column;align-items:center;flex-shrink:0;">'
        f'    <div style="width:10px;height:10px;border-radius:50%;background:{dot_color};'
        f'    margin-top:16px;box-shadow:0 0 0 3px {dot_color}33;"></div>'
        f'    <div style="width:2px;flex:1;min-height:24px;background:{COLORS["border"]};'
        f'    margin-top:4px;"></div>'
        f'  </div>'
        f'  <div style="flex:1;background:{COLORS["surface"]};border:1px solid {COLORS["border"]};'
        f'  border-radius:12px;padding:14px 16px;margin-bottom:10px;">'
        f'    <div style="display:flex;justify-content:space-between;align-items:center;'
        f'    margin-bottom:8px;">'
        f'      <span style="font-size:13px;color:{COLORS["text_muted"]};">{time_str}</span>'
        f'      {_op_badge(op)}'
        f'    </div>'
        f'    <div style="font-size:13px;color:{COLORS["text"]};margin-bottom:6px;'
        f'    line-height:1.5;">{diff}</div>'
        f'    <div style="font-size:13px;color:{COLORS["text_secondary"]};margin-bottom:6px;">'
        f'    <em>{evidence_text}</em></div>'
        f'    <div style="font-size:12px;color:{COLORS["text_muted"]};">'
        f'    Approved by {approved_by}</div>'
        f'  </div>'
        f'</div>'
    )


def render() -> None:
    # ── 1. Page title ──────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="margin-bottom:20px;">
            <div style="font-size:26px;font-weight:800;color:{COLORS['text']};
            letter-spacing:-0.02em;line-height:1.2;">
                Change Log
            </div>
            <div style="font-size:13px;color:{COLORS['text_muted']};margin-top:6px;">
                Every applied change with before/after snapshots and source evidence.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 2. Weekly Executive Digest banner ─────────────────────────────────
    with st.container():
        st.markdown(
            f'<div style="background:{COLORS["surface"]};border:1px solid {COLORS["border"]};'
            f'border-radius:12px;padding:16px 20px;margin-bottom:16px;">',
            unsafe_allow_html=True,
        )
        col_label, col_btn = st.columns([4, 1])
        with col_label:
            st.markdown(
                f'<div style="font-size:16px;font-weight:700;color:{COLORS["text"]};'
                f'padding-top:6px;">Weekly Executive Digest</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("Generate digest", type="primary", key="gen_digest"):
                with st.spinner("Summarising the last 7 days…"):
                    try:
                        summary = PlannerService().weekly_digest()
                        st.session_state["weekly_digest_md"] = summary
                    except Exception as exc:
                        st.error(f"Digest failed: {exc}")

        if "weekly_digest_md" in st.session_state:
            st.markdown(
                f'<div style="margin-top:16px;padding-top:16px;'
                f'border-top:1px solid {COLORS["border"]};">'
                f'<div style="font-size:13px;color:{COLORS["text"]};line-height:1.6;">'
                f'{st.session_state["weekly_digest_md"]}'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Load entries ───────────────────────────────────────────────────────
    with session_scope() as s:
        entries = change_log_repo.list_recent(s, limit=200)
        rows = [
            {
                "applied_at": e.applied_at,
                "op": e.op,
                "task_id": str(e.task_id) if e.task_id else "",
                "diff": _format_diff(e.before, e.after),
                "evidence": e.evidence_quote,
                "approved_by": e.approved_by,
            }
            for e in entries
        ]

    if not rows:
        empty_state(
            icon="🕘",
            title="No applied changes yet",
            subtitle="Approved drafts will appear here with full audit history.",
        )
        return

    # ── 3. Stat cards ──────────────────────────────────────────────────────
    total_changes = len(rows)
    create_count = sum(1 for r in rows if r["op"] == "create")
    update_count = sum(1 for r in rows if r["op"] == "update")
    delete_count = sum(1 for r in rows if r["op"] == "delete")

    c1, c2, c3, c4 = st.columns(4)

    def _stat_card(value: int, label: str, color: str) -> str:
        return (
            f'<div style="background:{COLORS["surface"]};border:1px solid {COLORS["border"]};'
            f'border-radius:12px;padding:20px 16px;text-align:center;">'
            f'<div style="font-size:28px;font-weight:800;color:{color};line-height:1;">'
            f'{value}</div>'
            f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;letter-spacing:0.06em;margin-top:6px;">'
            f'{label}</div>'
            f'</div>'
        )

    with c1:
        st.markdown(_stat_card(total_changes, "Total Changes", COLORS["text"]), unsafe_allow_html=True)
    with c2:
        st.markdown(_stat_card(create_count, "Created", COLORS["success"]), unsafe_allow_html=True)
    with c3:
        st.markdown(_stat_card(update_count, "Updated", COLORS["primary"]), unsafe_allow_html=True)
    with c4:
        st.markdown(_stat_card(delete_count, "Deleted", COLORS["error"]), unsafe_allow_html=True)

    # ── 4. Audit Timeline section label ───────────────────────────────────
    st.markdown(
        f'<div style="font-size:11px;font-weight:700;color:{COLORS["text_muted"]};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-top:24px;margin-bottom:12px;">'
        f'AUDIT TIMELINE</div>',
        unsafe_allow_html=True,
    )

    # ── 5. Timeline items ──────────────────────────────────────────────────
    timeline_html = ""
    for row in rows:
        time_str = row["applied_at"].strftime("%Y-%m-%d %H:%M") if row["applied_at"] else "—"
        timeline_html += _timeline_entry(
            time_str=time_str,
            op=row["op"],
            diff=row["diff"],
            evidence=row["evidence"] or "—",
            approved_by=row["approved_by"] or "system",
        )

    st.markdown(
        f'<div style="padding-left:4px;">{timeline_html}</div>',
        unsafe_allow_html=True,
    )
