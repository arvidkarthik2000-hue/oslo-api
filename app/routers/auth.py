"""Auth router — OTP send/verify, JWT refresh, logout, account delete."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db
from app.models.owner import Owner
from app.models.consent import Consent
from app.schemas.auth import (
    OTPSendRequest, OTPSendResponse,
    OTPVerifyRequest, OTPVerifyResponse,
    RefreshRequest, RefreshResponse,
)
from app.services.otp_service import send_otp, verify_otp
from app.services.jwt_service import create_access_token, create_refresh_token, verify_token
from app.services.audit_service import log_audit_event
from app.dependencies import get_current_owner

router = APIRouter()


@router.post("/otp/send", response_model=OTPSendResponse)
async def otp_send(body: OTPSendRequest, request: Request):
    """Send OTP to phone number."""
    # TODO: Rate limit check — 5/hour per phone, 10/day per IP
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
    
    # Normalize phone
    phone = body.phone_number.lstrip("+")
    if not phone.startswith("91") and len(phone) == 10:
        phone = f"91{phone}"
    
    # Find or create owner
    result = await db.execute(select(Owner).where(Owner.phone_number == phone))
    owner = result.scalar_one_or_none()
    is_new = owner is None
    
    if is_new:
        owner = Owner(
            phone_number=phone,
            phone_verified_at=datetime.now(timezone.utc),
        )
        db.add(owner)
        await db.flush()  # get owner_id
        
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
    
    # Check if consents exist
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
    # TODO: Schedule hard delete job after 30 days (KMS key destruction)
    return None
