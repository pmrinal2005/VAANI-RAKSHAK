# ==============================================================================
# VAANI-RAKSHAK — FastAPI Application Factory
#
# Architecture:
#   API layer (routes) → Application services → Domain/Orchestration
#               → Interfaces → Adapters → External systems
#
# The frontend is a separate Vite/React application (port 5173 in dev).
# This backend serves only REST + WebSocket — no static file serving here.
# ==============================================================================

from __future__ import annotations

import uuid
from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import audit, calls, score, streaming
from app.api.routes import health as health_router
from app.core.config import get_settings
from app.core.exceptions import VaaniError
from app.core.lifecycle import lifespan
from app.core.profiling import ProfilingMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.core.security import RequestSizeLimitMiddleware, SecurityHeadersMiddleware

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    """
    Application factory.

    Returns a fully-configured FastAPI application instance.
    All configuration is sourced from Settings (environment variables).
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "VAANI-RAKSHAK R2 — Real-time voice-cloning detection backend. "
            "Modular, async-first pipeline with cascade orchestration, "
            "Kafka event streaming, and clean R1/R4 integration interfaces."
        ),
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        lifespan=lifespan,
    )

    # --------------------------------------------------------------------------
    # Middleware — deliberate execution order (outermost first)
    # --------------------------------------------------------------------------

    # 1. Security Headers (outermost — ensures all responses contain defense-in-depth headers)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)

    # 2. Performance & Latency Profiling (measures total request duration)
    app.add_middleware(ProfilingMiddleware, settings=settings)

    # 3. Request Body Size Limiter (rejects oversized HTTP payloads before memory buffering)
    app.add_middleware(RequestSizeLimitMiddleware, settings=settings)

    # 4. Token Bucket Rate Limiter (rejects brute-force/DoS before expensive routing)
    app.add_middleware(RateLimitMiddleware, settings=settings)

    # 5. Trusted Host — prevents HTTP Host header injection (non-dev environments)
    if not settings.is_development:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # Tighten per deployment environment
        )

    # 6. CORS — allow the Vite dev server and production frontend origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Trace-ID", "X-Response-Time", "Server-Timing"],
    )

    # 7. Request ID middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Any) -> Any:  # noqa: ANN401
        """Attach a unique request ID to every request and response."""
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # --------------------------------------------------------------------------
    # Exception handlers
    # --------------------------------------------------------------------------

    @app.exception_handler(VaaniError)
    async def vaani_error_handler(
        request: Request,
        exc: VaaniError,
    ) -> JSONResponse:
        """Map VaaniError subclasses to structured JSON error responses."""
        logger.warning(
            "request.error",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
        )
        body: dict[str, Any] = {
            "error": {
                "code": exc.error_code,
                "message": exc.message,
            }
        }
        if settings.is_development and exc.detail:
            body["error"]["detail"] = exc.detail

        return JSONResponse(
            content=body,
            status_code=exc.status.value,
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Catch-all handler — never expose stack traces to external callers."""
        logger.exception(
            "request.unhandled_error",
            path=request.url.path,
            exc_type=type(exc).__name__,
        )
        return JSONResponse(
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                }
            },
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        )

    # --------------------------------------------------------------------------
    # Routers
    # --------------------------------------------------------------------------

    prefix = settings.api_prefix

    app.include_router(health_router.router, prefix=prefix)
    app.include_router(score.router, prefix=prefix)
    app.include_router(streaming.router, prefix=prefix)
    app.include_router(calls.router, prefix=prefix)
    app.include_router(audit.router, prefix=prefix)

    # --------------------------------------------------------------------------
    # Root redirect
    # --------------------------------------------------------------------------

    @app.get("/", include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse(
            content={
                "service": settings.app_name,
                "version": settings.app_version,
                "docs": f"{prefix}/docs",
                "health": f"{prefix}/health",
            }
        )

    return app


# Module-level app instance for uvicorn / gunicorn
app = create_app()
