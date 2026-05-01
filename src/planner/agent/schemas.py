"""Pydantic schemas for structured LLM outputs."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


Status = Literal["not_started", "in_progress", "blocked", "done"]
Priority = Literal["low", "med", "high"]
Op = Literal["create", "update", "delete"]


class ExtractedItem(BaseModel):
    """A task-shaped item extracted from a meeting note."""

    title: str
    description: str | None = None
    owner: str | None = None
    due_date: date | None = None
    status: Status | None = None
    priority: Priority | None = None
    dependency_hints: list[str] = Field(default_factory=list)
    evidence_quote: str
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    items: list[ExtractedItem]


class CandidateMatch(BaseModel):
    task_id: str
    title: str
    owner: str | None = None
    status: Status | None = None
    due_date: date | None = None


class ClassificationResult(BaseModel):
    """Output of classify_change for one extracted item."""

    op: Literal["create", "update", "conflict"]
    target_task_id: str | None = None
    candidate_task_ids: list[str] = Field(default_factory=list)
    fields_to_change: dict = Field(default_factory=dict)
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class ProposedChange(BaseModel):
    """One proposed change attached to a draft."""

    op: Literal["create", "update", "conflict"]
    target_task_id: str | None = None
    candidate_task_ids: list[str] = Field(default_factory=list)
    fields: dict = Field(default_factory=dict)
    evidence_quote: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class DraftSummary(BaseModel):
    summary_md: str
