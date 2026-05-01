"""Convert tasks repository search hits into CandidateMatch objects for the LLM."""
from __future__ import annotations

from sqlalchemy.orm import Session

from planner.agent.schemas import CandidateMatch, ExtractedItem


def build_candidate_matches(
    session: Session, *, item: ExtractedItem, limit: int = 5,
) -> list[CandidateMatch]:
    """Find existing tasks plausibly matching the extracted item."""
    # Lazy import — tasks_repo lives in planner.repositories which is built in a separate task.
    from planner.repositories import tasks_repo

    query_parts = [item.title]
    if item.owner:
        query_parts.append(item.owner)
    query = " ".join(query_parts)
    candidates = tasks_repo.search_candidates(session, query=query, limit=limit)
    return [
        CandidateMatch(
            task_id=str(t.id),
            title=t.title,
            owner=t.owner,
            status=t.status,
            due_date=t.due_date,
        )
        for t in candidates
    ]
