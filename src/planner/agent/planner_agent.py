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
        if not items:
            return []
        # Candidate lookup is local DB + fuzzy string match — fast, not a bottleneck.
        candidates_per_item = [
            build_candidate_matches(session, item=item, limit=5) for item in items
        ]
        # BOTTLENECK (old pattern, now fixed) — the original code called
        # tools.classify_change() inside a `for item in items` loop: one LLM
        # round-trip per item, executed serially. With N=5 items at ~30-60 s
        # each, total classify time was 150-300 s. The fix: send all items in a
        # single batch call so the model classifies everything in one inference
        # pass, reducing N network round-trips to 1.
        classifications = tools.batch_classify_changes(
            items=items, candidates_per_item=candidates_per_item,
        )
        # if LLM returned fewer results than items, pad with "create"
        from planner.agent.schemas import ClassificationResult
        while len(classifications) < len(items):
            classifications.append(ClassificationResult(op="create", reason="fallback", confidence=0.5))

        proposed: list[ProposedChange] = []
        _exclude = {"evidence_quote", "confidence"}
        for item, cls in zip(items, classifications):
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
