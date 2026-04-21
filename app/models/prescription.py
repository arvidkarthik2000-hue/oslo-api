"""Prescription model."""
import uuid
from datetime import date, datetime
from sqlalchemy import String, Boolean, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Prescription(Base):
    __tablename__ = "prescription"

    prescription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profile.profile_id"), nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("document.document_id"))
    prescribed_by: Mapped[str | None] = mapped_column(String)
    prescribing_rmp_nmc: Mapped[str | None] = mapped_column(String)
    prescribed_at: Mapped[date] = mapped_column(Date, nullable=False)
    items: Mapped[dict] = mapped_column(JSONB, nullable=False)  # [{drug, dose, frequency, duration_days, instructions}]
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    started_at: Mapped[date | None] = mapped_column(Date)
    ended_at: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String, nullable=False)  # 'extracted'|'manual'|'teleconsult'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
