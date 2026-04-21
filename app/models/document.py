"""Document model — uploaded medical files."""
import uuid
from datetime import date, datetime
from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Document(Base):
    __tablename__ = "document"

    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("owner.owner_id"), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profile.profile_id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)  # 'camera'|'picker'|'share'|'email_import'
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    s3_key: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    classified_as: Mapped[str | None] = mapped_column(String)
    classification_confidence: Mapped[float | None] = mapped_column(Float)
    classification_model_version: Mapped[str | None] = mapped_column(String)
    document_date: Mapped[date | None] = mapped_column(Date)
    provider_name: Mapped[str | None] = mapped_column(String)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    extractions = relationship("Extraction", back_populates="document", lazy="selectin")
