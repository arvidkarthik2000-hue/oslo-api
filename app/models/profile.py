"""Profile model — family member profiles under an owner."""
import uuid
from datetime import date, datetime
from sqlalchemy import String, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship
from app.database import Base


class Profile(Base):
    __tablename__ = "profile"

    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("owner.owner_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    relationship: Mapped[str] = mapped_column(String, nullable=False)  # 'self'|'spouse'|'child'|'parent'|'other'
    dob: Mapped[date | None] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String)  # 'M'|'F'|'other'
    blood_group: Mapped[str | None] = mapped_column(String)
    pregnancy_status: Mapped[str | None] = mapped_column(String)  # NULL|'pregnant'|'nursing'
    avatar_color: Mapped[str | None] = mapped_column(String)
    abha_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    owner = sa_relationship("Owner", back_populates="profiles")
    emergency_profile = sa_relationship("EmergencyProfile", back_populates="profile", uselist=False)
