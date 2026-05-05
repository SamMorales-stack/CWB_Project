"""Agent tools — thin wrappers around prompted LLM calls."""
from __future__ import annotations

import json

from planner.agent.client import schema_to_user_hint, structured_completion
from planner.agent.prompts import (
    BATCH_CLASSIFY_SYSTEM,
    BATCH_CLASSIFY_USER_TEMPLATE,
    CLASSIFY_SYSTEM,
    CLASSIFY_USER_TEMPLATE,
    DIGEST_SYSTEM,
    DIGEST_USER_TEMPLATE,
    DRAFT_SYSTEM,
    DRAFT_USER_TEMPLATE,
    EXTRACT_SYSTEM,
    EXTRACT_USER_TEMPLATE,
)
from planner.agent.schemas import (
    BatchClassificationResult,
    CandidateMatch,
    ClassificationResult,
    DraftSummary,
    ExtractedItem,
    ExtractionResult,
    ProposedChange,
)
from planner.config import get_settings


def extract_tasks(
    *, note_text: str, source: str, meeting_date: str, title: str,
) -> list[ExtractedItem]:
    """Extract task-shaped items from a meeting note."""
    s = get_settings()
    user = EXTRACT_USER_TEMPLATE.format(
        source=source, meeting_date=meeting_date, title=title, content=note_text,
    ) + schema_to_user_hint(ExtractionResult)
    result = structured_completion(
        deployment=s.azure_openai_deployment_fast,
        system=EXTRACT_SYSTEM,
        user=user,
        schema_model=ExtractionResult,
        temperature=0.1,
    )
    return result.items


def classify_change(
    *, item: ExtractedItem, candidates: list[CandidateMatch],
) -> ClassificationResult:
    """Decide whether the extracted item is create, update, or conflict (single item)."""
    s = get_settings()
    user = CLASSIFY_USER_TEMPLATE.format(
        item_json=item.model_dump_json(indent=2),
        candidates_json=json.dumps([c.model_dump(mode="json") for c in candidates], indent=2),
    ) + schema_to_user_hint(ClassificationResult)
    return structured_completion(
        deployment=s.azure_openai_deployment_fast,
        system=CLASSIFY_SYSTEM,
        user=user,
        schema_model=ClassificationResult,
        temperature=0.1,
    )


def batch_classify_changes(
    *, items: list[ExtractedItem], candidates_per_item: list[list[CandidateMatch]],
) -> list[ClassificationResult]:
    """Classify all extracted items in a single LLM call."""
    s = get_settings()
    payload = [
        {
            "item": item.model_dump(mode="json"),
            "candidates": [c.model_dump(mode="json") for c in candidates],
        }
        for item, candidates in zip(items, candidates_per_item)
    ]
    user = BATCH_CLASSIFY_USER_TEMPLATE.format(
        items_json=json.dumps(payload, indent=2),
    ) + schema_to_user_hint(BatchClassificationResult)
    result = structured_completion(
        deployment=s.azure_openai_deployment_fast,
        system=BATCH_CLASSIFY_SYSTEM,
        user=user,
        schema_model=BatchClassificationResult,
        temperature=0.1,
    )
    return result.classifications


def generate_draft(*, changes: list[ProposedChange]) -> DraftSummary:
    """Compose an executive-friendly summary of the proposed changes."""
    s = get_settings()
    payload = [c.model_dump(mode="json") for c in changes]
    user = (
        DRAFT_USER_TEMPLATE.format(changes_json=json.dumps(payload, indent=2))
        + schema_to_user_hint(DraftSummary)
    )
    return structured_completion(
        deployment=s.azure_openai_deployment_fast,
        system=DRAFT_SYSTEM,
        user=user,
        schema_model=DraftSummary,
        temperature=0.3,
    )


def summarize_changes(*, entries: list[dict]) -> DraftSummary:
    """Compose a weekly executive digest from change_log entries."""
    s = get_settings()
    user = (
        DIGEST_USER_TEMPLATE.format(entries_json=json.dumps(entries, indent=2, default=str))
        + schema_to_user_hint(DraftSummary)
    )
    return structured_completion(
        deployment=s.azure_openai_deployment_main,
        system=DIGEST_SYSTEM,
        user=user,
        schema_model=DraftSummary,
        temperature=0.4,
    )
