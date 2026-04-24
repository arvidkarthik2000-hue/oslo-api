"""Document schemas — upload, list, detail, extraction."""
import uuid
from datetime import datetime, date
from pydantic import BaseModel, Field
from typing import Any


# --- Upload ---
class DocumentUploadRequest(BaseModel):
    profile_id: uuid.UUID
    source: str = Field(default="picker", description="camera|picker|share|email_import")
    mime_type: str = Field(default="application/pdf")
    byte_size: int = Field(default=0)
    page_count: int = Field(default=1)
    file_name: str = Field(default="document.pdf")


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    upload_url: str | None = None  # Supabase storage URL for POC
    status: str = "pending"


# --- Finalize (trigger AI pipeline) ---
class DocumentFinalizeRequest(BaseModel):
    """Called after file is uploaded to storage."""
    s3_key: str = Field(default="", description="Storage key/path where file was uploaded")
    sha256: str = Field(default="", description="File hash for dedup")
    image_urls: list[str] = Field(default=[], description="Public URLs for AI processing")


class DocumentFinalizeResponse(BaseModel):
    document_id: uuid.UUID
    classified_as: str | None
    classification_confidence: float | None
    extraction_id: uuid.UUID | None
    processing_status: str


# --- List ---
class DocumentListItem(BaseModel):
    document_id: uuid.UUID
    profile_id: uuid.UUID
    source: str
    mime_type: str
    classified_as: str | None
    document_date: date | None
    provider_name: str | None
    uploaded_at: datetime
    processing_status: str | None = "complete"

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int


# --- Detail ---
class ExtractionDetail(BaseModel):
    extraction_id: uuid.UUID
    model_version: str
    schema_version: str
    json_payload: dict
    validation_flags: dict | None
    user_corrected: bool
    is_current: bool
    created_at: datetime
    explanation_markdown: str | None = None

    model_config = {"from_attributes": True}


class DocumentDetail(BaseModel):
    document_id: uuid.UUID
    profile_id: uuid.UUID
    source: str
    mime_type: str
    byte_size: int
    page_count: int
    s3_key: str
    uploaded_at: datetime
    classified_as: str | None
    classification_confidence: float | None
    document_date: date | None
    provider_name: str | None
    processing_status: str | None
    extractions: list[ExtractionDetail] = []

    model_config = {"from_attributes": True}


# --- Extraction correction ---
class ExtractionCorrectionRequest(BaseModel):
    corrected_payload: dict = Field(..., description="Full corrected extraction JSON")


# --- Explain ---
class ExplainResponse(BaseModel):
    explanation_markdown: str
    critical_flags: list[str] = []
    urgency: str = "routine"
