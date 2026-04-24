"""AI Service client — calls XQZ's AI endpoints or falls back to mocks.

Config: if AI_SERVICE_BASE_URL is empty, uses mock responses.
Once XQZ sets the real URL on Day 3, mocks auto-disable.
"""
import httpx
import logging
from typing import Any

from app.config import get_settings
from app.services import ai_service_mock as mock

logger = logging.getLogger(__name__)
settings = get_settings()

_TIMEOUT = 90.0  # seconds (Gemma 4 can take 60s on cold start)
_USE_MOCK = not settings.ai_service_base_url or settings.ai_service_base_url == "https://oslo-ai.example.com"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.ai_service_api_key}",
        "Content-Type": "application/json",
    }


async def _post(path: str, payload: dict, timeout: float = _TIMEOUT) -> dict:
    """POST to AI service with error handling."""
    url = f"{settings.ai_service_base_url}{path}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=_headers(), timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.error("AI service timeout: %s", path)
            raise AIServiceError(f"AI service timed out on {path}")
        except httpx.HTTPStatusError as e:
            logger.error("AI service error %s: %s", e.response.status_code, e.response.text[:200])
            raise AIServiceError(f"AI service returned {e.response.status_code}")
        except httpx.ConnectError:
            logger.error("AI service unreachable: %s", url)
            raise AIServiceError("AI service unreachable")


class AIServiceError(Exception):
    """Raised when AI service call fails."""
    pass


# ===== Public API =====

async def classify(document_id: str, image_urls: list[str], owner_id_hash: str = "") -> dict:
    """Classify a document into lab_report / prescription / discharge_summary / etc."""
    if _USE_MOCK:
        return await mock.mock_classify(document_id, image_urls)
    return await _post("/classify", {
        "document_id": document_id,
        "image_urls": image_urls,
        "owner_id_hash": owner_id_hash,
    })


async def extract(document_id: str, image_urls: list[str], document_class: str,
                  patient_context: dict | None = None) -> dict:
    """Extract structured data from a document."""
    if _USE_MOCK:
        return await mock.mock_extract(document_id, image_urls, document_class, patient_context)
    return await _post("/extract", {
        "document_id": document_id,
        "image_urls": image_urls,
        "document_class": document_class,
        "patient_context": patient_context or {},
    })


async def explain(document_id: str, structured_extraction: dict,
                  patient_profile: dict | None = None, language: str = "en") -> dict:
    """Generate a plain-language explanation of a document."""
    if _USE_MOCK:
        return await mock.mock_explain(document_id, structured_extraction, patient_profile)
    return await _post("/explain", {
        "document_id": document_id,
        "structured_extraction": structured_extraction,
        "patient_profile": patient_profile or {},
        "language": language,
    })


async def ask(owner_id_hash: str, profile_id: str, question: str,
             context_documents: list[dict] | None = None) -> dict:
    """Answer a health question using the user's records as context."""
    if _USE_MOCK:
        return await mock.mock_ask(question, context_documents or [])
    return await _post("/ask", {
        "owner_id_hash": owner_id_hash,
        "profile_id": profile_id,
        "question": question,
        "context_documents": context_documents or [],
    })


async def summarize(owner_id_hash: str, profile_id: str, report_type: str,
                    patient_profile: dict, context_data: dict) -> dict:
    """Generate Smart Report or Timeline Summary."""
    if _USE_MOCK:
        return await mock.mock_summarize(report_type, context_data)
    return await _post("/summarize", {
        "owner_id_hash": owner_id_hash,
        "profile_id": profile_id,
        "report_type": report_type,
        "patient_profile": patient_profile,
        "context_data": context_data,
    }, timeout=60.0)  # summarize can take longer


async def transcribe(audio_url: str, language: str = "en", owner_id_hash: str = "") -> dict:
    """Transcribe an audio recording."""
    if _USE_MOCK:
        return await mock.mock_transcribe(audio_url)
    return await _post("/transcribe", {
        "audio_url": audio_url,
        "language": language,
        "owner_id_hash": owner_id_hash,
    })


async def embed(texts: list[str], model: str = "bge-m3") -> dict:
    """Generate embeddings for text chunks (used for Ask AI retrieval)."""
    if _USE_MOCK:
        return await mock.mock_embed(texts)
    return await _post("/embed", {
        "texts": texts,
        "model": model,
    })


async def check_health() -> dict:
    """Check AI service health."""
    if _USE_MOCK:
        return await mock.mock_health()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.ai_service_base_url}/health",
                headers=_headers(),
                timeout=5.0,
            )
            return resp.json()
    except Exception:
        return {"status": "unreachable", "models_loaded": [], "gpu_utilization": 0}
