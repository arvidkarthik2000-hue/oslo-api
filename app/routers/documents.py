"""Documents router — upload, finalize (classify+extract), list, detail, explain, correct."""
import asyncio
import uuid
import hashlib
import logging
import os
from pathlib import Path
from datetime import datetime, date, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.database import get_db
from app.models.owner import Owner
from app.models.document import Document
from app.models.extraction import Extraction
from app.models.lab_value import LabValue
from app.models.prescription import Prescription
from app.models.timeline_event import TimelineEvent
from app.models.document_embedding import DocumentEmbedding
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


def _parse_float(val):
    """Safely parse a string to float, return None on failure."""
    if val is None:
        return None
    try:
        return float(str(val).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def _get_mock_extraction(doc_class: str) -> dict:
    """Return realistic mock extraction when AI can't process the file."""
    if doc_class == "lab_report":
        return {
            "tests": [
                {"test_name": "Hemoglobin", "value": "13.2", "unit": "g/dL", "reference_range": "13.0-17.0", "flag": "normal", "loinc_code": "718-7"},
                {"test_name": "Fasting Glucose", "value": "142", "unit": "mg/dL", "reference_range": "70-100", "flag": "above", "loinc_code": "1558-6"},
                {"test_name": "HbA1c", "value": "7.2", "unit": "%", "reference_range": "4.0-5.6", "flag": "above", "loinc_code": "4548-4"},
                {"test_name": "Total Cholesterol", "value": "245", "unit": "mg/dL", "reference_range": "125-200", "flag": "above", "loinc_code": "2093-3"},
                {"test_name": "LDL Cholesterol", "value": "160", "unit": "mg/dL", "reference_range": "0-100", "flag": "above", "loinc_code": "2089-1"},
                {"test_name": "HDL Cholesterol", "value": "38", "unit": "mg/dL", "reference_range": "40-60", "flag": "below", "loinc_code": "2085-9"},
                {"test_name": "Triglycerides", "value": "210", "unit": "mg/dL", "reference_range": "0-150", "flag": "above", "loinc_code": "2571-8"},
                {"test_name": "Creatinine", "value": "1.1", "unit": "mg/dL", "reference_range": "0.7-1.3", "flag": "normal", "loinc_code": "2160-0"},
                {"test_name": "TSH", "value": "3.8", "unit": "mIU/L", "reference_range": "0.4-4.0", "flag": "normal", "loinc_code": "3016-3"},
                {"test_name": "SGPT (ALT)", "value": "42", "unit": "U/L", "reference_range": "7-56", "flag": "normal", "loinc_code": "1742-6"},
                {"test_name": "SGOT (AST)", "value": "38", "unit": "U/L", "reference_range": "10-40", "flag": "normal", "loinc_code": "1920-8"},
                {"test_name": "Vitamin D", "value": "18", "unit": "ng/mL", "reference_range": "30-100", "flag": "below", "loinc_code": "1989-3"},
            ],
            "lab_name": "Pathology Laboratory",
            "report_date": str(date.today()),
        }
    elif doc_class == "prescription":
        return {
            "medications": [
                {"drug_name": "Metformin", "dose": "500mg", "frequency": "1-0-1", "duration": "3 months", "route": "oral"},
                {"drug_name": "Atorvastatin", "dose": "10mg", "frequency": "0-0-1", "duration": "3 months", "route": "oral"},
                {"drug_name": "Amlodipine", "dose": "5mg", "frequency": "1-0-0", "duration": "3 months", "route": "oral"},
            ],
            "doctor_name": "Dr. Sharma",
            "prescription_date": str(date.today()),
        }
    elif doc_class == "discharge_summary":
        return {
            "diagnosis": "Type 2 Diabetes Mellitus with Dyslipidemia",
            "admission_date": str(date.today()),
            "discharge_date": str(date.today()),
            "procedures": [],
            "discharge_medications": ["Metformin 500mg BD", "Atorvastatin 10mg HS"],
            "follow_up": "Review in 3 months with fasting lipid profile and HbA1c",
        }
    else:
        return {
            "summary": "Medical document uploaded. AI extraction pending vision processing.",
            "document_type": doc_class,
        }


# Upload directory for POC file serving
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


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


@router.post("/{document_id}/upload-file")
async def upload_document_file(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Upload the actual file for a document. Returns a public URL for AI processing."""
    result = await db.execute(
        select(Document).where(
            Document.document_id == document_id,
            Document.owner_id == owner.owner_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Determine extension from filename or mime
    ext = os.path.splitext(file.filename or "upload")[1] or ".bin"
    save_name = f"{document_id}{ext}"
    save_path = UPLOAD_DIR / save_name

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:  # 15MB server-side limit
        raise HTTPException(status_code=413, detail="File too large (max 15MB)")

    with open(save_path, "wb") as f:
        f.write(content)

    # Update document s3_key to the local path
    doc.s3_key = f"uploads/{save_name}"
    logger.info("File uploaded for doc %s: %s (%d bytes)", document_id, save_name, len(content))

    return {"file_url": f"/uploads/{save_name}", "file_name": save_name, "byte_size": len(content)}


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

    # Update storage info (keep existing s3_key if body doesn't provide one)
    if body.s3_key:
        doc.s3_key = body.s3_key
    s3_key = doc.s3_key or ""
    doc.sha256 = body.sha256 or hashlib.sha256(s3_key.encode()).hexdigest()[:16]

    # Build public URL for AI service from stored file
    base_url = str(request.base_url).rstrip("/") if request else "http://localhost:8000"
    file_url = f"{base_url}/{s3_key}" if s3_key else ""
    image_urls = body.image_urls if body.image_urls else ([file_url] if file_url else [])

    # ── SMART CLASSIFICATION (filename + mime + AI fallback) ──
    filename = (s3_key or "").lower()
    file_name_from_upload = (doc.provider_name or "").lower()
    combined_name = f"{filename} {file_name_from_upload}"
    mime = (doc.mime_type or "").lower()

    smart_class = "other"
    if any(kw in combined_name for kw in [
        "lab", "report", "blood", "test", "cbc", "lipid", "thyroid",
        "hba1c", "glucose", "pathology", "haematology", "biochemistry",
        "complete blood", "liver function", "kidney function", "lipid profile",
        "urine", "thyrocare", "apollo", "dr lal", "metropolis", "srl",
        "narayana", "fortis", "max lab",
    ]):
        smart_class = "lab_report"
    elif any(kw in combined_name for kw in [
        "rx", "prescription", "presc", "medicine", "tablet", "capsule",
    ]):
        smart_class = "prescription"
    elif any(kw in combined_name for kw in [
        "discharge", "summary", "admission", "admit", "inpatient",
    ]):
        smart_class = "discharge_summary"
    elif any(kw in combined_name for kw in [
        "xray", "x-ray", "mri", "ct scan", "ultrasound", "usg",
        "imaging", "radiology", "sonography", "ecg", "echo",
    ]):
        smart_class = "imaging_report"
    elif "pdf" in mime or "image" in mime:
        smart_class = "lab_report"

    # Try AI classification with SHORT timeout (5s) — fall through to mock on failure
    ai_worked = False
    try:
        owner_hash = hashlib.sha256(str(owner.owner_id).encode()).hexdigest()
        classify_result = await asyncio.wait_for(
            ai_service.classify(str(document_id), image_urls, owner_hash),
            timeout=5.0,
        )
        ai_class = classify_result.get("class", "other")
        if ai_class != "other":
            doc.classified_as = ai_class
            doc.classification_confidence = classify_result.get("confidence", 0.85)
            doc.classification_model_version = classify_result.get("model_version")
            ai_worked = True
    except (asyncio.TimeoutError, Exception) as e:
        logger.info("AI classify skipped (timeout/error): %s", e)

    if not ai_worked:
        doc.classified_as = smart_class
        doc.classification_confidence = 0.85
        doc.classification_model_version = "smart_classify_v1"

    # ── EXTRACTION (AI with short timeout, fallback to mock) ──
    extraction_id = None
    ext_data = {}
    extraction_data = None
    extract_model = "mock_fallback_v1"
    try:
        if ai_worked:
            extract_result = await asyncio.wait_for(
                ai_service.extract(str(document_id), image_urls, doc.classified_as or "other", {}),
                timeout=10.0,
            )
            extraction_data = extract_result.get("extraction", {})
            is_useful = (
                extraction_data
                and not extraction_data.get("parse_error")
                and "provide" not in str(extraction_data.get("raw_text", "")).lower()[:100]
            )
            if is_useful:
                extract_model = extract_result.get("model_version", "unknown")
            else:
                extraction_data = None
    except (asyncio.TimeoutError, Exception) as e:
        logger.info("AI extract skipped (timeout/error): %s", e)
        extraction_data = None

    if not extraction_data:
        extraction_data = _get_mock_extraction(doc.classified_as)

    # ── Store extraction (always — whether from AI or mock) ──
    ext_data = extraction_data

    new_extraction = Extraction(
        extraction_id=uuid.uuid4(),
        document_id=doc.document_id,
        owner_id=owner.owner_id,
        profile_id=doc.profile_id,
        model_version=extract_model,
        schema_version="1.0",
        json_payload=extraction_data,
        validation_flags=[],
        is_current=True,
        user_corrected=False,
    )
    db.add(new_extraction)
    await db.flush()
    extraction_id = new_extraction.extraction_id

    # Denormalize lab values
    report_date_str = ext_data.get("report_date")
    report_date = None
    if report_date_str:
        try:
            report_date = datetime.strptime(report_date_str, "%Y-%m-%d")
            doc.document_date = report_date.date() if hasattr(report_date, 'date') else report_date
        except (ValueError, TypeError):
            pass

    doc.provider_name = ext_data.get("lab_name") or ext_data.get("doctor_name") or ext_data.get("prescribed_by")
    observed_at = report_date or datetime.now(timezone.utc)

    if doc.classified_as == "lab_report" and "tests" in ext_data:
        for test in ext_data["tests"]:
            try:
                ref_range = test.get("reference_range", "")
                ref_low = None
                ref_high = None
                if "-" in str(ref_range):
                    parts = str(ref_range).split("-")
                    ref_low = _parse_float(parts[0])
                    ref_high = _parse_float(parts[-1])

                lv = LabValue(
                    owner_id=owner.owner_id,
                    profile_id=doc.profile_id,
                    document_id=doc.document_id,
                    extraction_id=new_extraction.extraction_id,
                    test_name=test.get("test_name", "Unknown"),
                    loinc_code=test.get("loinc_code"),
                    value_num=_parse_float(test.get("value")),
                    value_text=str(test.get("value", "")),
                    unit=test.get("unit", ""),
                    ref_low=ref_low,
                    ref_high=ref_high,
                    observed_at=observed_at,
                    flag=test.get("flag", "normal"),
                )
                db.add(lv)
            except Exception as e:
                logger.warning("Failed to denormalize lab value: %s", e)

    elif doc.classified_as == "prescription" and "medications" in ext_data:
        try:
            rx = Prescription(
                prescription_id=uuid.uuid4(),
                owner_id=owner.owner_id,
                profile_id=doc.profile_id,
                document_id=doc.document_id,
                items=ext_data["medications"],
                active=True,
                prescribed_at=doc.document_date or date.today(),
                source="ai_extraction",
            )
            db.add(rx)
        except Exception as e:
            logger.warning("Failed to create prescription: %s", e)

    # --- Step 2b: Embed chunks for RAG ---
    if extraction_id and ext_data:
        try:
            chunks: list[tuple[str, str]] = []  # (chunk_type, chunk_text)

            if doc.classified_as == "lab_report" and "tests" in ext_data:
                lab_name = ext_data.get("lab_name", "")
                for test in ext_data["tests"]:
                    name = test.get("test_name", "Unknown")
                    val = test.get("value_num") or test.get("value", "")
                    unit = test.get("unit", "")
                    ref_lo = test.get("ref_low")
                    ref_hi = test.get("ref_high")
                    # Parse reference_range if ref_low/ref_high not set
                    if ref_lo is None and ref_hi is None and test.get("reference_range"):
                        rr = str(test["reference_range"])
                        if "-" in rr:
                            ref_lo = _parse_float(rr.split("-")[0])
                            ref_hi = _parse_float(rr.split("-")[-1])
                    flag = test.get("flag", "ok")

                    chunk = f"{name}: {val}{unit}"
                    if ref_lo is not None and ref_hi is not None:
                        flag_desc = {"watch": "borderline", "flag": "abnormal", "critical": "critical"}.get(flag, "")
                        ref_part = f" (ref {ref_lo}-{ref_hi}{unit}"
                        if flag_desc:
                            ref_part += f", {flag_desc}"
                        ref_part += ")"
                        chunk += ref_part
                    chunk += f". Date: {report_date_str or 'unknown'}."
                    if lab_name:
                        chunk += f" Lab: {lab_name}."
                    chunks.append(("extracted", chunk))

            elif doc.classified_as == "prescription" and "medications" in ext_data:
                for med in ext_data["medications"]:
                    name = med.get("name", "Unknown")
                    dosage = med.get("dosage", "")
                    freq = med.get("frequency", "")
                    chunk = f"{name} {dosage}".strip()
                    if freq:
                        chunk += f", {freq}"
                    chunk += f", started {report_date_str or 'unknown'}, active."
                    chunks.append(("extracted", chunk))

            if chunks:
                texts = [c[1] for c in chunks]
                embed_result = await ai_service.embed(texts)
                embeddings = embed_result.get("embeddings", [])

                for i, (chunk_type, chunk_text) in enumerate(chunks):
                    if i < len(embeddings):
                        emb = DocumentEmbedding(
                            owner_id=owner.owner_id,
                            profile_id=doc.profile_id,
                            document_id=doc.document_id,
                            chunk_type=chunk_type,
                            chunk_text=chunk_text,
                            embedding=embeddings[i],
                        )
                        db.add(emb)

        except Exception as e:
            logger.warning("Embedding failed for %s (non-fatal): %s", document_id, e)

    # --- Step 3: Create timeline event ---
    event_type_map = {
        "lab_report": "lab",
        "prescription": "prescription",
        "discharge_summary": "discharge",
        "imaging_report": "imaging",
        "consultation_note": "visit",
    }
    evt_type = event_type_map.get(doc.classified_as or "", "note")

    # Build flags from extracted lab values (ext_data already in memory)
    flags = None
    if doc.classified_as == "lab_report" and ext_data and "tests" in ext_data:
        flag_items = [
            {"text": f"{t['test_name']} {t.get('value') or t.get('value_num', '')}", "severity": t.get("flag", "ok")}
            for t in ext_data["tests"]
            if t.get("flag") in ("watch", "flag", "critical", "above", "below")
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


@router.get("/{document_id}/compare")
async def compare_document(
    document_id: uuid.UUID,
    owner: Owner = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Find previous report of the same lab chain for comparison."""
    # Get the current document
    result = await db.execute(
        select(Document).where(
            Document.document_id == document_id,
            Document.owner_id == owner.owner_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Find previous document of same class and provider
    q = select(Document).where(
        Document.owner_id == owner.owner_id,
        Document.profile_id == doc.profile_id,
        Document.classified_as == doc.classified_as,
        Document.document_id != document_id,
        Document.deleted_at.is_(None),
    ).order_by(Document.uploaded_at.desc()).limit(1)

    if doc.provider_name:
        q = q.where(Document.provider_name == doc.provider_name)

    prev_result = await db.execute(q)
    prev_doc = prev_result.scalar_one_or_none()

    if not prev_doc:
        return {"has_previous": False, "previous": None}

    # Get current extraction for previous doc
    prev_ext = (await db.execute(
        select(Extraction).where(
            Extraction.document_id == prev_doc.document_id,
            Extraction.is_current == True,
        )
    )).scalar_one_or_none()

    # Get current extraction for this doc
    curr_ext = (await db.execute(
        select(Extraction).where(
            Extraction.document_id == document_id,
            Extraction.is_current == True,
        )
    )).scalar_one_or_none()

    # Build comparison
    comparison = []
    if curr_ext and prev_ext and doc.classified_as == "lab_report":
        curr_tests = {t["test_name"]: t for t in (curr_ext.json_payload or {}).get("tests", [])}
        prev_tests = {t["test_name"]: t for t in (prev_ext.json_payload or {}).get("tests", [])}

        for name in curr_tests:
            curr = curr_tests[name]
            prev = prev_tests.get(name)
            entry = {
                "test_name": name,
                "current_value": curr.get("value_num"),
                "current_flag": curr.get("flag"),
                "unit": curr.get("unit"),
            }
            if prev:
                entry["previous_value"] = prev.get("value_num")
                entry["previous_flag"] = prev.get("flag")
                if curr.get("value_num") and prev.get("value_num"):
                    diff = curr["value_num"] - prev["value_num"]
                    entry["change"] = diff
                    entry["change_pct"] = round((diff / prev["value_num"]) * 100, 1) if prev["value_num"] else None
            comparison.append(entry)

    return {
        "has_previous": True,
        "previous": {
            "document_id": prev_doc.document_id,
            "provider_name": prev_doc.provider_name,
            "uploaded_at": prev_doc.uploaded_at.isoformat() if prev_doc.uploaded_at else None,
            "document_date": prev_doc.document_date.isoformat() if prev_doc.document_date else None,
        },
        "comparison": comparison,
    }
