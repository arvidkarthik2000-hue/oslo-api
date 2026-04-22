"""Audit event logging service.

Every mutation MUST emit an audit event. If audit write fails, the mutation fails.
"""
import json
import uuid
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession


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

    Runs within the current transaction; if this fails the parent mutation also rolls back.
    """
    stmt = text("""
        INSERT INTO audit_event (
            owner_id, profile_id, action, actor_type, actor_id,
            resource_type, resource_id, metadata, ip_address, user_agent
        )
        VALUES (
            :owner_id, :profile_id, :action, :actor_type, :actor_id,
            :resource_type, :resource_id, :metadata, :ip_address, :user_agent
        )
    """).bindparams(bindparam("metadata", type_=JSONB))

    await db.execute(
        stmt,
        {
            "owner_id": owner_id,
            "profile_id": profile_id,
            "action": action,
            "actor_type": actor_type,
            "actor_id": actor_id or owner_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata,  # pass dict directly; SQLAlchemy JSONB adapter handles it
            "ip_address": ip_address,
            "user_agent": user_agent,
        },
    )