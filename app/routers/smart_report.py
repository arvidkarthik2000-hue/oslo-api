"""Smart Report router — AI-synthesized health summary."""
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.owner import Owner
from app.models.profile import Profile
from app.models.lab_value import LabValue
from app.models.prescription import Prescription
from app.models.smart_report_cache import SmartReportCache
from app.dependencies import get_current_owner
from app.services import ai_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{profile_id}")
async def get_smart_report(
    profile_id: uuid.UUID,
    force_refresh: bool = Query(default=False),
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Generate or return cached Smart Report. 24h cache TTL."""
    # Check cache unless force refresh
    if not force_refresh:
        cache_q = select(SmartReportCache).where(
            SmartReportCache.owner_id == owner.owner_id,
            SmartReportCache.profile_id == profile_id,
            SmartReportCache.report_type == "smart_report",
            SmartReportCache.expires_at > datetime.now(timezone.utc),
        ).order_by(SmartReportCache.generated_at.desc()).limit(1)

        cached = (await db.execute(cache_q)).scalar_one_or_none()
        if cached:
            return {
                "report_markdown": cached.content_markdown,
                "sections": cached.sections,
                "generated_at": cached.generated_at.isoformat(),
                "cached": True,
            }

    # Gather patient profile
    profile = (await db.execute(
        select(Profile).where(Profile.profile_id == profile_id)
    )).scalar_one_or_none()

    patient_profile = {}
    if profile:
        patient_profile = {
            "name": profile.display_name,
            "sex": profile.sex,
            "blood_group": profile.blood_group,
        }
        if profile.date_of_birth:
            from datetime import date
            age = (date.today() - profile.date_of_birth).days // 365
            patient_profile["age"] = age

    # Gather lab values (last 200)
    lab_q = select(LabValue).where(
        LabValue.owner_id == owner.owner_id,
        LabValue.profile_id == profile_id,
    ).order_by(LabValue.observed_at.desc()).limit(200)
    lab_values = (await db.execute(lab_q)).scalars().all()

    # Gather prescriptions
    rx_q = select(Prescription).where(
        Prescription.owner_id == owner.owner_id,
        Prescription.profile_id == profile_id,
    ).order_by(Prescription.prescribed_at.desc()).limit(50)
    prescriptions = (await db.execute(rx_q)).scalars().all()

    context_data = {
        "lab_values": [
            {
                "test": lv.test_name,
                "value": float(lv.value_num) if lv.value_num else None,
                "unit": lv.unit,
                "observed_at": lv.observed_at.isoformat() if lv.observed_at else None,
                "loinc": lv.loinc_code,
                "flag": lv.flag,
            }
            for lv in lab_values
        ],
        "prescriptions": [
            {
                "items": rx.items,
                "prescribed_by": rx.prescribed_by,
                "prescribed_at": rx.prescribed_at.isoformat() if rx.prescribed_at else None,
                "active": rx.active,
            }
            for rx in prescriptions
        ],
    }

    try:
        owner_hash = hashlib.sha256(str(owner.owner_id).encode()).hexdigest()
        result = await ai_service.summarize(
            owner_id_hash=owner_hash,
            profile_id=str(profile_id),
            report_type="smart_report",
            patient_profile=patient_profile,
            context_data=context_data,
        )

        # Cache
        cache_entry = SmartReportCache(
            owner_id=owner.owner_id,
            profile_id=profile_id,
            report_type="smart_report",
            content_markdown=result.get("report_markdown", ""),
            sections=result.get("sections"),
            model_version=result.get("model_version"),
        )
        db.add(cache_entry)

        return {
            "report_markdown": result.get("report_markdown", ""),
            "sections": result.get("sections"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cached": False,
        }
    except ai_service.AIServiceError:
        raise HTTPException(
            status_code=503,
            detail="Smart Report generation unavailable. Please try again.",
        )


@router.get("/{profile_id}/medications")
async def get_current_medications(
    profile_id: uuid.UUID,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get current active medications for a profile."""
    q = select(Prescription).where(
        Prescription.owner_id == owner.owner_id,
        Prescription.profile_id == profile_id,
        Prescription.active == True,
    ).order_by(Prescription.prescribed_at.desc())

    result = await db.execute(q)
    prescriptions = result.scalars().all()

    medications = []
    for rx in prescriptions:
        if isinstance(rx.items, list):
            for item in rx.items:
                medications.append({
                    "drug_name": item.get("drug_name", item.get("drug", "Unknown")),
                    "dose": item.get("dose", ""),
                    "frequency": item.get("frequency", ""),
                    "duration": item.get("duration", ""),
                    "prescribed_by": rx.prescribed_by,
                    "prescribed_at": rx.prescribed_at.isoformat() if rx.prescribed_at else None,
                    "prescription_id": str(rx.prescription_id),
                })

    return {"medications": medications, "total": len(medications)}
