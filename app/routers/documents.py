"""Documents router — upload, list, detail, delete (Phase 1 stubs + Phase 2 full)."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.owner import Owner
from app.dependencies import get_current_owner

router = APIRouter()


@router.get("")
async def list_documents(
    profile_id: uuid.UUID | None = None,
    category: str | None = None,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """List documents. Full implementation in Phase 2."""
    # Phase 1 stub
    return {"documents": [], "total": 0}


@router.post("/upload-url")
async def create_upload_url(
    owner: Owner = Depends(get_current_owner),
):
    """Generate S3 presigned upload URL. Full implementation in Phase 2."""
    # Phase 2: S3 presigned URL generation
    return {"message": "Document upload available in Phase 2"}


@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get document detail. Full implementation in Phase 2."""
    return {"message": "Document detail available in Phase 2"}
