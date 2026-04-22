"""Smart report cache model."""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from app.database import Base


class SmartReportCache(Base):
    __tablename__ = "smart_report_cache"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profile.profile_id"), nullable=False)
    report_type = Column(String, nullable=False)  # smart_report | timeline_summary
    content_markdown = Column(Text, nullable=False)
    source_document_ids = Column(ARRAY(UUID(as_uuid=True)))
    generated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.utcnow() + timedelta(hours=24))
    sections = Column(JSONB)
    model_version = Column(String)

    __table_args__ = (
        Index("idx_smart_report_profile", "profile_id", "report_type", generated_at.desc()),
    )
