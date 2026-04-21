"""Consents router — DPDP consent management."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.owner import Owner
from app.models.consent import Consent
from app.schemas.consent import ConsentCreate, ConsentResponse, ConsentListResponse
from app.services.audit_service import log_audit_event
from app.dependencies import get_current_owner

router = APIRouter()

# Consent text templates — versioned, snapshot stored with each consent
CONSENT_TEXTS = {
    "storage": {
        "v1": "OSLO stores your medical documents securely in encrypted storage (AWS Mumbai, India). Your data never leaves India. You can export or delete your data at any time.",
    },
    "ai_extraction": {
        "v1": "OSLO uses AI to extract structured information from your medical documents (lab values, medications, etc.). This processing happens on secured servers in India. No human reviews your documents unless you explicitly request it.",
    },
    "cloud_ai_optin": {
        "v1": "You optionally allow OSLO to use cloud AI services (such as Claude by Anthropic) for enhanced understanding of complex documents. This sends document content to external servers. You can enable or disable this per document.",
    },
    "training_corrections": {
        "v1": "When you correct an AI extraction error, your correction may be used to improve OSLO's AI models. All training data is anonymized — your name, phone, and identifying details are removed before use.",
    },
    "teleconsult": {
        "v1": "OSLO facilitates teleconsultations with registered medical practitioners. Your health records may be shared with the consulting doctor for the duration of the consultation. Records are retained for 3 years as required by Indian medical regulations.",
    },
    "family_member_data": {
        "v1": "As the account holder, you are the data fiduciary for family members whose profiles you create. You are responsible for obtaining their consent (or acting as guardian for minors). Family member data is subject to the same privacy protections as your own.",
    },
}


@router.get("", response_model=ConsentListResponse)
async def list_consents(
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """List all consents for the current owner."""
    result = await db.execute(
        select(Consent)
        .where(Consent.owner_id == owner.owner_id)
        .order_by(Consent.granted_at.desc())
    )
    consents = result.scalars().all()
    return ConsentListResponse(consents=[ConsentResponse.model_validate(c) for c in consents])


@router.post("", response_model=ConsentResponse, status_code=201)
async def create_consent(
    body: ConsentCreate,
    request: Request,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Record a consent grant or denial."""
    # Get the consent text for the given version
    purpose_texts = CONSENT_TEXTS.get(body.purpose, {})
    consent_text = purpose_texts.get(body.text_version, f"Consent for {body.purpose} (version {body.text_version})")
    
    consent = Consent(
        owner_id=owner.owner_id,
        purpose=body.purpose,
        granted=body.granted,
        consent_text_version=body.text_version,
        consent_text=consent_text,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(consent)
    await db.flush()
    
    await log_audit_event(
        db, action=f"consent.{'grant' if body.granted else 'deny'}",
        actor_type="user", owner_id=owner.owner_id,
        resource_type="consent", resource_id=consent.consent_id,
        metadata={"purpose": body.purpose, "granted": body.granted},
        ip_address=request.client.host if request.client else None,
    )
    
    return ConsentResponse.model_validate(consent)


@router.post("/{consent_id}/revoke", status_code=200)
async def revoke_consent(
    consent_id: uuid.UUID,
    request: Request,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a previously granted consent."""
    result = await db.execute(
        select(Consent).where(
            Consent.consent_id == consent_id,
            Consent.owner_id == owner.owner_id,
            Consent.revoked_at.is_(None),
        )
    )
    consent = result.scalar_one_or_none()
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found or already revoked")
    
    consent.revoked_at = datetime.now(timezone.utc)
    
    await log_audit_event(
        db, action="consent.revoke", actor_type="user",
        owner_id=owner.owner_id,
        resource_type="consent", resource_id=consent.consent_id,
        metadata={"purpose": consent.purpose},
        ip_address=request.client.host if request.client else None,
    )
    
    # TODO: Trigger downstream effects (e.g., revoking ai_extraction stops future extractions)
    
    return {"status": "revoked", "purpose": consent.purpose}
