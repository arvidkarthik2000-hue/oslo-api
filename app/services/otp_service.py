"""MSG91 OTP service for phone verification."""
import httpx
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MSG91_BASE = "https://control.msg91.com/api/v5"


async def send_otp(phone_number: str) -> dict:
    """Send OTP via MSG91.
    
    Args:
        phone_number: E.164 format phone number (e.g., '919876543210')
    
    Returns:
        dict with request_id and status
    """
    # Strip + prefix if present
    phone = phone_number.lstrip("+")
    
    # In development mode, use a mock OTP
    if settings.environment == "development" and not settings.msg91_auth_key:
        logger.warning("DEV MODE: Sending mock OTP to %s***", phone[:4])
        return {"request_id": "dev-mock-request", "type": "success"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MSG91_BASE}/otp",
            headers={"authkey": settings.msg91_auth_key},
            params={
                "template_id": settings.msg91_template_id,
                "mobile": phone,
                "otp_length": settings.msg91_otp_length,
                "otp_expiry": settings.msg91_otp_expiry_minutes,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("OTP sent to %s***: %s", phone[:4], data.get("type"))
        return data


async def verify_otp(phone_number: str, otp: str) -> bool:
    """Verify OTP via MSG91.
    
    Returns True if OTP is valid.
    """
    phone = phone_number.lstrip("+")
    
    # Dev mode: accept '123456' as valid OTP
    if settings.environment == "development" and not settings.msg91_auth_key:
        logger.warning("DEV MODE: Accepting mock OTP for %s***", phone[:4])
        return otp == "123456"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{MSG91_BASE}/otp/verify",
            headers={"authkey": settings.msg91_auth_key},
            params={"mobile": phone, "otp": otp},
            timeout=10,
        )
        data = response.json()
        return data.get("type") == "success"
