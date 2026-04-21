"""Emergency profile router."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.owner import Owner
from app.models.profile import Profile
from app.models.emergency_profile import EmergencyProfile
from app.schemas.emergency import EmergencyProfileUpsert, EmergencyProfileResponse
from app.services.audit_service import log_audit_event
from app.dependencies import get_current_owner

router = APIRouter()


async def _get_profile(db: AsyncSession, profile_id: uuid.UUID, owner: Owner) -> Profile:
    result = await db.execute(
        select(Profile).where(
            Profile.profile_id == profile_id,
            Profile.owner_id == owner.owner_id,
            Profile.deleted_at.is_(None),
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get("/{profile_id}/emergency", response_model=EmergencyProfileResponse)
async def get_emergency_profile(
    profile_id: uuid.UUID,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get emergency profile for a family member."""
    await _get_profile(db, profile_id, owner)
    result = await db.execute(
        select(EmergencyProfile).where(EmergencyProfile.profile_id == profile_id)
    )
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Emergency profile not set up yet")
    return EmergencyProfileResponse.model_validate(ep)


@router.put("/{profile_id}/emergency", response_model=EmergencyProfileResponse)
async def upsert_emergency_profile(
    profile_id: uuid.UUID,
    body: EmergencyProfileUpsert,
    request: Request,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Create or update emergency profile."""
    profile = await _get_profile(db, profile_id, owner)
    
    result = await db.execute(
        select(EmergencyProfile).where(EmergencyProfile.profile_id == profile_id)
    )
    ep = result.scalar_one_or_none()
    
    if ep is None:
        ep = EmergencyProfile(
            profile_id=profile_id,
            allergies=[a.model_dump() for a in body.allergies],
            chronic_conditions=[c.model_dump() for c in body.chronic_conditions],
            current_medications=body.current_medications,
            emergency_contacts=[e.model_dump() for e in body.emergency_contacts],
            organ_donor=body.organ_donor,
            advance_directives=body.advance_directives,
            last_reviewed_at=datetime.now(timezone.utc),
        )
        db.add(ep)
    else:
        ep.allergies = [a.model_dump() for a in body.allergies]
        ep.chronic_conditions = [c.model_dump() for c in body.chronic_conditions]
        ep.current_medications = body.current_medications
        ep.emergency_contacts = [e.model_dump() for e in body.emergency_contacts]
        ep.organ_donor = body.organ_donor
        ep.advance_directives = body.advance_directives
        ep.last_reviewed_at = datetime.now(timezone.utc)
    
    await db.flush()
    
    await log_audit_event(
        db, action="emergency.upsert", actor_type="user",
        owner_id=owner.owner_id, profile_id=profile_id,
        resource_type="emergency_profile", resource_id=profile_id,
        ip_address=request.client.host if request.client else None,
    )
    
    return EmergencyProfileResponse.model_validate(ep)
