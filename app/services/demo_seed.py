"""Demo seed data — creates realistic documents for POC testing.

Called from /auth/dev-create on first user creation.
Seeds 3 lab reports from different Indian lab chains with realistic values.
NO fake prescriptions — medications should only appear when a user
actually uploads a prescription.
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


# Three realistic Indian lab reports with different dates and labs
SEED_REPORTS = [
    {
        "lab_name": "Anderson Diagnostics",
        "days_ago": 14,
        "tests": [
            {"test_name": "Hemoglobin", "loinc_code": "718-7", "value": "14.8", "unit": "g/dL", "reference_range": "13.0-17.0", "flag": "normal"},
            {"test_name": "Fasting Glucose", "loinc_code": "1558-6", "value": "142", "unit": "mg/dL", "reference_range": "70-100", "flag": "above"},
            {"test_name": "HbA1c", "loinc_code": "4548-4", "value": "7.2", "unit": "%", "reference_range": "4.0-5.6", "flag": "above"},
            {"test_name": "Total Cholesterol", "loinc_code": "2093-3", "value": "245", "unit": "mg/dL", "reference_range": "125-200", "flag": "above"},
            {"test_name": "LDL Cholesterol", "loinc_code": "2089-1", "value": "160", "unit": "mg/dL", "reference_range": "0-100", "flag": "above"},
            {"test_name": "HDL Cholesterol", "loinc_code": "2085-9", "value": "38", "unit": "mg/dL", "reference_range": "40-60", "flag": "below"},
            {"test_name": "Triglycerides", "loinc_code": "2571-8", "value": "210", "unit": "mg/dL", "reference_range": "0-150", "flag": "above"},
            {"test_name": "Creatinine", "loinc_code": "2160-0", "value": "1.1", "unit": "mg/dL", "reference_range": "0.7-1.3", "flag": "normal"},
            {"test_name": "TSH", "loinc_code": "3016-3", "value": "3.8", "unit": "mIU/L", "reference_range": "0.4-4.0", "flag": "normal"},
            {"test_name": "SGPT (ALT)", "loinc_code": "1742-6", "value": "42", "unit": "U/L", "reference_range": "7-56", "flag": "normal"},
            {"test_name": "SGOT (AST)", "loinc_code": "1920-8", "value": "38", "unit": "U/L", "reference_range": "10-40", "flag": "normal"},
            {"test_name": "Vitamin D", "loinc_code": "1989-3", "value": "18", "unit": "ng/mL", "reference_range": "30-100", "flag": "below"},
        ],
    },
    {
        "lab_name": "Thyrocare Technologies",
        "days_ago": 45,
        "tests": [
            {"test_name": "Hemoglobin", "loinc_code": "718-7", "value": "14.5", "unit": "g/dL", "reference_range": "13.0-17.0", "flag": "normal"},
            {"test_name": "Fasting Glucose", "loinc_code": "1558-6", "value": "132", "unit": "mg/dL", "reference_range": "70-100", "flag": "above"},
            {"test_name": "HbA1c", "loinc_code": "4548-4", "value": "6.9", "unit": "%", "reference_range": "4.0-5.6", "flag": "above"},
            {"test_name": "Total Cholesterol", "loinc_code": "2093-3", "value": "238", "unit": "mg/dL", "reference_range": "125-200", "flag": "above"},
            {"test_name": "LDL Cholesterol", "loinc_code": "2089-1", "value": "155", "unit": "mg/dL", "reference_range": "0-100", "flag": "above"},
            {"test_name": "HDL Cholesterol", "loinc_code": "2085-9", "value": "40", "unit": "mg/dL", "reference_range": "40-60", "flag": "normal"},
            {"test_name": "Triglycerides", "loinc_code": "2571-8", "value": "195", "unit": "mg/dL", "reference_range": "0-150", "flag": "above"},
            {"test_name": "Creatinine", "loinc_code": "2160-0", "value": "1.0", "unit": "mg/dL", "reference_range": "0.7-1.3", "flag": "normal"},
            {"test_name": "TSH", "loinc_code": "3016-3", "value": "4.5", "unit": "mIU/L", "reference_range": "0.4-4.0", "flag": "above"},
            {"test_name": "Vitamin D", "loinc_code": "1989-3", "value": "15", "unit": "ng/mL", "reference_range": "30-100", "flag": "below"},
        ],
    },
    {
        "lab_name": "Apollo Diagnostics",
        "days_ago": 90,
        "tests": [
            {"test_name": "Hemoglobin", "loinc_code": "718-7", "value": "13.8", "unit": "g/dL", "reference_range": "13.0-17.0", "flag": "normal"},
            {"test_name": "Fasting Glucose", "loinc_code": "1558-6", "value": "118", "unit": "mg/dL", "reference_range": "70-100", "flag": "above"},
            {"test_name": "HbA1c", "loinc_code": "4548-4", "value": "6.4", "unit": "%", "reference_range": "4.0-5.6", "flag": "above"},
            {"test_name": "Total Cholesterol", "loinc_code": "2093-3", "value": "220", "unit": "mg/dL", "reference_range": "125-200", "flag": "above"},
            {"test_name": "LDL Cholesterol", "loinc_code": "2089-1", "value": "142", "unit": "mg/dL", "reference_range": "0-100", "flag": "above"},
            {"test_name": "HDL Cholesterol", "loinc_code": "2085-9", "value": "44", "unit": "mg/dL", "reference_range": "40-60", "flag": "normal"},
            {"test_name": "Triglycerides", "loinc_code": "2571-8", "value": "175", "unit": "mg/dL", "reference_range": "0-150", "flag": "above"},
            {"test_name": "Creatinine", "loinc_code": "2160-0", "value": "0.9", "unit": "mg/dL", "reference_range": "0.7-1.3", "flag": "normal"},
            {"test_name": "TSH", "loinc_code": "3016-3", "value": "3.2", "unit": "mIU/L", "reference_range": "0.4-4.0", "flag": "normal"},
            {"test_name": "Vitamin D", "loinc_code": "1989-3", "value": "22", "unit": "ng/mL", "reference_range": "30-100", "flag": "below"},
        ],
    },
]


async def cleanup_demo_data(db, owner_id):
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


async def seed_demo_documents(db, owner_id, profile_id):
    """Create 3 demo lab reports with realistic Indian lab data.

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

    for report in SEED_REPORTS:
        doc_id = uuid.uuid4()
        ext_id = uuid.uuid4()
        report_date = now - timedelta(days=report["days_ago"])

        # Document
        doc = Document(
            document_id=doc_id,
            owner_id=owner_id,
            profile_id=profile_id,
            source="upload",
            mime_type="application/pdf",
            byte_size=245000,
            page_count=2,
            s3_key=f"demo/{doc_id}.pdf",
            sha256=f"demo_{doc_id}_sha256",
            classified_as="lab_report",
            classification_confidence=0.96,
            document_date=report_date.date(),
            provider_name=report["lab_name"],
        )
        db.add(doc)

        # Extraction
        ext = Extraction(
            extraction_id=ext_id,
            document_id=doc_id,
            owner_id=owner_id,
            profile_id=profile_id,
            model_version="parrotlet-v-lite-4b",
            schema_version="1.0",
            json_payload={
                "tests": report["tests"],
                "lab_name": report["lab_name"],
                "report_date": report_date.strftime("%Y-%m-%d"),
                "patient_name": "Demo User",
            },
            validation_flags=[],
            is_current=True,
        )
        db.add(ext)

        # Lab values
        for test in report["tests"]:
            ref_parts = test["reference_range"].split("-")
            ref_low = float(ref_parts[0]) if len(ref_parts) == 2 else None
            ref_high = float(ref_parts[1]) if len(ref_parts) == 2 else None

            lv = LabValue(
                owner_id=owner_id,
                profile_id=profile_id,
                document_id=doc_id,
                extraction_id=ext_id,
                test_name=test["test_name"],
                loinc_code=test["loinc_code"],
                value_num=float(test["value"]),
                value_text=test["value"],
                unit=test["unit"],
                ref_low=ref_low,
                ref_high=ref_high,
                flag=test["flag"],
                observed_at=report_date,
            )
            db.add(lv)

        # Timeline event
        flagged = [t for t in report["tests"] if t["flag"] != "normal"]
        timeline = TimelineEvent(
            owner_id=owner_id,
            profile_id=profile_id,
            event_type="lab",
            title="Lab Report uploaded",
            subtitle=report["lab_name"],
            provider=report["lab_name"],
            occurred_at=report_date,
            source_ref=doc_id,
            source_ref_type="document",
            flags=[
                {"text": f"{t['test_name']} {t['value']} {t['unit']}", "severity": t["flag"]}
                for t in flagged[:4]
            ],
        )
        db.add(timeline)

        logger.info("Demo seed: created %s report (%s)", report["lab_name"], doc_id)

    logger.info("Demo seed complete: 3 lab reports, 0 prescriptions")


# Alias for backward compatibility
seed_demo_data = seed_demo_documents
