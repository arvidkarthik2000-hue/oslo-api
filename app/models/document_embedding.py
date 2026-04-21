"""DocumentEmbedding model — vector embeddings for RAG."""
import uuid
from datetime import datetime
from sqlalchemy import String, BigInteger, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.database import Base


class DocumentEmbedding(Base):
    __tablename__ = "document_embedding"

    embedding_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("document.document_id", ondelete="CASCADE"), nullable=False)
    chunk_type: Mapped[str] = mapped_column(String, nullable=False)  # 'ocr'|'extracted'|'explanation'
    chunk_text: Mapped[str] = mapped_column(String, nullable=False)
    embedding = mapped_column(Vector(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
