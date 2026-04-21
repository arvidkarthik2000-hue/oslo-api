"""EmergencyProfile model — one per profile."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class EmergencyProfile(Base):
    __tablename__ = "emergency_profile"

    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profile.profile_id", ondelete="CASCADE"), primary_key=True)
    allergies: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)  # [{substance, severity, reaction}]
    chronic_conditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    current_medications: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    emergency_contacts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)  # [{name, relationship, phone, is_primary}]
    organ_donor: Mapped[bool | None] = mapped_column(Boolean, default=False)
    advance_directives: Mapped[str | None] = mapped_column(String)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    profile = relationship("Profile", back_populates="emergency_profile")
