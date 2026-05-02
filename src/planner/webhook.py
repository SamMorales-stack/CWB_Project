"""
Webhook API — lets external tools (Teams, Zoom, Power Automate, etc.)
POST meeting transcripts directly into PlanForge without manual copy-paste.

Runs on port 8502 alongside the Streamlit UI (port 8501).

Authentication: pass your WEBHOOK_API_KEY in the X-API-Key header.

Example curl:
    curl -X POST http://localhost:8502/api/ingest \\
      -H "Content-Type: application/json" \\
      -H "X-API-Key: your-key-here" \\
      -d '{
        "title": "Weekly site meeting",
        "content": "Rina confirmed riser strategy is blocked...",
        "source": "meeting",
        "meeting_date": "2026-05-03",
        "attendees": ["Rina Ali", "Ivy Chung"]
      }'

Power Automate flow:
    Trigger: "When a Teams meeting ends"
    Action:  HTTP POST to https://<your-domain>/api/ingest
             Body: { title, content (transcript), meeting_date, attendees }
"""
from __future__ import annotations

import threading
from datetime import date, datetime

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from planner.config import get_settings

app = FastAPI(
    title="PlanForge Webhook API",
    description="Accepts meeting transcripts and triggers the agent pipeline automatically.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class IngestPayload(BaseModel):
    title: str
    content: str
    source: str = "meeting"
    meeting_date: str | None = None
    attendees: list[str] = []


class IngestResponse(BaseModel):
    status: str
    note_id: str
    draft_id: str
    changes_proposed: int
    summary: str


def _require_api_key(x_api_key: str | None) -> None:
    expected = get_settings().webhook_api_key
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")


@app.get("/api/health")
def health() -> dict:
    """Health check — no auth required."""
    return {"status": "ok", "service": "PlanForge Webhook API"}


@app.post("/api/ingest", response_model=IngestResponse)
def ingest(
    payload: IngestPayload,
    x_api_key: str | None = Header(default=None),
) -> IngestResponse:
    """
    Ingest a meeting transcript and run the full agent pipeline.

    The agent extracts tasks, classifies them against the existing plan,
    and creates a pending draft ready for human review in the Drafts page.
    """
    _require_api_key(x_api_key)

    from planner.service import PlannerService

    meeting_date: date | None = None
    if payload.meeting_date:
        try:
            meeting_date = datetime.fromisoformat(payload.meeting_date).date()
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"meeting_date must be ISO format (YYYY-MM-DD), got: {payload.meeting_date}",
            )

    service = PlannerService()
    note = service.ingest_note(
        text=payload.content,
        source=payload.source,
        title=payload.title,
        meeting_date=meeting_date or date.today(),
        attendees=payload.attendees,
    )

    try:
        draft = service.run_pipeline(note_id=note.id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {exc}") from exc

    return IngestResponse(
        status="ok",
        note_id=str(note.id),
        draft_id=str(draft.id),
        changes_proposed=len(draft.proposed_changes),
        summary=draft.summary_md or "",
    )


def start(port: int = 8502) -> None:
    """Start the webhook server (blocking)."""
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


def start_in_background(port: int = 8502) -> None:
    """Start the webhook server in a daemon thread alongside Streamlit."""
    t = threading.Thread(target=start, kwargs={"port": port}, daemon=True)
    t.start()
