"""Trends router — lab value time series for charting."""
import uuid
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct

from app.database import get_db
from app.models.owner import Owner
from app.models.lab_value import LabValue
from app.dependencies import get_current_owner

logger = logging.getLogger(__name__)
router = APIRouter()

# System → test name mapping for filter chips
SYSTEM_TESTS = {
    "cardiovascular": ["Total Cholesterol", "LDL Cholesterol", "HDL Cholesterol", "Triglycerides", "Hs-CRP"],
    "metabolic": ["Fasting Glucose", "HbA1c", "TSH"],
    "renal": ["Creatinine", "Urea", "eGFR", "Potassium", "Sodium"],
    "liver": ["SGPT (ALT)", "SGOT (AST)", "Bilirubin Total", "ALP", "GGT"],
    "endocrine": ["TSH", "T3", "T4", "Cortisol", "Testosterone"],
    "inflammatory": ["CRP", "ESR", "Ferritin"],
}


@router.get("/{profile_id}")
async def get_trends(
    profile_id: uuid.UUID,
    system: str | None = None,
    test_name: str | None = None,
    limit: int = Query(default=100, le=500),
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get lab value trends for a profile. Filter by system or specific test."""
    q = select(LabValue).where(
        LabValue.owner_id == owner.owner_id,
        LabValue.profile_id == profile_id,
        LabValue.value_num.isnot(None),
    ).order_by(LabValue.test_name, LabValue.observed_at.desc())

    # Filter by system
    if system and system.lower() in SYSTEM_TESTS:
        test_names = SYSTEM_TESTS[system.lower()]
        q = q.where(LabValue.test_name.in_(test_names))
    elif test_name:
        q = q.where(LabValue.test_name.ilike(f"%{test_name}%"))

    q = q.limit(limit)
    result = await db.execute(q)
    values = result.scalars().all()

    # Group by test name for charting
    series: dict[str, list] = {}
    for v in values:
        if v.test_name not in series:
            series[v.test_name] = []
        series[v.test_name].append({
            "value": float(v.value_num) if v.value_num else None,
            "unit": v.unit,
            "observed_at": v.observed_at.isoformat() if v.observed_at else None,
            "ref_low": float(v.ref_low) if v.ref_low else None,
            "ref_high": float(v.ref_high) if v.ref_high else None,
            "flag": v.flag,
            "loinc_code": v.loinc_code,
        })

    # Build metric cards data
    metrics = []
    for name, points in series.items():
        if not points:
            continue
        latest = points[0]  # already desc sorted
        sparkline_values = [p["value"] for p in reversed(points) if p["value"] is not None][:20]
        metrics.append({
            "test_name": name,
            "latest_value": latest["value"],
            "unit": latest["unit"],
            "ref_low": latest["ref_low"],
            "ref_high": latest["ref_high"],
            "flag": latest["flag"],
            "sparkline": sparkline_values,
            "data_points": len(points),
            "series": points,
        })

    return {"metrics": metrics, "total_tests": len(metrics)}


@router.get("/{profile_id}/available-tests")
async def get_available_tests(
    profile_id: uuid.UUID,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get list of unique test names available for this profile."""
    q = select(
        LabValue.test_name,
        func.count().label("count"),
        func.max(LabValue.observed_at).label("latest"),
    ).where(
        LabValue.owner_id == owner.owner_id,
        LabValue.profile_id == profile_id,
    ).group_by(LabValue.test_name).order_by(func.count().desc())

    result = await db.execute(q)
    rows = result.all()

    return {
        "tests": [
            {
                "test_name": row[0],
                "count": row[1],
                "latest": row[2].isoformat() if row[2] else None,
            }
            for row in rows
        ]
    }
