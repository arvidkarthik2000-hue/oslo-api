"""Emergency profile schemas."""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class Allergy(BaseModel):
    substance: str
    severity: str | None = None
    reaction: str | None = None


class ChronicCondition(BaseModel):
    condition: str
    diagnosed_year: int | None = None


class EmergencyContact(BaseModel):
    name: str
    relationship: str
    phone: str
    is_primary: bool = False


class EmergencyProfileUpsert(BaseModel):
    allergies: list[Allergy] = Field(default_factory=list)
    chronic_conditions: list[ChronicCondition] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    emergency_contacts: list[EmergencyContact] = Field(default_factory=list)
    organ_donor: bool = False
    advance_directives: str | None = None


class EmergencyProfileResponse(BaseModel):
    profile_id: uuid.UUID
    allergies: list[dict]
    chronic_conditions: list[dict]
    current_medications: list[dict]
    emergency_contacts: list[dict]
    organ_donor: bool | None
    advance_directives: str | None
    last_reviewed_at: datetime | None
    updated_at: datetime

    model_config = {"from_attributes": True}
