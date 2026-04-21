"""JWT token creation and verification."""
import uuid
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.config import get_settings

settings = get_settings()


def create_access_token(owner_id: uuid.UUID, extra_claims: dict | None = None) -> str:
    """Create a short-lived access token (1 hour)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(owner_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(owner_id: uuid.UUID) -> str:
    """Create a long-lived refresh token (30 days)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(owner_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str, expected_type: str = "access") -> dict:
    """Verify and decode a JWT token.
    
    Returns the decoded payload or raises JWTError.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != expected_type:
            raise JWTError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")
        return payload
    except JWTError:
        raise


def get_owner_id_from_token(token: str) -> uuid.UUID:
    """Extract owner_id from a verified access token."""
    payload = verify_token(token, expected_type="access")
    return uuid.UUID(payload["sub"])
