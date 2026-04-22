"""Documents router — upload, finalize (classify+extract), list, detail, explain, correct."""
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.database import get_db
from app.models.owner import Owner
from app.models.document import Document
from app.models.extraction import Extraction
from app.models.lab_value import LabValue
from app.models.prescription import Prescription
from app.models.timeline_event import TimelineEvent
from app.dependencies import get_current_owner
from app.services import ai_service
from app.services.audit_service import log_audit_event
from app.schemas.document import (
    DocumentUploadRequest, DocumentUploadResponse,
    DocumentFinalizeRequest, DocumentFinalizeResponse,
    DocumentListResponse, DocumentListItem,
    DocumentDetail, ExtractionDetail,
    ExtractionCorrectionRequest,
    ExplainResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def create_document(
    body: DocumentUploadRequest,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Create a document record. Returns document_id for upload."""
    doc = Document(
        owner_id=owner.owner_id,
        profile_id=body.profile_id,
        source=body.source,
        mime_type=body.mime_type,
        byte_size=body.byte_size,
        page_count=body.page_count,
        s3_key="",  # set on finalize
        sha256="",  # set on finalize
    )
    db.add(doc)
    await db.flush()

    await log_audit_event(
        db, action="document.create", actor_type="user",
        owner_id=owner.owner_id, profile_id=body.profile_id,
        resource_type="document", resource_id=doc.document_id,
        ip_address=request.client.host if request and request.client else None,
    )

    return DocumentUploadResponse(
        document_id=doc.document_id,
        upload_url=None,  # POC: client uploads directly to Supabase storage
        status="pending",
    )


@router.post("/{document_id}/finalize", response_model=DocumentFinalizeResponse)
async def finalize_document(
    document_id: uuid.UUID,
    body: DocumentFinalizeRequest,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """After file upload, trigger classification + extraction pipeline."""
    # Fetch document
    result = await db.execute(
        select(Document).where(
            Document.document_id == document_id,
            Document.owner_id == owner.owner_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Update storage info
    doc.s3_key = body.s3_key
    doc.sha256 = body.sha256 or hashlib.sha256(body.s3_key.encode()).hexdigest()[:16]

    # Image URLs for AI (use s3_key as URL for POC)
    image_urls = body.image_urls if body.image_urls else [body.s3_key]

    # --- Step 1: Classify ---
    try:
        owner_hash = hashlib.sha256(str(owner.owner_id).encode()).hexdigest()
        classify_result = await ai_service.classify(
            str(document_id), image_urls, owner_hash
        )
        doc.classified_as = classify_result.get("class", "other")
        doc.classification_confidence = classify_result.get("confidence")
        doc.classification_model_version = classify_result.get("model_version")
    except ai_service.AIServiceError as e:
        logger.error("Classification failed for %s: %s", document_id, e)
        doc.classified_as = "other"
        doc.classification_confidence = 0.0

    # --- Step 2: Extract ---
    extraction_id = None
    try:
        extract_result = await ai_service.extract(
            str(document_id), image_urls, doc.classified_as or "other"
        )

        extraction = Extraction(
            document_id=doc.document_id,
            owner_id=owner.owner_id,
            profile_id=doc.profile_id,
            model_version=extract_result.get("model_version", "unknown"),
            schema_version=extract_result.get("schema_version", "v1"),
            json_payload=extract_result.get("extraction", {}),
            validation_flags=extract_result.get("validation_flags"),
            is_current=True,
        )
        db.add(extraction)
        await db.flush()
        extraction_id = extraction.extraction_id

        # Denormalize: populate lab_value or prescription tables
        ext_data = extract_result.get("extraction", {})
        report_date_str = ext_data.get("report_date")
        report_date = None
        if report_date_str:
            try:
                from datetime import date as date_type
                report_date = datetime.strptime(report_date_str, "%Y-%m-%d")
                doc.document_date = report_date.date() if hasattr(report_date, 'date') else report_date
            except (ValueError, TypeError):
                pass

        doc.provider_name = ext_data.get("lab_name") or ext_data.get("prescribed_by")
        observed_at = report_date or datetime.now(timezone.utc)

        if doc.classified_as == "lab_report" and "tests" in ext_data:
            for test in ext_data["tests"]:
                lv = LabValue(
                    owner_id=owner.owner_id,
                    profile_id=doc.profile_id,
                    document_id=doc.document_id,
                    extraction_id=extraction.extraction_id,
                    test_name=test.get("test_name", "Unknown"),
                    loinc_code=test.get("loinc_code"),
                    value_num=test.get("value_num"),
                    value_text=str(test.get("value_num", "")),
                    unit=test.get("unit"),
                    ref_low=test.get("ref_low"),
                    ref_high=test.get("ref_high"),
                    observed_at=observed_at,
                    flag=test.get("flag", "ok"),
                )
                db.add(lv)

        elif doc.classified_as == "prescription" and "medications" in ext_data:
            from datetime import date as date_type
            rx = Prescription(
                owner_id=owner.owner_id,
                profile_id=doc.profile_id,
                document_id=doc.document_id,
                prescribed_by=ext_data.get("prescribed_by"),
                prescribed_at=doc.document_date or date_type.today(),
                items=ext_data["medications"],
                active=True,
                source="upload",
            )
            db.add(rx)

    except ai_service.AIServiceError as e:
        logger.error("Extraction failed for %s: %s", document_id, e)

    # --- Step 3: Create timeline event ---
    event_type_map = {
        "lab_report": "lab",
        "prescription": "prescription",
        "discharge_summary": "discharge",
        "imaging_report": "imaging",
        "consultation_note": "visit",
    }
    evt_type = event_type_map.get(doc.classified_as or "", "note")

    # Build flags from extracted lab values
    flags = None
    if doc.classified_as == "lab_report":
        ext_data = (await db.execute(
            select(Extraction.json_payload).where(Extraction.extraction_id == extraction_id)
        )).scalar_one_or_none() if extraction_id else None
        if ext_data and "tests" in (ext_data or {}):
            flag_items = [
                {"text": f"{t['test_name']} {t.get('value_num', '')}", "severity": t.get("flag", "ok")}
                for t in ext_data["tests"]
                if t.get("flag") in ("watch", "flag", "critical")
            ][:3]  # top 3 flags
            if flag_items:
                flags = flag_items

    timeline = TimelineEvent(
        owner_id=owner.owner_id,
        profile_id=doc.profile_id,
        event_type=evt_type,
        occurred_at=doc.uploaded_at,
        source_ref=doc.document_id,
        source_ref_type="document",
        title=f"{(doc.classified_as or 'document').replace('_', ' ').title()} uploaded",
        subtitle=doc.provider_name,
        provider=doc.provider_name,
        flags=flags,
    )
    db.add(timeline)

    await log_audit_event(
        db, action="document.finalize", actor_type="system",
        owner_id=owner.owner_id, profile_id=doc.profile_id,
        resource_type="document", resource_id=doc.document_id,
        metadata={"classified_as": doc.classified_as, "extraction_id": str(extraction_id)},
    )

    return DocumentFinalizeResponse(
        document_id=doc.document_id,
        classified_as=doc.classified_as,
        classification_confidence=doc.classification_confidence,
        extraction_id=extraction_id,
        processing_status="complete",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    profile_id: uuid.UUID | None = None,
    category: str | None = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """List documents with optional filters."""
    q = select(Document).where(
        Document.owner_id == owner.owner_id,
        Document.deleted_at.is_(None),
    ).order_by(Document.uploaded_at.desc())

    if profile_id:
        q = q.where(Document.profile_id == profile_id)
    if category:
        q = q.where(Document.classified_as == category)

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    docs = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentListItem.model_validate(d) for d in docs],
        total=total,
    )


@router.get("/counts")
async def document_counts(
    profile_id: uuid.UUID | None = None,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get document counts by category for Records tab."""
    q = select(
        Document.classified_as,
        func.count().label("count"),
    ).where(
        Document.owner_id == owner.owner_id,
        Document.deleted_at.is_(None),
    ).group_by(Document.classified_as)

    if profile_id:
        q = q.where(Document.profile_id == profile_id)

    result = await db.execute(q)
    rows = result.all()
    return {"counts": {row[0] or "other": row[1] for row in rows}}


@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get document detail with extractions."""
    result = await db.execute(
        select(Document).where(
            Document.document_id == document_id,
            Document.owner_id == owner.owner_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Fetch extractions
    ext_result = await db.execute(
        select(Extraction).where(
            Extraction.document_id == document_id
        ).order_by(Extraction.created_at.desc())
    )
    extractions = ext_result.scalars().all()

    return {
        "document_id": doc.document_id,
        "profile_id": doc.profile_id,
        "source": doc.source,
        "mime_type": doc.mime_type,
        "byte_size": doc.byte_size,
        "page_count": doc.page_count,
        "s3_key": doc.s3_key,
        "uploaded_at": doc.uploaded_at,
        "classified_as": doc.classified_as,
        "classification_confidence": doc.classification_confidence,
        "document_date": doc.document_date,
        "provider_name": doc.provider_name,
        "extractions": [
            {
                "extraction_id": e.extraction_id,
                "model_version": e.model_version,
                "schema_version": e.schema_version,
                "json_payload": e.json_payload,
                "validation_flags": e.validation_flags,
                "user_corrected": e.user_corrected,
                "is_current": e.is_current,
                "created_at": e.created_at,
            }
            for e in extractions
        ],
    }


@router.post("/{document_id}/correct")
async def correct_extraction(
    document_id: uuid.UUID,
    body: ExtractionCorrectionRequest,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Submit user correction — creates new extraction, supersedes previous."""
    # Verify document ownership
    result = await db.execute(
        select(Document).where(
            Document.document_id == document_id,
            Document.owner_id == owner.owner_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Mark all existing extractions as not current
    await db.execute(
        update(Extraction)
        .where(Extraction.document_id == document_id)
        .values(is_current=False)
    )

    # Create new corrected extraction
    new_ext = Extraction(
        document_id=document_id,
        owner_id=owner.owner_id,
        profile_id=doc.profile_id,
        model_version="user-correction",
        schema_version="v1",
        json_payload=body.corrected_payload,
        user_corrected=True,
        user_corrected_at=datetime.now(timezone.utc),
        is_current=True,
    )
    db.add(new_ext)
    await db.flush()

    await log_audit_event(
        db, action="extraction.correct", actor_type="user",
        owner_id=owner.owner_id, profile_id=doc.profile_id,
        resource_type="extraction", resource_id=new_ext.extraction_id,
    )

    return {
        "extraction_id": new_ext.extraction_id,
        "status": "corrected",
    }


@router.post("/{document_id}/explain", response_model=ExplainResponse)
async def explain_document(
    document_id: uuid.UUID,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get AI explanation for a document."""
    # Fetch document + current extraction
    result = await db.execute(
        select(Document).where(
            Document.document_id == document_id,
            Document.owner_id == owner.owner_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    ext_result = await db.execute(
        select(Extraction).where(
            Extraction.document_id == document_id,
            Extraction.is_current == True,
        )
    )
    extraction = ext_result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=404, detail="No extraction found")

    try:
        explain_result = await ai_service.explain(
            str(document_id),
            extraction.json_payload,
        )
        return ExplainResponse(
            explanation_markdown=explain_result.get("explanation_markdown", ""),
            critical_flags=explain_result.get("critical_flags", []),
            urgency=explain_result.get("urgency", "routine"),
        )
    except ai_service.AIServiceError:
        raise HTTPException(status_code=503, detail="Explanation unavailable. Tap to retry.")
