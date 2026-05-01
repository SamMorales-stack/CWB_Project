"""Change Log page: audit trail with diff view and weekly digest."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from planner.db import session_scope
from planner.repositories import change_log_repo
from planner.service import PlannerService


def render() -> None:
    st.title("Change Log")
    st.caption("Every applied change with before/after snapshots and source evidence.")

    col_btn, _ = st.columns([1, 4])
    if col_btn.button("📰 Generate weekly digest"):
        with st.spinner("Summarising the last 7 days…"):
            try:
                summary = PlannerService().weekly_digest()
                st.session_state["weekly_digest_md"] = summary
            except Exception as exc:
                st.error(f"Digest failed: {exc}")

    if "weekly_digest_md" in st.session_state:
        st.markdown("### Weekly digest")
        st.markdown(st.session_state["weekly_digest_md"])
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
        st.info("No applied changes yet.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, use_container_width=True)


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
            parts.append(f"{k}: {b!r} -> {a!r}")
    return "; ".join(parts)
