"""Shared FastAPI dependencies."""
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db, set_tenant_context
from app.services.jwt_service import verify_token
from app.models.owner import Owner

security = HTTPBearer()


async def get_current_owner(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Owner:
    """Verify JWT and return the current Owner, setting RLS context."""
    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        owner_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Set RLS tenant context
    await set_tenant_context(db, owner_id)
    
    # Fetch owner
    result = await db.execute(select(Owner).where(Owner.owner_id == owner_id, Owner.deleted_at.is_(None)))
    owner = result.scalar_one_or_none()
    
    if owner is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found or deleted")
    
    return owner
