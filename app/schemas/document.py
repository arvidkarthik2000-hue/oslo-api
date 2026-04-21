"""Document schemas."""
import uuid
from datetime import date, datetime
from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    mime_type: str
    byte_size: int = Field(..., gt=0)
    profile_id: uuid.UUID
    source: str = Field(..., pattern=r"^(camera|picker|share|email_import)$")


class DocumentUploadResponse(BaseModel):
    upload_url: str
    document_id: uuid.UUID


class DocumentResponse(BaseModel):
    document_id: uuid.UUID
    profile_id: uuid.UUID
    source: str
    mime_type: str
    byte_size: int
    page_count: int
    uploaded_at: datetime
    classified_as: str | None
    classification_confidence: float | None
    document_date: date | None
    provider_name: str | None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
