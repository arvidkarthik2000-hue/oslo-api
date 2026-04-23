"""Demo data seeder — populates the database with realistic Indian health records.

Called automatically when a new demo user is created via /auth/dev-create.
Matches the mobile seed data so both sides stay in sync.
"""
import uuid
import logging
from datetime import datetime, timezone, date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.document import Document
from app.models.extraction import Extraction
from app.models.lab_value import LabValue
from app.models.prescription import Prescription
from app.models.timeline_event import TimelineEvent

logger = logging.getLogger(__name__)

SEED_DATA = [
    {
        "classified_as": "lab_report",
        "provider_name": "Dr Lal PathLabs",
        "document_date": date(2025, 10, 15),
        "tests": [
            {"test_name": "Hemoglobin", "value_num": 13.8, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.5, "flag": "ok", "loinc_code": "718-7"},
            {"test_name": "Fasting Glucose", "value_num": 112, "unit": "mg/dL", "ref_low": 70, "ref_high": 100, "flag": "watch", "loinc_code": "1558-6"},
            {"test_name": "HbA1c", "value_num": 6.8, "unit": "%", "ref_low": 4.0, "ref_high": 5.6, "flag": "watch", "loinc_code": "4548-4"},
            {"test_name": "Total Cholesterol", "value_num": 228, "unit": "mg/dL", "ref_low": 0, "ref_high": 200, "flag": "watch", "loinc_code": "2093-3"},
            {"test_name": "LDL Cholesterol", "value_num": 148, "unit": "mg/dL", "ref_low": 0, "ref_high": 100, "flag": "flag", "loinc_code": "2089-1"},
            {"test_name": "HDL Cholesterol", "value_num": 42, "unit": "mg/dL", "ref_low": 40, "ref_high": 60, "flag": "ok", "loinc_code": "2085-9"},
            {"test_name": "Creatinine", "value_num": 0.9, "unit": "mg/dL", "ref_low": 0.7, "ref_high": 1.3, "flag": "ok", "loinc_code": "2160-0"},
            {"test_name": "TSH", "value_num": 3.2, "unit": "mIU/L", "ref_low": 0.4, "ref_high": 4.0, "flag": "ok", "loinc_code": "3016-3"},
        ],
    },
    {
        "classified_as": "lab_report",
        "provider_name": "Thyrocare Technologies",
        "document_date": date(2026, 1, 10),
        "tests": [
            {"test_name": "Hemoglobin", "value_num": 14.1, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.5, "flag": "ok", "loinc_code": "718-7"},
            {"test_name": "Fasting Glucose", "value_num": 118, "unit": "mg/dL", "ref_low": 70, "ref_high": 100, "flag": "watch", "loinc_code": "1558-6"},
            {"test_name": "HbA1c", "value_num": 7.1, "unit": "%", "ref_low": 4.0, "ref_high": 5.6, "flag": "flag", "loinc_code": "4548-4"},
            {"test_name": "Total Cholesterol", "value_num": 215, "unit": "mg/dL", "ref_low": 0, "ref_high": 200, "flag": "watch", "loinc_code": "2093-3"},
            {"test_name": "LDL Cholesterol", "value_num": 132, "unit": "mg/dL", "ref_low": 0, "ref_high": 100, "flag": "flag", "loinc_code": "2089-1"},
            {"test_name": "HDL Cholesterol", "value_num": 44, "unit": "mg/dL", "ref_low": 40, "ref_high": 60, "flag": "ok", "loinc_code": "2085-9"},
            {"test_name": "Triglycerides", "value_num": 195, "unit": "mg/dL", "ref_low": 0, "ref_high": 150, "flag": "watch", "loinc_code": "2571-8"},
            {"test_name": "SGPT (ALT)", "value_num": 34, "unit": "U/L", "ref_low": 7, "ref_high": 56, "flag": "ok", "loinc_code": "1742-6"},
            {"test_name": "Vitamin D", "value_num": 18, "unit": "ng/mL", "ref_low": 30, "ref_high": 100, "flag": "flag", "loinc_code": "1989-3"},
        ],
    },
    {
        "classified_as": "lab_report",
        "provider_name": "Apollo Diagnostics",
        "document_date": date(2026, 4, 5),
        "tests": [
            {"test_name": "Hemoglobin", "value_num": 13.5, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.5, "flag": "ok", "loinc_code": "718-7"},
            {"test_name": "Fasting Glucose", "value_num": 126, "unit": "mg/dL", "ref_low": 70, "ref_high": 100, "flag": "flag", "loinc_code": "1558-6"},
            {"test_name": "HbA1c", "value_num": 7.8, "unit": "%", "ref_low": 4.0, "ref_high": 5.6, "flag": "flag", "loinc_code": "4548-4"},
            {"test_name": "Total Cholesterol", "value_num": 198, "unit": "mg/dL", "ref_low": 0, "ref_high": 200, "flag": "ok", "loinc_code": "2093-3"},
            {"test_name": "LDL Cholesterol", "value_num": 118, "unit": "mg/dL", "ref_low": 0, "ref_high": 100, "flag": "watch", "loinc_code": "2089-1"},
            {"test_name": "Creatinine", "value_num": 1.0, "unit": "mg/dL", "ref_low": 0.7, "ref_high": 1.3, "flag": "ok", "loinc_code": "2160-0"},
            {"test_name": "TSH", "value_num": 4.8, "unit": "mIU/L", "ref_low": 0.4, "ref_high": 4.0, "flag": "watch", "loinc_code": "3016-3"},
            {"test_name": "SGPT (ALT)", "value_num": 42, "unit": "U/L", "ref_low": 7, "ref_high": 56, "flag": "ok", "loinc_code": "1742-6"},
            {"test_name": "SGOT (AST)", "value_num": 38, "unit": "U/L", "ref_low": 5, "ref_high": 40, "flag": "ok", "loinc_code": "1920-8"},
            {"test_name": "Vitamin D", "value_num": 24, "unit": "ng/mL", "ref_low": 30, "ref_high": 100, "flag": "watch", "loinc_code": "1989-3"},
        ],
    },
    {
        "classified_as": "prescription",
        "provider_name": "Dr. S. Krishnan, MD (Gen Med)",
        "document_date": date(2025, 11, 1),
        "medications": [
            {"drug_name": "Atorvastatin", "dose": "10mg", "frequency": "0-0-1", "duration": "Ongoing"},
            {"drug_name": "Metformin", "dose": "500mg", "frequency": "1-0-1", "duration": "Ongoing"},
        ],
    },
    {
        "classified_as": "prescription",
        "provider_name": "Dr. S. Krishnan, MD (Gen Med)",
        "document_date": date(2026, 1, 15),
        "medications": [
            {"drug_name": "Atorvastatin", "dose": "10mg", "frequency": "0-0-1", "duration": "Ongoing"},
            {"drug_name": "Metformin", "dose": "500mg", "frequency": "1-0-1", "duration": "Ongoing"},
            {"drug_name": "Vitamin D3", "dose": "60000 IU", "frequency": "Weekly", "duration": "8 weeks"},
        ],
    },
]


async def seed_demo_data(
    db: AsyncSession, owner_id: uuid.UUID, profile_id: uuid.UUID
) -> int:
    """Insert demo documents, lab values, prescriptions, and timeline events.

    Idempotent: skips if documents already exist for this owner.
    Returns the number of documents seeded.
    """
    count = (
        await db.execute(
            select(func.count()).select_from(Document).where(
                Document.owner_id == owner_id
            )
        )
    ).scalar() or 0
    if count > 0:
        logger.info("Demo data already exists for %s (%d docs), skipping", owner_id, count)
        return 0

    event_type_map = {
        "lab_report": "lab",
        "prescription": "prescription",
    }

    seeded = 0
    for seed in SEED_DATA:
        doc_date = seed["document_date"]
        occurred_at = datetime.combine(
            doc_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)

        # --- Document ---
        doc = Document(
            owner_id=owner_id,
            profile_id=profile_id,
            source="demo_seed",
            mime_type="application/pdf",
            byte_size=0,
            page_count=1,
            s3_key=f"demo/{seed['provider_name'].replace(' ', '_')}_{doc_date.isoformat()}.pdf",
            sha256=f"demo-{seeded}",
            classified_as=seed["classified_as"],
            classification_confidence=0.99,
            document_date=doc_date,
            provider_name=seed["provider_name"],
        )
        db.add(doc)
        await db.flush()

        # --- Extraction ---
        if seed["classified_as"] == "lab_report":
            json_payload = {
                "report_date": doc_date.isoformat(),
                "lab_name": seed["provider_name"],
                "tests": seed["tests"],
            }
        else:
            json_payload = {
                "report_date": doc_date.isoformat(),
                "prescribed_by": seed["provider_name"],
                "medications": seed["medications"],
            }

        extraction = Extraction(
            document_id=doc.document_id,
            owner_id=owner_id,
            profile_id=profile_id,
            model_version="demo-seed",
            schema_version="v1",
            json_payload=json_payload,
            is_current=True,
        )
        db.add(extraction)
        await db.flush()

        # --- Lab Values / Prescriptions ---
        if seed["classified_as"] == "lab_report":
            for test in seed["tests"]:
                lv = LabValue(
                    owner_id=owner_id,
                    profile_id=profile_id,
                    document_id=doc.document_id,
                    extraction_id=extraction.extraction_id,
                    test_name=test["test_name"],
                    loinc_code=test.get("loinc_code"),
                    value_num=test["value_num"],
                    value_text=str(test["value_num"]),
                    unit=test["unit"],
                    ref_low=test["ref_low"],
                    ref_high=test["ref_high"],
                    observed_at=occurred_at,
                    flag=test.get("flag", "ok"),
                )
                db.add(lv)
        else:
            rx = Prescription(
                owner_id=owner_id,
                profile_id=profile_id,
                document_id=doc.document_id,
                prescribed_by=seed["provider_name"],
                prescribed_at=doc_date,
                items=seed["medications"],
                active=True,
                source="demo_seed",
            )
            db.add(rx)

        # --- Timeline Event ---
        evt_type = event_type_map.get(seed["classified_as"], "note")
        title = f"{seed['classified_as'].replace('_', ' ').title()} uploaded"

        # Build flags for lab reports
        flags = None
        if seed["classified_as"] == "lab_report":
            flag_items = [
                {"text": f"{t['test_name']} {t['value_num']}", "severity": t["flag"]}
                for t in seed["tests"]
                if t.get("flag") in ("watch", "flag", "critical")
            ][:3]
            if flag_items:
                flags = flag_items

        timeline = TimelineEvent(
            owner_id=owner_id,
            profile_id=profile_id,
            event_type=evt_type,
            occurred_at=occurred_at,
            source_ref=doc.document_id,
            source_ref_type="document",
            title=title,
            subtitle=seed["provider_name"],
            provider=seed["provider_name"],
            flags=flags,
        )
        db.add(timeline)
        seeded += 1

    logger.info("Seeded %d demo documents for owner %s", seeded, owner_id)
    return seeded
