"""Teleconsult models — sessions and messages."""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TeleconsultSession(Base):
    __tablename__ = "teleconsult_session"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("owner.owner_id"), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profile.profile_id"), nullable=False)
    rmp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rmp_nmc: Mapped[str] = mapped_column(String, nullable=False)
    rmp_name: Mapped[str] = mapped_column(String, nullable=False)
    rmp_qualification: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="awaiting_response")
    patient_consent_recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    patient_consent_text: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    messages = relationship("TeleconsultMessage", back_populates="session", lazy="selectin")


class TeleconsultMessage(Base):
    __tablename__ = "teleconsult_message"

    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teleconsult_session.session_id", ondelete="CASCADE"), nullable=False)
    sender: Mapped[str] = mapped_column(String, nullable=False)  # 'patient'|'rmp'
    content: Mapped[str] = mapped_column(String, nullable=False)
    attachments: Mapped[dict | None] = mapped_column(JSONB)
    emergency_trigger_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("TeleconsultSession", back_populates="messages")
