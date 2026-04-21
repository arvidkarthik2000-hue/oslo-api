"""AuditEvent model — append-only audit log."""
import uuid
from datetime import datetime
from sqlalchemy import String, BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_event"

    audit_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor_type: Mapped[str] = mapped_column(String, nullable=False)  # 'user'|'system'|'rmp'|'admin'
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resource_type: Mapped[str | None] = mapped_column(String)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    ip_address: Mapped[str | None] = mapped_column(String)
    user_agent: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
