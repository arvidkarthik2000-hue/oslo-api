"""Auth schemas."""
import uuid
from pydantic import BaseModel, Field


class OTPSendRequest(BaseModel):
    phone_number: str = Field(..., description="E.164 format, e.g. +919876543210")


class OTPSendResponse(BaseModel):
    request_id: str
    expires_in: int = 300


class OTPVerifyRequest(BaseModel):
    phone_number: str
    otp: str


class OTPVerifyResponse(BaseModel):
    access_token: str
    refresh_token: str
    is_new_user: bool
    consent_required: bool
    owner_id: uuid.UUID


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str


class DevCreateResponse(BaseModel):
    """Response for POC dev-create endpoint."""
    access_token: str
    refresh_token: str
    owner_id: uuid.UUID
    profile_id: uuid.UUID
    is_new: bool
