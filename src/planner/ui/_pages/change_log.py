"""Change Log page: audit trail with diff view and weekly digest."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from planner.db import session_scope
from planner.repositories import change_log_repo
from planner.service import PlannerService
from planner.ui.styles import (
    COLORS,
    ICONS,
    empty_state,
    op_badge,
    section_header,
    timeline_item,
)


def render() -> None:
    # Header
    st.markdown(
        f"""
        <div style="margin-bottom:4px;">
            <div style="font-size:28px;font-weight:800;color:{COLORS['text']};letter-spacing:-0.02em;">
                {ICONS['changelog']} Change Log
            </div>
            <div style="font-size:14px;color:{COLORS['text_muted']};margin-top:6px;max-width:640px;">
                Every applied change with before/after snapshots and source evidence.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Weekly digest action
    st.markdown(
        f'<div style="background:{COLORS["surface"]};border:1px solid {COLORS["border"]};'
        f'border-radius:12px;padding:16px;margin:16px 0;display:flex;'
        f'justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;">',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="font-size:14px;font-weight:600;color:{COLORS["text"]};">'
        f'{ICONS['info']} Weekly Executive Digest</div>',
        unsafe_allow_html=True,
    )
    if st.button(
        f"{ICONS['applied']} Generate digest",
        type="primary",
        key="gen_digest",
    ):
        with st.spinner("Summarising the last 7 days…"):
            try:
                summary = PlannerService().weekly_digest()
                st.session_state["weekly_digest_md"] = summary
            except Exception as exc:
                st.error(f"Digest failed: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)

    if "weekly_digest_md" in st.session_state:
        st.markdown(
            f"""
            <div style="background:{COLORS['surface']};border:1px solid {COLORS['border']};
            border-radius:12px;padding:20px;margin:12px 0;">
                <div style="font-size:12px;font-weight:700;color:{COLORS['text_secondary']};
                text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;">
                    Generated Digest
                </div>
                <div style="font-size:14px;color:{COLORS['text']};">
                    {st.session_state["weekly_digest_md"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("---")

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

    # Summary stats
    total_changes = len(rows)
    create_count = sum(1 for r in rows if r["op"] == "create")
    update_count = sum(1 for r in rows if r["op"] == "update")
    delete_count = sum(1 for r in rows if r["op"] == "delete")

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(
            f'<div style="text-align:center;background:{COLORS["surface"]};'
            f'border:1px solid {COLORS["border"]};border-radius:10px;padding:12px;">'
            f'<div style="font-size:22px;font-weight:800;color:{COLORS["text"]};">{total_changes}</div>'
            f'<div style="font-size:10px;font-weight:700;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;letter-spacing:0.05em;">Total Changes</div></div>',
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            f'<div style="text-align:center;background:{COLORS["surface"]};'
            f'border:1px solid {COLORS["border"]};border-radius:10px;padding:12px;">'
            f'<div style="font-size:22px;font-weight:800;color:{COLORS["success"]};">{create_count}</div>'
            f'<div style="font-size:10px;font-weight:700;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;letter-spacing:0.05em;">Created</div></div>',
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            f'<div style="text-align:center;background:{COLORS["surface"]};'
            f'border:1px solid {COLORS["border"]};border-radius:10px;padding:12px;">'
            f'<div style="font-size:22px;font-weight:800;color:{COLORS["primary"]};">{update_count}</div>'
            f'<div style="font-size:10px;font-weight:700;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;letter-spacing:0.05em;">Updated</div></div>',
            unsafe_allow_html=True,
        )
    with s4:
        st.markdown(
            f'<div style="text-align:center;background:{COLORS["surface"]};'
            f'border:1px solid {COLORS["border"]};border-radius:10px;padding:12px;">'
            f'<div style="font-size:22px;font-weight:800;color:{COLORS["error"]};">{delete_count}</div>'
            f'<div style="font-size:10px;font-weight:700;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;letter-spacing:0.05em;">Deleted</div></div>',
            unsafe_allow_html=True,
        )

    section_header("Audit Timeline", "Chronological history of all applied plan changes.")

    # Timeline view
    for row in rows:
        time_str = row["applied_at"].strftime("%Y-%m-%d %H:%M") if row["applied_at"] else "—"
        st.markdown(
            timeline_item(
                time_str=time_str,
                op=row["op"],
                diff=row["diff"],
                evidence=row["evidence"] or "—",
                approved_by=row["approved_by"] or "system",
            ),
            unsafe_allow_html=True,
        )


def _format_diff(before: dict | None, after: dict | None) -> str:
    if before is None and after is not None:
        return "+ " + ", ".join(f"{k}={v!r}" for k, v in after.items() if v is not None)
    if after is None and before is not None:
        return "- " + ", ".join(f"{k}={v!r}" for k, v in before.items() if v is not None)
    if before is None or after is None:
        return ""
    parts = []
    for k in sorted(set(before) | set(after)):
        b, a = before.get(k), after.get(k)
        if b != a:
            parts.append(f"{k}: {b!r} → {a!r}")
    return "; ".join(parts)
