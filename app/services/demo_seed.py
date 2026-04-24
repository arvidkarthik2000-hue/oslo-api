"""Demo seed data — creates realistic documents for POC testing.

Called from /auth/dev-create on first user creation.
This data is mocked — it simulates what the AI extraction pipeline
would produce for real uploaded documents.

NO fake prescriptions — only seed lab reports. Medications should
only appear when a user actually uploads a prescription.
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


# Realistic Indian lab report data
SEED_LAB_TESTS = [
    {"test_name": "Hemoglobin", "loinc_code": "718-7", "value": "14.2", "unit": "g/dL", "reference_range": "13.0-17.0", "flag": "normal"},
    {"test_name": "Fasting Blood Glucose", "loinc_code": "1558-6", "value": "126", "unit": "mg/dL", "reference_range": "70-100", "flag": "above"},
    {"test_name": "HbA1c", "loinc_code": "4548-4", "value": "6.8", "unit": "%", "reference_range": "4.0-5.6", "flag": "above"},
    {"test_name": "Total Cholesterol", "loinc_code": "2093-3", "value": "228", "unit": "mg/dL", "reference_range": "125-200", "flag": "above"},
    {"test_name": "LDL Cholesterol", "loinc_code": "2089-1", "value": "152", "unit": "mg/dL", "reference_range": "0-100", "flag": "above"},
    {"test_name": "HDL Cholesterol", "loinc_code": "2085-9", "value": "42", "unit": "mg/dL", "reference_range": "40-60", "flag": "normal"},
    {"test_name": "Triglycerides", "loinc_code": "2571-8", "value": "178", "unit": "mg/dL", "reference_range": "0-150", "flag": "above"},
    {"test_name": "Creatinine", "loinc_code": "2160-0", "value": "1.0", "unit": "mg/dL", "reference_range": "0.7-1.3", "flag": "normal"},
    {"test_name": "TSH", "loinc_code": "3016-3", "value": "4.2", "unit": "mIU/L", "reference_range": "0.4-4.0", "flag": "above"},
    {"test_name": "SGPT (ALT)", "loinc_code": "1742-6", "value": "32", "unit": "U/L", "reference_range": "7-56", "flag": "normal"},
    {"test_name": "SGOT (AST)", "loinc_code": "1920-8", "value": "28", "unit": "U/L", "reference_range": "10-40", "flag": "normal"},
    {"test_name": "Vitamin D (25-OH)", "loinc_code": "1989-3", "value": "18", "unit": "ng/mL", "reference_range": "30-100", "flag": "below"},
]


async def cleanup_demo_data(db, owner_id: uuid.UUID):
    """Delete ALL data for the demo owner. Use before re-seeding."""
    from sqlalchemy import text
    
    tables = [
        "smart_report_cache",
        "document_embedding",
        "lab_value",
        "extraction",
        "timeline_event",
        "prescription",
        "document",
    ]
    
    for table in tables:
        try:
            await db.execute(
                text(f"DELETE FROM {table} WHERE owner_id = :oid"),
                {"oid": str(owner_id)},
            )
        except Exception as e:
            logger.warning("cleanup %s: %s", table, e)
    
    logger.info("Cleaned up all demo data for owner %s", owner_id)


async def seed_demo_documents(db, owner_id: uuid.UUID, profile_id: uuid.UUID):
    """Create demo documents with extractions for the demo owner.
    
    Only seeds if no documents exist yet for this owner.
    Only lab reports — NO prescriptions or fake medications.
    """
    from sqlalchemy import select, func
    from app.models.document import Document
    from app.models.extraction import Extraction
    from app.models.lab_value import LabValue
    from app.models.timeline_event import TimelineEvent
    
    # Check if documents already exist
    count = await db.execute(
        select(func.count()).select_from(Document).where(Document.owner_id == owner_id)
    )
    if count.scalar() > 0:
        logger.info("Demo owner already has documents, skipping seed")
        return
    
    now = datetime.now(timezone.utc)
    
    # --- Lab Report only ---
    lab_doc_id = uuid.uuid4()
    lab_ext_id = uuid.uuid4()
    lab_report_date = now - timedelta(days=14)  # 2 weeks ago
    
    lab_doc = Document(
        document_id=lab_doc_id,
        owner_id=owner_id,
        profile_id=profile_id,
        source="upload",
        mime_type="application/pdf",
        byte_size=245000,
        page_count=2,
        s3_key=f"demo/{lab_doc_id}.pdf",
        sha256="demo_lab_sha256",
        classified_as="lab_report",
        classification_confidence=0.96,
        document_date=lab_report_date.date(),
        provider_name="Sample Lab",
    )
    db.add(lab_doc)
    
    lab_ext = Extraction(
        extraction_id=lab_ext_id,
        document_id=lab_doc_id,
        owner_id=owner_id,
        profile_id=profile_id,
        model_version="demo_seed_v1",
        schema_version="1.0",
        json_payload={
            "tests": SEED_LAB_TESTS,
            "lab_name": "Sample Lab",
            "report_date": lab_report_date.strftime("%Y-%m-%d"),
            "patient_name": "Demo User",
        },
        validation_flags=[],
        is_current=True,
    )
    db.add(lab_ext)
    
    # Create lab_value rows for trending
    for test in SEED_LAB_TESTS:
        ref_parts = test["reference_range"].split("-")
        ref_low = float(ref_parts[0]) if len(ref_parts) == 2 else None
        ref_high = float(ref_parts[1]) if len(ref_parts) == 2 else None
        
        lv = LabValue(
            owner_id=owner_id,
            profile_id=profile_id,
            document_id=lab_doc_id,
            extraction_id=lab_ext_id,
            test_name=test["test_name"],
            loinc_code=test["loinc_code"],
            value_num=float(test["value"]),
            value_text=test["value"],
            unit=test["unit"],
            ref_low=ref_low,
            ref_high=ref_high,
            flag=test["flag"],
            observed_at=lab_report_date,
        )
        db.add(lv)
    
    # Timeline event for lab report
    lab_timeline = TimelineEvent(
        owner_id=owner_id,
        profile_id=profile_id,
        event_type="lab",
        title="Lab Report uploaded",
        subtitle="Sample Lab",
        provider="Sample Lab",
        occurred_at=lab_report_date,
        source_ref=lab_doc_id,
        source_ref_type="document",
        flags=[
            {"text": "Fasting Glucose 126", "severity": "above"},
            {"text": "HbA1c 6.8", "severity": "above"},
            {"text": "Total Cholesterol 228", "severity": "above"},
        ],
    )
    db.add(lab_timeline)
    
    logger.info("Demo seed: created lab report (%s) — no prescriptions", lab_doc_id)


# Alias for backward compatibility with auth.py import
seed_demo_data = seed_demo_documents
