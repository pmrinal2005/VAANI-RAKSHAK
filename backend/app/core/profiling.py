# ==============================================================================
# VAANI-RAKSHAK — Request Latency Profiling Middleware
# Measures backend processing time, sets Server-Timing headers, & logs slow requests.
# ==============================================================================

from __future__ import annotations

import time

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class ProfilingMiddleware(BaseHTTPMiddleware):
    """
    Measures backend request processing duration using a monotonic clock.
    Injects X-Response-Time and Server-Timing headers for observability.
    """

    def __init__(self, app: ASGIApp, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        elapsed_sec = time.perf_counter() - start_time
        elapsed_ms = round(elapsed_sec * 1000.0, 2)

        # Ingest timing headers
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        response.headers["Server-Timing"] = f"total;dur={elapsed_ms}"

        # Warn if processing time exceeded configured threshold
        if elapsed_ms > self.settings.slow_request_threshold_ms:
            logger.warning(
                "performance.slow_request",
                method=request.method,
                path=request.url.path,
                elapsed_ms=elapsed_ms,
                threshold_ms=self.settings.slow_request_threshold_ms,
                status_code=response.status_code,
            )

        return response
