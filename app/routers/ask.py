"""Ask AI router — answer health questions using patient records."""
import uuid
import hashlib
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.owner import Owner
from app.models.lab_value import LabValue
from app.models.prescription import Prescription
from app.models.extraction import Extraction
from app.models.document_embedding import DocumentEmbedding
from app.dependencies import get_current_owner
from app.services import ai_service

logger = logging.getLogger(__name__)
router = APIRouter()


class AskRequest(BaseModel):
    profile_id: uuid.UUID
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    answer_markdown: str
    intent: str | None = None
    refused: bool = False
    critical_flag: bool = False
    citations: list[dict] | None = None
    disclaimer_appended: bool = True


@router.post("", response_model=AskResponse)
async def ask_question(
    body: AskRequest,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Answer a health question using the user's records as context."""
    # Gather context: recent lab values + prescriptions + extractions
    lab_q = select(LabValue).where(
        LabValue.owner_id == owner.owner_id,
        LabValue.profile_id == body.profile_id,
    ).order_by(LabValue.observed_at.desc()).limit(100)
    lab_values = (await db.execute(lab_q)).scalars().all()

    rx_q = select(Prescription).where(
        Prescription.owner_id == owner.owner_id,
        Prescription.profile_id == body.profile_id,
    ).order_by(Prescription.prescribed_at.desc()).limit(20)
    prescriptions = (await db.execute(rx_q)).scalars().all()

    # Build context documents for AI
    context_documents = []
    for lv in lab_values:
        context_documents.append({
            "type": "lab_value",
            "test_name": lv.test_name,
            "value": float(lv.value_num) if lv.value_num else None,
            "unit": lv.unit,
            "observed_at": lv.observed_at.isoformat() if lv.observed_at else None,
            "flag": lv.flag,
            "ref_range": f"{lv.ref_low}-{lv.ref_high}" if lv.ref_low and lv.ref_high else None,
        })

    for rx in prescriptions:
        context_documents.append({
            "type": "prescription",
            "items": rx.items,
            "prescribed_by": rx.prescribed_by,
            "prescribed_at": rx.prescribed_at.isoformat() if rx.prescribed_at else None,
            "active": rx.active,
        })

    # --- RAG retrieval: embed question → pgvector cosine search → top 5 chunks ---
    try:
        embed_result = await ai_service.embed([body.question])
        query_vec = embed_result.get("embeddings", [[]])[0]
        if query_vec:
            rag_stmt = (
                select(
                    DocumentEmbedding.chunk_text,
                    DocumentEmbedding.chunk_type,
                    DocumentEmbedding.document_id,
                    DocumentEmbedding.embedding.cosine_distance(query_vec).label("distance"),
                )
                .where(
                    DocumentEmbedding.owner_id == owner.owner_id,
                    DocumentEmbedding.profile_id == body.profile_id,
                )
                .order_by(DocumentEmbedding.embedding.cosine_distance(query_vec))
                .limit(5)
            )
            rag_rows = (await db.execute(rag_stmt)).all()
            for row in rag_rows:
                context_documents.append({
                    "type": "rag_chunk",
                    "chunk_type": row.chunk_type,
                    "text": row.chunk_text,
                    "relevance_score": round(1.0 - row.distance, 4),
                })
    except Exception as e:
        logger.warning("RAG retrieval failed (using structured context only): %s", e)

    try:
        owner_hash = hashlib.sha256(str(owner.owner_id).encode()).hexdigest()
        result = await ai_service.ask(
            owner_id_hash=owner_hash,
            profile_id=str(body.profile_id),
            question=body.question,
            context_documents=context_documents,
        )

        return AskResponse(
            answer_markdown=result.get("answer_markdown", ""),
            intent=result.get("intent"),
            refused=result.get("refused", False),
            critical_flag=result.get("critical_flag", False),
            citations=result.get("citations"),
            disclaimer_appended=result.get("disclaimer_appended", True),
        )
    except ai_service.AIServiceError:
        raise HTTPException(
            status_code=503,
            detail="Ask AI is temporarily unavailable. Please try again.",
        )
