"""Profile router — CRUD for family profiles."""
import uuid
import random
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.owner import Owner
from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse, ProfileListResponse
from app.services.audit_service import log_audit_event
from app.dependencies import get_current_owner

router = APIRouter()

# Default avatar colors (accessible teal/blue/purple/green palette)
AVATAR_COLORS = ["#0F6E56", "#2563EB", "#7C3AED", "#DC2626", "#EA580C", "#0891B2", "#4F46E5", "#059669"]


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """List all profiles for the current owner."""
    result = await db.execute(
        select(Profile)
        .where(Profile.owner_id == owner.owner_id, Profile.deleted_at.is_(None))
        .order_by(Profile.created_at)
    )
    profiles = result.scalars().all()
    return ProfileListResponse(profiles=[ProfileResponse.model_validate(p) for p in profiles])


@router.post("", response_model=ProfileResponse, status_code=201)
async def create_profile(
    body: ProfileCreate,
    request: Request,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Create a new profile. Enforces max 1 for free, 5 for paid."""
    # Count existing profiles
    count_result = await db.execute(
        select(func.count()).select_from(Profile)
        .where(Profile.owner_id == owner.owner_id, Profile.deleted_at.is_(None))
    )
    profile_count = count_result.scalar()
    
    max_profiles = 1 if owner.subscription_tier == "free" else 5
    if profile_count >= max_profiles:
        tier_msg = "Upgrade to Family plan for up to 5 profiles" if owner.subscription_tier == "free" else "Maximum 5 profiles reached"
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=tier_msg)
    
    # Enforce one 'self' profile per owner
    if body.relationship == "self":
        existing_self = await db.execute(
            select(Profile).where(
                Profile.owner_id == owner.owner_id,
                Profile.relationship_type == "self",
                Profile.deleted_at.is_(None),
            )
        )
        if existing_self.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A 'self' profile already exists")
    
    profile = Profile(
        owner_id=owner.owner_id,
        name=body.name,
        relationship_type=body.relationship,
        dob=body.dob,
        sex=body.sex,
        blood_group=body.blood_group,
        pregnancy_status=body.pregnancy_status,
        avatar_color=body.avatar_color or random.choice(AVATAR_COLORS),
    )
    db.add(profile)
    await db.flush()
    
    await log_audit_event(
        db, action="profile.create", actor_type="user",
        owner_id=owner.owner_id, profile_id=profile.profile_id,
        resource_type="profile", resource_id=profile.profile_id,
        ip_address=request.client.host if request.client else None,
    )
    
    return ProfileResponse.model_validate(profile)


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: uuid.UUID,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get a single profile."""
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
    return ProfileResponse.model_validate(profile)


@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    body: ProfileUpdate,
    request: Request,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Update profile fields."""
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
    
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    await log_audit_event(
        db, action="profile.update", actor_type="user",
        owner_id=owner.owner_id, profile_id=profile.profile_id,
        resource_type="profile", resource_id=profile.profile_id,
        metadata={"fields_updated": list(update_data.keys())},
        ip_address=request.client.host if request.client else None,
    )
    
    return ProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: uuid.UUID,
    request: Request,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a profile. Documents kept 30 days."""
    from datetime import datetime, timezone
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
    
    if profile.relationship_type == "self":
        raise HTTPException(status_code=400, detail="Cannot delete your own profile. Use account deletion instead.")
    
    profile.deleted_at = datetime.now(timezone.utc)
    
    await log_audit_event(
        db, action="profile.delete", actor_type="user",
        owner_id=owner.owner_id, profile_id=profile.profile_id,
        resource_type="profile", resource_id=profile.profile_id,
        ip_address=request.client.host if request.client else None,
    )
    return None
