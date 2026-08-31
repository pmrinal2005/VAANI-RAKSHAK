# ==============================================================================
# VAANI-RAKSHAK — Application Exception Hierarchy
# Defines structured exceptions that translate cleanly to HTTP responses.
# All domain-level errors should subclass VaaniError.
# ==============================================================================

from __future__ import annotations

from http import HTTPStatus
from typing import Any


class VaaniError(Exception):
    """
    Base exception for all VAANI-RAKSHAK application errors.

    Attributes:
        message:    Human-readable error description.
        error_code: Machine-readable error identifier (e.g. "AUDIO_TOO_SHORT").
        status:     Suggested HTTP status code for API responses.
        detail:     Optional additional context (not exposed to external callers
                    in production — only included in development mode).
    """

    message: str = "An unexpected error occurred."
    error_code: str = "INTERNAL_ERROR"
    status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str | None = None,
        *,
        error_code: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.error_code = error_code or self.__class__.error_code
        self.detail = detail or {}
        super().__init__(self.message)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(error_code={self.error_code!r}, message={self.message!r})"
        )


# ------------------------------------------------------------------------------
# 400 — Bad Request
# ------------------------------------------------------------------------------


class ValidationError(VaaniError):
    """Request payload failed schema validation."""

    message = "Request validation failed."
    error_code = "VALIDATION_ERROR"
    status = HTTPStatus.BAD_REQUEST


class AudioValidationError(ValidationError):
    """Audio payload is malformed, too short, or unreadable."""

    message = "Audio validation failed."
    error_code = "AUDIO_VALIDATION_ERROR"


class AudioTooShortError(AudioValidationError):
    """Audio clip is below the minimum duration for analysis."""

    message = "Audio clip is too short for reliable analysis."
    error_code = "AUDIO_TOO_SHORT"


class AudioTooSilentError(AudioValidationError):
    """Audio clip is predominantly silence."""

    message = "Audio clip is too silent — no usable voice detected."
    error_code = "AUDIO_TOO_SILENT"


class AudioLowSnrError(AudioValidationError):
    """Audio clip has insufficient signal-to-noise ratio."""

    message = "Audio clip has insufficient signal-to-noise ratio."
    error_code = "AUDIO_LOW_SNR"


class UnsupportedCodecError(AudioValidationError):
    """Audio codec is not supported by the pipeline."""

    message = "Audio codec is not supported."
    error_code = "UNSUPPORTED_CODEC"


# ------------------------------------------------------------------------------
# 404 — Not Found
# ------------------------------------------------------------------------------


class NotFoundError(VaaniError):
    """Requested resource does not exist."""

    message = "Resource not found."
    error_code = "NOT_FOUND"
    status = HTTPStatus.NOT_FOUND


class CallNotFoundError(NotFoundError):
    """No call record found for the given call_id."""

    message = "Call not found."
    error_code = "CALL_NOT_FOUND"


# ------------------------------------------------------------------------------
# 409 — Conflict
# ------------------------------------------------------------------------------


class DuplicateRequestError(VaaniError):
    """
    Idempotency violation — the same request has already been processed.

    Callers should retrieve the existing result rather than resubmitting.
    """

    message = "Duplicate request — this request has already been processed."
    error_code = "DUPLICATE_REQUEST"
    status = HTTPStatus.CONFLICT


# ------------------------------------------------------------------------------
# 422 — Unprocessable Entity
# ------------------------------------------------------------------------------


class PipelineError(VaaniError):
    """
    The pipeline failed to process a valid request.

    This is distinct from ValidationError — the request was well-formed,
    but processing encountered a recoverable failure.
    """

    message = "Pipeline processing failed."
    error_code = "PIPELINE_ERROR"
    status = HTTPStatus.UNPROCESSABLE_ENTITY


class CascadeError(PipelineError):
    """Cascade orchestration failed at a specific tier."""

    message = "Cascade tier processing failed."
    error_code = "CASCADE_ERROR"


class FusionError(PipelineError):
    """Fusion engine failed to produce a result."""

    message = "Fusion engine failed."
    error_code = "FUSION_ERROR"


# ------------------------------------------------------------------------------
# 429 — Too Many Requests
# ------------------------------------------------------------------------------


class RateLimitError(VaaniError):
    """Rate limit exceeded."""

    message = "Rate limit exceeded. Please retry after the specified delay."
    error_code = "RATE_LIMIT_EXCEEDED"
    status = HTTPStatus.TOO_MANY_REQUESTS


# ------------------------------------------------------------------------------
# 500 — Internal Server Error (infrastructure-level)
# ------------------------------------------------------------------------------


class InfrastructureError(VaaniError):
    """
    Dependency failure — Kafka, model server, or other external system.

    Must NEVER silently return a zero score.  The caller is responsible for
    surfacing this as uncertainty rather than a clean result.
    """

    message = "Infrastructure dependency failed."
    error_code = "INFRASTRUCTURE_ERROR"
    status = HTTPStatus.INTERNAL_SERVER_ERROR


class KafkaError(InfrastructureError):
    """Kafka producer/consumer failure."""

    message = "Kafka messaging failed."
    error_code = "KAFKA_ERROR"


class ModelUnavailableError(InfrastructureError):
    """
    Model adapter could not produce a result due to unavailability.

    Per the VAANI-RAKSHAK principle: model unavailability must be represented
    as explicit UNCERTAIN state — never as score=0 (which implies authentic).
    """

    message = "Detection model is unavailable."
    error_code = "MODEL_UNAVAILABLE"


class ModelTimeoutError(ModelUnavailableError):
    """Model adapter timed out."""

    message = "Detection model timed out."
    error_code = "MODEL_TIMEOUT"


class AuditLedgerError(InfrastructureError):
    """Audit ledger write failed."""

    message = "Audit ledger write failed."
    error_code = "AUDIT_LEDGER_ERROR"


# ------------------------------------------------------------------------------
# 503 — Service Unavailable
# ------------------------------------------------------------------------------


class ServiceUnavailableError(VaaniError):
    """Service is temporarily unavailable (e.g. during startup)."""

    message = "Service is temporarily unavailable."
    error_code = "SERVICE_UNAVAILABLE"
    status = HTTPStatus.SERVICE_UNAVAILABLE
