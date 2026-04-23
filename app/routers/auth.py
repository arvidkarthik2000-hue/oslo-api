"""Auth router — OTP send/verify, JWT refresh, dev-create, logout, account delete."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db
from app.models.owner import Owner
from app.models.profile import Profile
from app.schemas.auth import (
    OTPSendRequest, OTPSendResponse,
    OTPVerifyRequest, OTPVerifyResponse,
    RefreshRequest, RefreshResponse,
    DevCreateResponse,
)
from app.services.otp_service import send_otp, verify_otp
from app.services.jwt_service import create_access_token, create_refresh_token, verify_token
from app.services.audit_service import log_audit_event
from app.dependencies import get_current_owner, DEMO_OWNER_ID
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/dev-create", response_model=DevCreateResponse)
async def dev_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create or return the demo owner + profile for POC dev mode.

    Only available when ENVIRONMENT=development.
    """
    if settings.environment != "development":
        raise HTTPException(status_code=403, detail="Dev-only endpoint")

    # Find or create demo owner
    result = await db.execute(
        select(Owner).where(Owner.owner_id == DEMO_OWNER_ID)
    )
    owner = result.scalar_one_or_none()
    is_new = owner is None

    if is_new:
        owner = Owner(
            owner_id=DEMO_OWNER_ID,
            phone_number="9199999999",
            phone_verified_at=datetime.now(timezone.utc),
        )
        db.add(owner)
        await db.flush()

    # Find or create demo profile
    profile_result = await db.execute(
        select(Profile).where(
            Profile.owner_id == DEMO_OWNER_ID,
            Profile.relationship == "self",
        )
    )
    profile = profile_result.scalar_one_or_none()

    if profile is None:
        from datetime import date
        profile = Profile(
            owner_id=DEMO_OWNER_ID,
            name="Demo User",
            relationship="self",
            dob=date(1978, 3, 15),
            sex="M",
            blood_group="O+",
        )
        db.add(profile)
        await db.flush()

    # Seed demo data on first creation
    if is_new:
        from app.services.demo_seed import seed_demo_data
        await seed_demo_data(db, owner.owner_id, profile.profile_id)

    access_token = create_access_token(owner.owner_id)
    refresh_token = create_refresh_token(owner.owner_id)

    await log_audit_event(
        db, action="auth.dev_create", actor_type="system",
        owner_id=owner.owner_id, profile_id=profile.profile_id,
        ip_address=request.client.host if request.client else None,
    )

    return DevCreateResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        owner_id=owner.owner_id,
        profile_id=profile.profile_id,
        is_new=is_new,
    )


@router.post("/otp/send", response_model=OTPSendResponse)
async def otp_send(body: OTPSendRequest, request: Request):
    """Send OTP to phone number."""
    result = await send_otp(body.phone_number)
    return OTPSendResponse(
        request_id=result.get("request_id", "unknown"),
        expires_in=300,
    )


@router.post("/otp/verify", response_model=OTPVerifyResponse)
async def otp_verify(
    body: OTPVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Verify OTP and issue tokens. Creates owner if new."""
    is_valid = await verify_otp(body.phone_number, body.otp)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")

    phone = body.phone_number.lstrip("+")
    if not phone.startswith("91") and len(phone) == 10:
        phone = f"91{phone}"

    result = await db.execute(select(Owner).where(Owner.phone_number == phone))
    owner = result.scalar_one_or_none()
    is_new = owner is None

    if is_new:
        owner = Owner(
            phone_number=phone,
            phone_verified_at=datetime.now(timezone.utc),
        )
        db.add(owner)
        await db.flush()
        await log_audit_event(
            db, action="auth.signup", actor_type="user",
            owner_id=owner.owner_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    else:
        owner.phone_verified_at = datetime.now(timezone.utc)
        await log_audit_event(
            db, action="auth.login", actor_type="user",
            owner_id=owner.owner_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    from app.models.consent import Consent
    consent_result = await db.execute(
        select(Consent).where(Consent.owner_id == owner.owner_id, Consent.purpose == "storage")
    )
    consent_required = consent_result.scalar_one_or_none() is None

    access_token = create_access_token(owner.owner_id)
    refresh_token = create_refresh_token(owner.owner_id)

    return OTPVerifyResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        is_new_user=is_new,
        consent_required=consent_required,
        owner_id=owner.owner_id,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(body: RefreshRequest):
    """Exchange a refresh token for a new access token."""
    try:
        payload = verify_token(body.refresh_token, expected_type="refresh")
        owner_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    new_access = create_access_token(owner_id)
    return RefreshResponse(access_token=new_access)


@router.post("/logout", status_code=204)
async def logout(
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Logout — currently a no-op server-side (JWT is stateless). Audit logged."""
    await log_audit_event(
        db, action="auth.logout", actor_type="user",
        owner_id=owner.owner_id,
        ip_address=request.client.host if request and request.client else None,
    )
    return None


@router.delete("/account", status_code=204)
async def delete_account(
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Delete account — DPDP right-to-delete. 30-day grace period."""
    owner.deleted_at = datetime.now(timezone.utc)
    await log_audit_event(
        db, action="auth.account_delete_requested", actor_type="user",
        owner_id=owner.owner_id,
        metadata={"grace_period_days": 30},
        ip_address=request.client.host if request and request.client else None,
    )
    return None
