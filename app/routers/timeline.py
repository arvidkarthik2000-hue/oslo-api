"""Timeline router — list events, create notes, voice notes, AI summary."""
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.owner import Owner
from app.models.timeline_event import TimelineEvent
from app.models.lab_value import LabValue
from app.models.prescription import Prescription
from app.models.smart_report_cache import SmartReportCache
from app.dependencies import get_current_owner
from app.services import ai_service
from app.services.audit_service import log_audit_event
from app.schemas.timeline import (
    TimelineListResponse, TimelineEventItem,
    TimelineNoteRequest, TimelineNoteResponse,
    TimelineVoiceNoteRequest, TimelineVoiceNoteResponse,
    TimelineSummaryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=TimelineListResponse)
async def list_timeline(
    profile_id: uuid.UUID | None = None,
    event_type: str | None = None,
    search: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """List timeline events with filters. Supports type filter, date range, keyword search."""
    q = select(TimelineEvent).where(
        TimelineEvent.owner_id == owner.owner_id,
    ).order_by(TimelineEvent.occurred_at.desc())

    if profile_id:
        q = q.where(TimelineEvent.profile_id == profile_id)
    if event_type:
        q = q.where(TimelineEvent.event_type == event_type)
    if start_date:
        q = q.where(TimelineEvent.occurred_at >= start_date)
    if end_date:
        q = q.where(TimelineEvent.occurred_at <= end_date)
    if search:
        pattern = f"%{search}%"
        q = q.where(
            TimelineEvent.title.ilike(pattern)
            | TimelineEvent.subtitle.ilike(pattern)
            | TimelineEvent.provider.ilike(pattern)
        )

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    events = result.scalars().all()

    return TimelineListResponse(
        events=[TimelineEventItem.model_validate(e) for e in events],
        total=total,
    )


@router.post("/note", response_model=TimelineNoteResponse, status_code=201)
async def create_note(
    body: TimelineNoteRequest,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual text note on the timeline."""
    event = TimelineEvent(
        owner_id=owner.owner_id,
        profile_id=body.profile_id,
        event_type="note",
        occurred_at=body.occurred_at or datetime.now(timezone.utc),
        title="Note",
        subtitle=body.text[:120],  # preview
        flags={"full_text": body.text},
    )
    db.add(event)
    await db.flush()

    await log_audit_event(
        db, action="timeline.note.create", actor_type="user",
        owner_id=owner.owner_id, profile_id=body.profile_id,
        resource_type="timeline_event", resource_id=event.event_id,
    )

    return TimelineNoteResponse(event_id=event.event_id)


@router.post("/voice-note", response_model=TimelineVoiceNoteResponse, status_code=201)
async def create_voice_note(
    body: TimelineVoiceNoteRequest,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Create a voice note — transcribes audio then saves to timeline."""
    # Transcribe
    try:
        owner_hash = hashlib.sha256(str(owner.owner_id).encode()).hexdigest()
        transcribe_result = await ai_service.transcribe(
            audio_url=body.audio_url,
            language="en",
            owner_id_hash=owner_hash,
        )
        transcript = transcribe_result.get("transcript", "")
    except ai_service.AIServiceError as e:
        logger.error("Transcription failed: %s", e)
        transcript = "[Transcription failed — audio saved]"

    event = TimelineEvent(
        owner_id=owner.owner_id,
        profile_id=body.profile_id,
        event_type="voice_note",
        occurred_at=body.occurred_at or datetime.now(timezone.utc),
        title="Voice Note",
        subtitle=transcript[:120] if transcript else "Voice recording",
        flags={
            "full_text": transcript,
            "audio_url": body.audio_url,
            "duration_sec": transcribe_result.get("duration_sec") if transcript and not transcript.startswith("[") else None,
        },
    )
    db.add(event)
    await db.flush()

    await log_audit_event(
        db, action="timeline.voice_note.create", actor_type="user",
        owner_id=owner.owner_id, profile_id=body.profile_id,
        resource_type="timeline_event", resource_id=event.event_id,
    )

    return TimelineVoiceNoteResponse(
        event_id=event.event_id,
        transcript=transcript,
    )


@router.post("/summarize", response_model=TimelineSummaryResponse)
async def timeline_summary(
    profile_id: uuid.UUID,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI timeline summary. Uses cache if available (24h TTL)."""
    # Check cache
    cache_q = select(SmartReportCache).where(
        SmartReportCache.owner_id == owner.owner_id,
        SmartReportCache.profile_id == profile_id,
        SmartReportCache.report_type == "timeline_summary",
        SmartReportCache.expires_at > datetime.now(timezone.utc),
    ).order_by(SmartReportCache.generated_at.desc()).limit(1)

    cached = (await db.execute(cache_q)).scalar_one_or_none()
    if cached:
        return TimelineSummaryResponse(
            report_markdown=cached.content_markdown,
            sections=cached.sections,
            cached=True,
        )

    # Gather context data
    lab_q = select(LabValue).where(
        LabValue.owner_id == owner.owner_id,
        LabValue.profile_id == profile_id,
    ).order_by(LabValue.observed_at.desc()).limit(200)
    lab_values = (await db.execute(lab_q)).scalars().all()

    rx_q = select(Prescription).where(
        Prescription.owner_id == owner.owner_id,
        Prescription.profile_id == profile_id,
    ).order_by(Prescription.prescribed_at.desc()).limit(50)
    prescriptions = (await db.execute(rx_q)).scalars().all()

    notes_q = select(TimelineEvent).where(
        TimelineEvent.owner_id == owner.owner_id,
        TimelineEvent.profile_id == profile_id,
        TimelineEvent.event_type.in_(["note", "voice_note"]),
    ).order_by(TimelineEvent.occurred_at.desc()).limit(50)
    notes = (await db.execute(notes_q)).scalars().all()

    context_data = {
        "lab_values": [
            {
                "test": lv.test_name,
                "value": float(lv.value_num) if lv.value_num else None,
                "unit": lv.unit,
                "observed_at": lv.observed_at.isoformat() if lv.observed_at else None,
                "loinc": lv.loinc_code,
                "flag": lv.flag,
            }
            for lv in lab_values
        ],
        "prescriptions": [
            {
                "items": rx.items,
                "prescribed_by": rx.prescribed_by,
                "prescribed_at": rx.prescribed_at.isoformat() if rx.prescribed_at else None,
                "active": rx.active,
            }
            for rx in prescriptions
        ],
        "notes": [
            {
                "text": (n.flags or {}).get("full_text", n.subtitle or ""),
                "occurred_at": n.occurred_at.isoformat() if n.occurred_at else None,
            }
            for n in notes
        ],
    }

    try:
        owner_hash = hashlib.sha256(str(owner.owner_id).encode()).hexdigest()
        result = await ai_service.summarize(
            owner_id_hash=owner_hash,
            profile_id=str(profile_id),
            report_type="timeline_summary",
            patient_profile={},  # enriched later when profile data is available
            context_data=context_data,
        )

        # Cache the result
        cache_entry = SmartReportCache(
            owner_id=owner.owner_id,
            profile_id=profile_id,
            report_type="timeline_summary",
            content_markdown=result.get("report_markdown", ""),
            sections=result.get("sections"),
            model_version=result.get("model_version"),
        )
        db.add(cache_entry)

        return TimelineSummaryResponse(
            report_markdown=result.get("report_markdown", ""),
            sections=result.get("sections"),
            cached=False,
        )
    except ai_service.AIServiceError:
        raise HTTPException(
            status_code=503,
            detail="Timeline summary generation unavailable. Please try again.",
        )
