"""ShareLink model — doctor-shareable summaries."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ShareLink(Base):
    __tablename__ = "share_link"

    share_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profile.profile_id"), nullable=False)
    created_by_owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("owner.owner_id"), nullable=False)
    doctor_name: Mapped[str | None] = mapped_column(String)
    doctor_nmc: Mapped[str | None] = mapped_column(String)
    scope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    jwt_token_hash: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accessed_at: Mapped[list | None] = mapped_column(ARRAY(DateTime(timezone=True)))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
