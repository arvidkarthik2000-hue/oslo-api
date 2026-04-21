"""Profile schemas."""
import uuid
from datetime import date, datetime
from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    relationship: str = Field(..., pattern=r"^(self|spouse|child|parent|other)$")
    dob: date | None = None
    sex: str | None = Field(None, pattern=r"^(M|F|other)$")
    blood_group: str | None = None
    pregnancy_status: str | None = Field(None, pattern=r"^(pregnant|nursing)$")
    avatar_color: str | None = None


class ProfileUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    dob: date | None = None
    sex: str | None = Field(None, pattern=r"^(M|F|other)$")
    blood_group: str | None = None
    pregnancy_status: str | None = None
    avatar_color: str | None = None


class ProfileResponse(BaseModel):
    profile_id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    relationship: str
    dob: date | None
    sex: str | None
    blood_group: str | None
    pregnancy_status: str | None
    avatar_color: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileListResponse(BaseModel):
    profiles: list[ProfileResponse]
