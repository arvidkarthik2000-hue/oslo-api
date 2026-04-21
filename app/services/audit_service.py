"""Audit event logging service.

Every mutation MUST emit an audit event. If audit write fails, the mutation fails.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def log_audit_event(
    db: AsyncSession,
    action: str,
    actor_type: str = "user",
    owner_id: uuid.UUID | None = None,
    profile_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Write an audit event to the audit_event table.
    
    This runs within the current transaction, so if it fails,
    the parent mutation also rolls back.
    """
    await db.execute(
        text("""
            INSERT INTO audit_event (owner_id, profile_id, action, actor_type, actor_id,
                                    resource_type, resource_id, metadata, ip_address, user_agent)
            VALUES (:owner_id, :profile_id, :action, :actor_type, :actor_id,
                    :resource_type, :resource_id, :metadata::jsonb, :ip_address, :user_agent)
        """),
        {
            "owner_id": owner_id,
            "profile_id": profile_id,
            "action": action,
            "actor_type": actor_type,
            "actor_id": actor_id or owner_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": str(metadata) if metadata else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
        },
    )
