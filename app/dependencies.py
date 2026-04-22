"""Shared FastAPI dependencies."""
import uuid
import logging
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db, set_tenant_context
from app.services.jwt_service import verify_token
from app.models.owner import Owner
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

security = HTTPBearer(auto_error=False)  # auto_error=False for optional auth in dev

# Fixed demo owner ID for POC dev mode
DEMO_OWNER_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")


async def get_current_owner(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Owner:
    """Verify JWT and return the current Owner, setting RLS context.

    In development mode: if no token is provided, uses the demo owner.
    """
    owner_id: uuid.UUID | None = None

    # Try to extract from JWT
    if credentials and credentials.credentials:
        try:
            payload = verify_token(credentials.credentials, expected_type="access")
            owner_id = uuid.UUID(payload["sub"])
        except (JWTError, KeyError, ValueError):
            if settings.environment != "development":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # In dev mode, fall through to demo owner

    # Dev mode fallback: use demo owner
    if owner_id is None:
        if settings.environment != "development":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        owner_id = DEMO_OWNER_ID
        logger.debug("Dev mode: using demo owner %s", owner_id)

    # Set RLS tenant context
    await set_tenant_context(db, owner_id)

    # Fetch owner
    result = await db.execute(
        select(Owner).where(Owner.owner_id == owner_id, Owner.deleted_at.is_(None))
    )
    owner = result.scalar_one_or_none()

    if owner is None:
        if settings.environment == "development":
            # Auto-create demo owner in dev mode
            owner = Owner(
                owner_id=DEMO_OWNER_ID,
                phone_number="9199999999",
            )
            db.add(owner)
            await db.flush()
            logger.info("Dev mode: auto-created demo owner %s", DEMO_OWNER_ID)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account not found or deleted",
            )

    return owner
