"""Timeline schemas."""
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class TimelineEventItem(BaseModel):
    event_id: uuid.UUID
    event_type: str
    occurred_at: datetime
    title: str
    subtitle: str | None = None
    provider: str | None = None
    source_ref: uuid.UUID | None = None
    source_ref_type: str | None = None
    flags: Any = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TimelineListResponse(BaseModel):
    events: list[TimelineEventItem]
    total: int


class TimelineNoteRequest(BaseModel):
    """Create a manual text note on the timeline."""
    profile_id: uuid.UUID
    text: str = Field(..., min_length=1, max_length=2000)
    occurred_at: datetime | None = None  # defaults to now


class TimelineNoteResponse(BaseModel):
    event_id: uuid.UUID
    status: str = "created"


class TimelineVoiceNoteRequest(BaseModel):
    """Create a voice note — audio_url points to uploaded audio."""
    profile_id: uuid.UUID
    audio_url: str
    occurred_at: datetime | None = None


class TimelineVoiceNoteResponse(BaseModel):
    event_id: uuid.UUID
    transcript: str
    status: str = "created"


class TimelineSummaryResponse(BaseModel):
    report_markdown: str
    sections: list[dict[str, Any]] | None = None
    cached: bool = False
