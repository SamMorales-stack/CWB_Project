"""High-level agent that runs the extract → classify → draft pipeline."""
from __future__ import annotations

from sqlalchemy.orm import Session

from planner.agent import tools
from planner.agent.schemas import DraftSummary, ExtractedItem, ProposedChange
from planner.matcher import build_candidate_matches


class PlannerAgent:
    """Stateless orchestrator over agent tools."""

    def extract(
        self, *, note_text: str, source: str, meeting_date: str, title: str,
    ) -> list[ExtractedItem]:
        return tools.extract_tasks(
            note_text=note_text, source=source, meeting_date=meeting_date, title=title,
        )

    def classify_all(
        self, session: Session, *, items: list[ExtractedItem],
    ) -> list[ProposedChange]:
        proposed: list[ProposedChange] = []
        for item in items:
            candidates = build_candidate_matches(session, item=item, limit=5)
            cls = tools.classify_change(item=item, candidates=candidates)
            _exclude = {"evidence_quote", "confidence"}
            fields = (
                cls.fields_to_change
                if cls.op == "update"
                else item.model_dump(mode="json", exclude_none=True, exclude=_exclude)
            )
            proposed.append(ProposedChange(
                op=cls.op,
                target_task_id=cls.target_task_id,
                candidate_task_ids=cls.candidate_task_ids,
                fields=fields,
                evidence_quote=item.evidence_quote,
                confidence=min(item.confidence, cls.confidence),
                reason=cls.reason,
            ))
        return proposed

    def draft(self, *, changes: list[ProposedChange]) -> DraftSummary:
        return tools.generate_draft(changes=changes)

    def weekly_digest(self, *, entries: list[dict]) -> DraftSummary:
        return tools.summarize_changes(entries=entries)
