"""Consent model — DPDP consent receipts."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Consent(Base):
    __tablename__ = "consent"

    consent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("owner.owner_id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)  # 'storage'|'ai_extraction'|'cloud_ai_optin'|'training_corrections'|'teleconsult'|'family_member_data'
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_text_version: Mapped[str] = mapped_column(String, nullable=False)
    consent_text: Mapped[str] = mapped_column(String, nullable=False)  # snapshot of exact text shown
    ip_address: Mapped[str | None] = mapped_column(String)
    user_agent: Mapped[str | None] = mapped_column(String)
    scope: Mapped[dict | None] = mapped_column(JSONB)  # e.g., {"profile_id": "..."}

    # Relationships
    owner = relationship("Owner", back_populates="consents")
