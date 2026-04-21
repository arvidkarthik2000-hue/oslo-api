"""Auth schemas."""
import uuid
from pydantic import BaseModel, Field


class OTPSendRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+?[1-9]\d{6,14}$", examples=["+919876543210"])


class OTPSendResponse(BaseModel):
    request_id: str
    expires_in: int = 300  # 5 minutes


class OTPVerifyRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+?[1-9]\d{6,14}$")
    request_id: str
    otp: str = Field(..., min_length=4, max_length=6)


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
