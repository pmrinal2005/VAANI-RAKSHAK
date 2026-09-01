# ==============================================================================
# VAANI-RAKSHAK — Enterprise Security Headers & Request Size Limiting
# Defense-in-depth HTTP security headers and early rejection of oversized payloads.
# ==============================================================================

from __future__ import annotations

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import Settings, get_settings

logger = structlog.get_logger(__name__)


# Content-Security-Policy directives
# Production: Highly restrictive policy for pure JSON/WebSocket APIs
PROD_CSP = "default-src 'none'; frame-ancestors 'none'"

# Development: Permits resources required by FastAPI's interactive Swagger UI and ReDoc
DEV_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net; "
    "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net data:; "
    "connect-src 'self'; "
    "worker-src 'self' blob:; "
    "frame-ancestors 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies standard enterprise security headers to all HTTP responses,
    including error responses.
    """

    def __init__(self, app: ASGIApp, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # Standard defense-in-depth headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            DEV_CSP if self.settings.is_development else PROD_CSP
        )
        response.headers["X-XSS-Protection"] = "0"  # Modern standard disables legacy buggy filter

        # HSTS is only active when explicitly enabled behind TLS/HTTPS
        if self.settings.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Early rejection mechanism for oversized HTTP payloads.
    Guards memory against DoS attacks before buffering requests into memory.
    """

    def __init__(self, app: ASGIApp, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()
        self.max_size_bytes = self.settings.max_request_size_mb * 1024 * 1024

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        content_length_str = request.headers.get("content-length")

        if content_length_str:
            try:
                content_length = int(content_length_str)
                if content_length > self.max_size_bytes:
                    logger.warning(
                        "security.request_too_large",
                        declared_length=content_length,
                        max_allowed=self.max_size_bytes,
                        path=request.url.path,
                        client=request.client.host if request.client else "unknown",
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": (
                                    f"Request payload ({content_length} bytes) exceeds "
                                    f"the maximum allowed size of "
                                    f"{self.settings.max_request_size_mb}MB."
                                ),
                            }
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)
