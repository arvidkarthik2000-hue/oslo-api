"""Extraction model — structured AI extraction results."""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Extraction(Base):
    __tablename__ = "extraction"

    extraction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("document.document_id", ondelete="CASCADE"), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False, default="v1")
    json_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation_flags: Mapped[dict | None] = mapped_column(JSONB)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    document = relationship("Document", back_populates="extractions")
