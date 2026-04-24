"""Mock AI service — realistic responses for Days 1-3 before XQZ's endpoint goes live.

Used when AI_SERVICE_BASE_URL is empty in .env.

IMPORTANT: Mock responses must NOT mention specific medications unless
prescription data is passed in context. The seed data only includes lab
reports — no prescriptions.
"""
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# --- Mock lab report extraction (realistic Indian lab report) ---
MOCK_LAB_TESTS = [
    {"test_name": "Hemoglobin", "loinc_code": "718-7", "value_num": 13.2, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0, "flag": "ok"},
    {"test_name": "Fasting Blood Glucose", "loinc_code": "1558-6", "value_num": 118, "unit": "mg/dL", "ref_low": 70, "ref_high": 100, "flag": "watch"},
    {"test_name": "HbA1c", "loinc_code": "4548-4", "value_num": 6.8, "unit": "%", "ref_low": 4.0, "ref_high": 5.6, "flag": "watch"},
    {"test_name": "Total Cholesterol", "loinc_code": "2093-3", "value_num": 228, "unit": "mg/dL", "ref_low": 0, "ref_high": 200, "flag": "watch"},
    {"test_name": "LDL Cholesterol", "loinc_code": "2089-1", "value_num": 152, "unit": "mg/dL", "ref_low": 0, "ref_high": 100, "flag": "flag"},
    {"test_name": "HDL Cholesterol", "loinc_code": "2085-9", "value_num": 42, "unit": "mg/dL", "ref_low": 40, "ref_high": 60, "flag": "ok"},
    {"test_name": "Triglycerides", "loinc_code": "2571-8", "value_num": 178, "unit": "mg/dL", "ref_low": 0, "ref_high": 150, "flag": "watch"},
    {"test_name": "Creatinine", "loinc_code": "2160-0", "value_num": 1.0, "unit": "mg/dL", "ref_low": 0.7, "ref_high": 1.3, "flag": "ok"},
    {"test_name": "TSH", "loinc_code": "3016-3", "value_num": 4.8, "unit": "mIU/L", "ref_low": 0.4, "ref_high": 4.0, "flag": "watch"},
    {"test_name": "SGPT (ALT)", "loinc_code": "1742-6", "value_num": 32, "unit": "U/L", "ref_low": 0, "ref_high": 40, "flag": "ok"},
    {"test_name": "SGOT (AST)", "loinc_code": "1920-8", "value_num": 28, "unit": "U/L", "ref_low": 0, "ref_high": 40, "flag": "ok"},
    {"test_name": "Vitamin D (25-OH)", "loinc_code": "1989-3", "value_num": 18, "unit": "ng/mL", "ref_low": 30, "ref_high": 100, "flag": "flag"},
]

MOCK_PRESCRIPTION = [
    {"drug_name": "Atorvastatin", "dose": "10mg", "frequency": "0-0-1", "duration": "90 days", "route": "oral"},
    {"drug_name": "Metformin", "dose": "500mg", "frequency": "1-0-1", "duration": "90 days", "route": "oral"},
    {"drug_name": "Vitamin D3", "dose": "60000 IU", "frequency": "weekly x 8", "duration": "8 weeks", "route": "oral"},
]

MOCK_SMART_REPORT_MD = """## Cardiovascular

Your recent lipid panel shows total cholesterol at **228 mg/dL** (above the typical range of <200) and LDL cholesterol at **152 mg/dL** (above the typical range of <100). HDL cholesterol is **42 mg/dL**, which is within the acceptable range but toward the lower end. Triglycerides are **178 mg/dL** (above the typical range of <150).

Given that LDL remains above target, discuss management options with your doctor at the next visit.

## Liver

SGPT (ALT) at **32 U/L** and SGOT (AST) at **28 U/L** are both within the typical range. No concerns noted. Continue monitoring periodically.

## Renal

Creatinine at **1.0 mg/dL** is within the typical range. Kidney function appears normal based on available data. eGFR is estimated at >90 mL/min (normal).

## Metabolic

Fasting glucose at **118 mg/dL** and HbA1c at **6.8%** indicate pre-diabetic to early diabetic range. Consistent dietary management and regular monitoring are recommended. Discuss treatment options with your doctor.

## Inflammatory

No CRP, ESR, or ferritin values available in recent reports. Consider adding these to your next panel for a more complete picture.

## Hormonal

TSH at **4.8 mIU/L** is mildly above the typical range (0.4\u20134.0). This may indicate subclinical hypothyroidism. A repeat TSH with free T3/T4 is recommended to confirm before initiating treatment.

Vitamin D at **18 ng/mL** is below the sufficient range (30\u2013100). Consider supplementation and recheck in 8-12 weeks."""

MOCK_SMART_REPORT_SECTIONS = [
    {"system": "cardiovascular", "status": "watch", "key_values": [
        {"name": "Total Cholesterol", "value": "228 mg/dL", "flag": "watch"},
        {"name": "LDL Cholesterol", "value": "152 mg/dL", "flag": "flag"},
        {"name": "HDL Cholesterol", "value": "42 mg/dL", "flag": "ok"},
        {"name": "Triglycerides", "value": "178 mg/dL", "flag": "watch"},
    ]},
    {"system": "liver", "status": "ok", "key_values": [
        {"name": "SGPT (ALT)", "value": "32 U/L", "flag": "ok"},
        {"name": "SGOT (AST)", "value": "28 U/L", "flag": "ok"},
    ]},
    {"system": "renal", "status": "ok", "key_values": [
        {"name": "Creatinine", "value": "1.0 mg/dL", "flag": "ok"},
    ]},
    {"system": "metabolic", "status": "watch", "key_values": [
        {"name": "Fasting Glucose", "value": "118 mg/dL", "flag": "watch"},
        {"name": "HbA1c", "value": "6.8 %", "flag": "watch"},
    ]},
    {"system": "inflammatory", "status": "ok", "key_values": []},
    {"system": "hormonal", "status": "watch", "key_values": [
        {"name": "TSH", "value": "4.8 mIU/L", "flag": "watch"},
        {"name": "Vitamin D", "value": "18 ng/mL", "flag": "flag"},
    ]},
]

MOCK_EXPLANATION_MD = """### Understanding Your Lab Report

**Blood Sugar:** Your fasting glucose (118 mg/dL) and HbA1c (6.8%) suggest your blood sugar levels are above the typical range. HbA1c reflects your average blood sugar over the past 2-3 months. The typical range is below 5.7%; values between 5.7-6.4% suggest pre-diabetes, and above 6.5% suggest diabetes. Discuss treatment options with your doctor.

**Cholesterol Panel:** Your LDL (\u201cbad\u201d) cholesterol at 152 mg/dL is above the recommended level of below 100 mg/dL. While your HDL (\u201cgood\u201d) cholesterol at 42 is acceptable, higher would be better. Triglycerides at 178 are also above the typical range of below 150. Discuss lipid management strategies with your doctor.

**Thyroid:** TSH at 4.8 is slightly above the typical upper limit of 4.0. This could indicate your thyroid is working slightly harder than usual. A follow-up test including free T3 and T4 levels would provide a clearer picture.

**Vitamin D:** At 18 ng/mL, your vitamin D is below the sufficient level of 30. Consider vitamin D supplementation and recheck in 8-12 weeks.

**Liver & Kidney:** Both are within the typical range. No immediate concerns.

> *This explanation is AI-generated for educational purposes. Always discuss your results with your doctor for personalized medical advice.*"""

MOCK_TIMELINE_SUMMARY_MD = """## Health Timeline Summary

### Key Findings
- Pre-diabetic / early diabetic range (Fasting Glucose 118 mg/dL, HbA1c 6.8%)
- Dyslipidemia (LDL 152, Total Cholesterol 228, Triglycerides 178 mg/dL)
- Vitamin D deficiency (18 ng/mL \u2014 below sufficient range of 30-100)
- Mildly elevated TSH (4.8 mIU/L \u2014 possible subclinical hypothyroidism)

### Current Medications
No prescriptions uploaded yet. Upload a prescription to track your medications here.

### Recent Lab Results
- Fasting glucose 118 mg/dL \u2014 above typical range (70-100)
- HbA1c 6.8% \u2014 above typical range (<5.7%)
- LDL Cholesterol 152 mg/dL \u2014 above target (<100)
- Vitamin D 18 ng/mL \u2014 below sufficient (>30)

### Health Risks to Monitor
- **Cardiovascular:** LDL and total cholesterol remain above target. Discuss lipid management with your doctor.
- **Metabolic:** HbA1c in diabetic range \u2014 consider dietary changes and medical consultation.
- **Thyroid:** Subclinical hypothyroidism may be present. Confirm with free T3/T4 testing.

### Recommended Follow-ups
1. Repeat lipid panel in 3 months
2. TSH + free T3/T4 to evaluate thyroid status
3. Vitamin D recheck after 8-12 weeks of supplementation
4. Regular BP monitoring \u2014 consider home BP device"""


async def mock_classify(document_id: str, image_urls: list[str]) -> dict:
    logger.info("MOCK: classify document %s", document_id)
    return {
        "class": "lab_report",
        "confidence": 0.94,
        "per_page_class": ["lab_report"] * len(image_urls),
        "model_version": "mock-v1",
        "latency_ms": 120,
    }


async def mock_extract(document_id: str, image_urls: list[str], document_class: str, patient_context: dict | None = None) -> dict:
    logger.info("MOCK: extract document %s (class=%s)", document_id, document_class)
    if document_class == "prescription":
        return {
            "document_id": document_id,
            "schema_version": "v1",
            "extraction": {
                "medications": MOCK_PRESCRIPTION,
                "prescribed_by": "Dr. Suresh Reddy",
                "prescribed_at": "2026-03-15",
            },
            "validation_flags": [],
            "model_version": "mock-v1",
        }
    # Default: lab report
    return {
        "document_id": document_id,
        "schema_version": "v1",
        "extraction": {
            "tests": MOCK_LAB_TESTS,
            "lab_name": "Sample Laboratory",
            "report_date": "2026-04-10",
            "patient_name": "Demo User",
        },
        "validation_flags": [],
        "model_version": "mock-v1",
    }


async def mock_explain(document_id: str, structured_extraction: dict, patient_profile: dict | None = None) -> dict:
    logger.info("MOCK: explain document %s", document_id)
    return {
        "explanation_markdown": MOCK_EXPLANATION_MD,
        "critical_flags": [],
        "urgency": "routine",
        "model_version": "mock-v1",
    }


async def mock_ask(question: str, context_documents: list[dict]) -> dict:
    logger.info("MOCK: ask '%s'", question[:80])
    # Check for refused questions
    refused_keywords = ["dangerous", "should i worry", "am i going to die", "fatal", "serious"]
    is_refused = any(kw in question.lower() for kw in refused_keywords)

    if is_refused:
        return {
            "answer_markdown": "I understand your concern. I can share what your reports show, but I'm not able to assess whether something is dangerous or provide a clinical judgment. Your doctor is the best person to interpret these findings in the context of your overall health.\n\n> Please consult your doctor for medical advice.",
            "intent": "clinical_interpretation",
            "refused": True,
            "critical_flag": False,
            "citations": [],
            "disclaimer_appended": True,
            "model_version": "mock-v1",
        }

    return {
        "answer_markdown": f"Based on your recent lab reports, here is what I found regarding your question:\n\nYour most recent HbA1c was **6.8%** (recorded April 2026), which is above the typical range of <5.7%. Three months prior, it was **6.4%**. This shows a slight upward trend.\n\nYour fasting glucose was **118 mg/dL**, also above the typical fasting range of 70-100 mg/dL.\n\nDiscuss management options with your doctor based on these trends. [1]\n\n> *This information is from your health records and is not medical advice.*",
        "intent": "factual_retrieval",
        "refused": False,
        "critical_flag": False,
        "citations": [
            {"index": 1, "document_id": "demo-doc-001", "excerpt": "HbA1c: 6.8%, Fasting Glucose: 118 mg/dL", "date": "2026-04-10"}
        ],
        "disclaimer_appended": True,
        "model_version": "mock-v1",
    }


async def mock_summarize(report_type: str, context_data: dict) -> dict:
    logger.info("MOCK: summarize type=%s", report_type)
    if report_type == "timeline_summary":
        return {
            "report_markdown": MOCK_TIMELINE_SUMMARY_MD,
            "sections": [],
            "model_version": "mock-v1",
        }
    return {
        "report_markdown": MOCK_SMART_REPORT_MD,
        "sections": MOCK_SMART_REPORT_SECTIONS,
        "model_version": "mock-v1",
    }


async def mock_transcribe(audio_url: str) -> dict:
    logger.info("MOCK: transcribe %s", audio_url)
    return {
        "transcript": "Feeling more fatigued lately. Started noticing it about two weeks ago. Sleep has been okay but energy levels drop after lunch. Might be thyroid related.",
        "confidence": 0.92,
        "duration_sec": 18.5,
        "model_version": "mock-v1",
    }


async def mock_embed(texts: list[str]) -> dict:
    logger.info("MOCK: embed %d texts", len(texts))
    # Return dummy 1024-dim embeddings
    return {
        "embeddings": [[0.01] * 1024 for _ in texts],
        "dimensions": 1024,
        "model_version": "mock-v1",
    }


async def mock_health() -> dict:
    return {
        "status": "ok",
        "models_loaded": ["mock-classifier", "mock-extractor", "mock-explainer"],
        "gpu_utilization": 0.0,
    }
