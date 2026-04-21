"""TimelineEvent model — materialized timeline entries."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TimelineEvent(Base):
    __tablename__ = "timeline_event"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profile.profile_id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)  # 'lab'|'prescription'|'visit'|'discharge'|'vaccination'|'imaging'|'note'|'voice_note'|'teleconsult'
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_ref_type: Mapped[str | None] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String)
    provider: Mapped[str | None] = mapped_column(String)
    flags: Mapped[dict | None] = mapped_column(JSONB)  # [{text: 'Hb 10.2 ↓', severity: 'flag'}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
