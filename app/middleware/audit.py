"""Audit middleware — logs request metadata for Sentry breadcrumbs."""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import sentry_sdk

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that adds Sentry breadcrumbs and logs request timing.
    
    PII scrubbing: phone numbers, names, and dates are NOT logged.
    Only request path, method, status, and timing are recorded.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        
        # Add Sentry breadcrumb
        sentry_sdk.add_breadcrumb(
            category="http",
            message=f"{request.method} {request.url.path}",
            level="info",
        )
        
        response = await call_next(request)
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        # Log request (no PII)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 1),
            },
        )
        
        # Add timing header
        response.headers["X-Request-Duration-Ms"] = str(round(duration_ms, 1))
        
        return response
