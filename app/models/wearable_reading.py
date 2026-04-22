"""Wearable reading model — Health Connect data."""
import uuid
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class WearableReading(Base):
    __tablename__ = "wearable_reading"

    reading_id = Column(BigInteger, primary_key=True, autoincrement=True)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profile.profile_id"), nullable=False)
    metric = Column(String, nullable=False)  # resting_hr | hrv | sleep_minutes | steps
    value = Column(Numeric, nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    source = Column(String, nullable=False, default="health_connect")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_wearable_profile_metric", "profile_id", "metric", observed_at.desc()),
    )
