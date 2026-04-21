"""LabValue model — denormalized lab results for fast trend queries."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Numeric, BigInteger, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import uuid


class LabValue(Base):
    __tablename__ = "lab_value"

    lab_value_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profile.profile_id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("document.document_id", ondelete="CASCADE"), nullable=False)
    extraction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("extraction.extraction_id", ondelete="CASCADE"), nullable=False)
    test_name: Mapped[str] = mapped_column(String, nullable=False)
    loinc_code: Mapped[str | None] = mapped_column(String)
    value_num: Mapped[Decimal | None] = mapped_column(Numeric)
    value_text: Mapped[str | None] = mapped_column(String)
    unit: Mapped[str | None] = mapped_column(String)
    ref_low: Mapped[Decimal | None] = mapped_column(Numeric)
    ref_high: Mapped[Decimal | None] = mapped_column(Numeric)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    flag: Mapped[str | None] = mapped_column(String)  # 'ok'|'watch'|'flag'|'critical'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
