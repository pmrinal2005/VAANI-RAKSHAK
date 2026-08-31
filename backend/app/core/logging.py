# ==============================================================================
# VAANI-RAKSHAK — Structured Logging Configuration
# Uses structlog for consistent, machine-parseable log output.
# Sensitive data (audio, credentials, PII) must never appear in logs.
# ==============================================================================

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    pass

# Fields that must never appear in log output
_SENSITIVE_FIELDS = frozenset(
    {
        "audio_data",
        "raw_audio",
        "samples",
        "password",
        "secret",
        "token",
        "api_key",
        "authorization",
        "credential",
        "private_key",
    }
)


def _drop_sensitive_fields(
    logger: Any,  # noqa: ANN401 — structlog processor signature
    method: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Processor: drop any key that matches a sensitive field name."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_FIELDS:
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """
    Configure structlog for the application.

    Args:
        log_level: Standard Python log level string.
        json_logs: If True, emit JSON lines (production).
                   If False, emit human-friendly coloured output (development).
    """
    # ------------------------------------------------------------------
    # Shared processors applied to every log record
    # ------------------------------------------------------------------
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _drop_sensitive_fields,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # Production: structured JSON — easily ingested by log aggregators
        processors: list[structlog.types.Processor] = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
    else:
        # Development: coloured, human-readable console output
        processors = [
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=shared_processors,
        )

    # ------------------------------------------------------------------
    # Configure stdlib logging to route through structlog
    # ------------------------------------------------------------------
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level.upper())

    # Quiet noisy third-party loggers
    for noisy in ("aiokafka", "kafka", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # ------------------------------------------------------------------
    # Configure structlog itself
    # ------------------------------------------------------------------
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Return a structlog BoundLogger for the given name.

    Usage::

        logger = get_logger(__name__)
        logger.info("pipeline.started", call_id=call_id, request_id=request_id)
    """
    from typing import cast

    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
