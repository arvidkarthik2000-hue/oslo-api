"""Wearable router — Health Connect data sync and trends."""
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.database import get_db
from app.models.owner import Owner
from app.models.wearable_reading import WearableReading
from app.dependencies import get_current_owner

logger = logging.getLogger(__name__)
router = APIRouter()


class WearableReadingItem(BaseModel):
    metric: str  # 'resting_hr' | 'hrv' | 'sleep_minutes' | 'steps'
    value: float
    observed_at: datetime
    source: str = "health_connect"


class WearableSyncRequest(BaseModel):
    profile_id: uuid.UUID
    readings: list[WearableReadingItem]


@router.post("/sync")
async def sync_wearable(
    body: WearableSyncRequest,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Receive Health Connect readings and store them."""
    count = 0
    for r in body.readings:
        reading = WearableReading(
            owner_id=owner.owner_id,
            profile_id=body.profile_id,
            metric=r.metric,
            value=r.value,
            observed_at=r.observed_at,
            source=r.source,
        )
        db.add(reading)
        count += 1

    await db.flush()
    return {"synced": count, "status": "ok"}


@router.get("/trends/{profile_id}")
async def wearable_trends(
    profile_id: uuid.UUID,
    days: int = Query(default=7, le=90),
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get wearable data trends for sparklines."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    q = select(WearableReading).where(
        WearableReading.owner_id == owner.owner_id,
        WearableReading.profile_id == profile_id,
        WearableReading.observed_at >= cutoff,
    ).order_by(WearableReading.metric, WearableReading.observed_at)

    result = await db.execute(q)
    readings = result.scalars().all()

    # Group by metric
    series: dict[str, list] = {}
    for r in readings:
        if r.metric not in series:
            series[r.metric] = []
        series[r.metric].append({
            "value": float(r.value),
            "observed_at": r.observed_at.isoformat(),
        })

    # Build summary
    metrics = []
    metric_labels = {
        "resting_hr": "Resting Heart Rate",
        "hrv": "Heart Rate Variability",
        "sleep_minutes": "Sleep Duration",
        "steps": "Daily Steps",
    }
    metric_units = {
        "resting_hr": "bpm",
        "hrv": "ms",
        "sleep_minutes": "min",
        "steps": "steps",
    }

    for metric, points in series.items():
        values = [p["value"] for p in points]
        metrics.append({
            "metric": metric,
            "label": metric_labels.get(metric, metric),
            "unit": metric_units.get(metric, ""),
            "latest": values[-1] if values else None,
            "avg": round(sum(values) / len(values), 1) if values else None,
            "sparkline": values[-20:],  # last 20 readings
            "data_points": len(points),
            "series": points,
        })

    return {"metrics": metrics, "days": days}
