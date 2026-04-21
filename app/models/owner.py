"""Owner model — the registered account holder."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Owner(Base):
    __tablename__ = "owner"

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    subscription_tier: Mapped[str] = mapped_column(String, nullable=False, default="free")
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    razorpay_customer_id: Mapped[str | None] = mapped_column(String)
    kms_key_arn: Mapped[str | None] = mapped_column(String)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    profiles = relationship("Profile", back_populates="owner", lazy="selectin")
    consents = relationship("Consent", back_populates="owner", lazy="selectin")
