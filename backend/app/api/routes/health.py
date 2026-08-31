# ==============================================================================
# VAANI-RAKSHAK — Health Check Routes
# Provides standard Kubernetes-compatible health probes.
#
# GET /api/v1/health        — Aggregated health with component status
# GET /api/v1/health/live   — Liveness probe (is the process alive?)
# GET /api/v1/health/ready  — Readiness probe (can the process serve traffic?)
# ==============================================================================

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Module-level start time for uptime calculation
_STARTUP_TIME: float = time.monotonic()


# ------------------------------------------------------------------------------
# Response schemas
# ------------------------------------------------------------------------------


class ComponentHealth(BaseModel):
    """Health status of a single dependency."""

    name: str
    status: str  # "healthy" | "degraded" | "unhealthy" | "not_configured"
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    """Aggregated health response."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str
    app_env: str
    timestamp: str
    uptime_seconds: float
    detection_mode: str
    components: list[ComponentHealth] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# Component health checks
# ------------------------------------------------------------------------------


async def _check_kafka() -> ComponentHealth:
    """Check Kafka / Mock event streaming broker health."""
    settings = get_settings()
    from app.core.lifecycle import get_global_producer

    prod = get_global_producer()
    if prod is not None and hasattr(prod, "is_healthy") and prod.is_healthy():
        is_mock = "MockEventProducer" in type(prod).__name__
        return ComponentHealth(
            name="kafka",
            status="healthy",
            detail=(
                "In-memory MockEventProducer operational"
                if is_mock
                else f"AIOKafka connected to {settings.kafka_bootstrap_servers}"
            ),
        )

    return ComponentHealth(
        name="kafka",
        status="not_configured" if settings.is_development else "degraded",
        detail=f"Bootstrap: {settings.kafka_bootstrap_servers}",
    )


async def _check_models() -> ComponentHealth:
    """
    Phase 1 placeholder.

    Real implementation will verify model adapter health (ONNX session alive,
    warmup inference succeeded).
    """
    settings = get_settings()
    return ComponentHealth(
        name="models",
        status="not_configured" if settings.detection_mode == "mock" else "healthy",
        detail=(
            f"detection_mode={settings.detection_mode} — mock adapters require no health check"
            if settings.detection_mode == "mock"
            else "Phase 1 — real model health check not yet implemented"
        ),
    )


async def _check_audit() -> ComponentHealth:
    """Phase 8 placeholder."""
    settings = get_settings()
    return ComponentHealth(
        name="audit_ledger",
        status="not_configured" if settings.audit_mode == "mock" else "healthy",
        detail=f"audit_mode={settings.audit_mode}",
    )


# ------------------------------------------------------------------------------
# Aggregation helper
# ------------------------------------------------------------------------------


def _aggregate_status(components: list[ComponentHealth]) -> str:
    statuses = {c.status for c in components}
    if "unhealthy" in statuses:
        return "unhealthy"
    if "degraded" in statuses:
        return "degraded"
    return "healthy"


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------


@router.get(
    "",
    summary="Aggregated health check",
    response_model=HealthResponse,
    responses={
        200: {"description": "Service is healthy or degraded"},
        503: {"description": "Service is unhealthy"},
    },
)
async def health() -> JSONResponse:
    """
    Return detailed health status including all registered component checks.

    Returns HTTP 200 for ``healthy`` and ``degraded``.
    Returns HTTP 503 for ``unhealthy``.

    Degraded state means the service is operational but at least one
    non-critical dependency is unavailable.
    """
    settings = get_settings()
    components = [
        await _check_kafka(),
        await _check_models(),
        await _check_audit(),
    ]

    agg = _aggregate_status(components)
    response_body: dict[str, Any] = HealthResponse(
        status=agg,
        version=settings.app_version,
        app_env=settings.app_env,
        timestamp=datetime.now(UTC).isoformat(),
        uptime_seconds=round(time.monotonic() - _STARTUP_TIME, 2),
        detection_mode=settings.detection_mode,
        components=components,
    ).model_dump()

    http_status = status.HTTP_503_SERVICE_UNAVAILABLE if agg == "unhealthy" else status.HTTP_200_OK

    logger.debug("health.check", overall_status=agg)
    return JSONResponse(content=response_body, status_code=http_status)


@router.get(
    "/live",
    summary="Liveness probe",
    responses={
        200: {"description": "Process is alive"},
    },
)
async def liveness() -> dict[str, str]:
    """
    Kubernetes liveness probe.

    Returns HTTP 200 as long as the process is running.
    If this endpoint is unreachable the process should be restarted.
    """
    return {"status": "alive"}


@router.get(
    "/ready",
    summary="Readiness probe",
    responses={
        200: {"description": "Service is ready to accept traffic"},
        503: {"description": "Service is not yet ready"},
    },
)
async def readiness() -> JSONResponse:
    """
    Kubernetes readiness probe.

    Returns HTTP 200 when the service is ready to serve traffic.
    Returns HTTP 503 during startup or when critical dependencies are down.

    In Phase 0, this always returns 200 (all deps are mocked).
    In later phases, this will verify Kafka connectivity and model availability.
    """
    settings = get_settings()

    # Phase 0: all dependencies are either mocked or not yet wired up.
    # The process is always ready if it's running.
    ready = True
    reason = "Phase 0 — mock mode, all dependencies satisfied"

    body = {
        "status": "ready" if ready else "not_ready",
        "detection_mode": settings.detection_mode,
        "reason": reason,
    }

    http_status = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    logger.debug("readiness.check", ready=ready, reason=reason)
    return JSONResponse(content=body, status_code=http_status)
