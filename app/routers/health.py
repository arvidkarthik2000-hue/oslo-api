"""Health check endpoint — public, no auth."""
from fastapi import APIRouter
from app.config import get_settings
import httpx

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Public health check. Returns app status and AI service connectivity."""
    ai_status = "unknown"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{settings.ai_service_base_url}/health",
                headers={"Authorization": f"Bearer {settings.ai_service_api_key}"},
                timeout=5,
            )
            ai_status = r.json().get("status", "ok") if r.status_code == 200 else "degraded"
    except Exception:
        ai_status = "unreachable"
    
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "ai_service_status": ai_status,
    }
