"""Consent schemas."""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ConsentCreate(BaseModel):
    purpose: str = Field(..., pattern=r"^(storage|ai_extraction|cloud_ai_optin|training_corrections|teleconsult|family_member_data)$")
    granted: bool
    text_version: str = Field(..., min_length=1)


class ConsentResponse(BaseModel):
    consent_id: uuid.UUID
    purpose: str
    granted: bool
    granted_at: datetime
    revoked_at: datetime | None
    consent_text_version: str

    model_config = {"from_attributes": True}


class ConsentListResponse(BaseModel):
    consents: list[ConsentResponse]
