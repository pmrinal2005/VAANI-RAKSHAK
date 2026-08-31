# ==============================================================================
# VAANI-RAKSHAK — Application Lifecycle Management
# Centralises startup and shutdown sequencing.
# Each dependency registers its own start/stop handlers here.
# ==============================================================================

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.

    Executed on startup (before ``yield``) and shutdown (after ``yield``).

    Startup sequence:
      1. Logging
      2. Settings validation
      3. Kafka (Phase 2 — placeholder registered here)
      4. Model adapters (Phase 1 — placeholder registered here)

    Shutdown sequence (reverse order):
      1. Model adapters
      2. Kafka
    """
    settings = get_settings()

    # ------------------------------------------------------------------
    # STARTUP
    # ------------------------------------------------------------------
    configure_logging(
        log_level=settings.log_level,
        json_logs=settings.log_json,
    )

    logger.info(
        "application.startup",
        app_name=settings.app_name,
        app_version=settings.app_version,
        app_env=settings.app_env,
        detection_mode=settings.detection_mode,
        audit_mode=settings.audit_mode,
    )

    # Kafka lifecycle initialisation
    await _startup_kafka(settings)

    # Phase 1 placeholder — model adapters will be initialised here
    _startup_models(settings)

    logger.info("application.ready", api_prefix=settings.api_prefix)

    yield

    # ------------------------------------------------------------------
    # SHUTDOWN
    # ------------------------------------------------------------------
    logger.info("application.shutdown.started")

    # Phase 1 placeholder
    _shutdown_models()

    # Kafka lifecycle shutdown
    await _shutdown_kafka()

    logger.info("application.shutdown.complete")


# ------------------------------------------------------------------------------
# Kafka & Streaming Bridge lifecycle
# ------------------------------------------------------------------------------

_GLOBAL_PRODUCER: object | None = None
_GLOBAL_CONSUMER: object | None = None
_GLOBAL_STREAMING_BRIDGE: object | None = None


def get_global_producer() -> object | None:
    return _GLOBAL_PRODUCER


def get_global_consumer() -> object | None:
    return _GLOBAL_CONSUMER


def get_global_streaming_bridge() -> object | None:
    return _GLOBAL_STREAMING_BRIDGE


async def _startup_kafka(settings: Settings) -> None:
    """Initialise and start global Kafka producer, consumer, and streaming bridge."""
    global _GLOBAL_PRODUCER, _GLOBAL_CONSUMER, _GLOBAL_STREAMING_BRIDGE
    from app.api.dependencies import get_connection_manager
    from app.domain.topics import TopicManager
    from app.messaging.consumer import AIOKafkaEventConsumer, MockEventConsumer
    from app.messaging.producer import AIOKafkaEventProducer, MockEventProducer
    from app.streaming.bridge import KafkaStreamingBridge

    topic_mgr = TopicManager(prefix=settings.kafka_topic_prefix)

    if settings.is_development or settings.detection_mode == "mock":
        mock_producer = MockEventProducer(topic_manager=topic_mgr)
        await mock_producer.start()
        _GLOBAL_PRODUCER = mock_producer

        mock_consumer = MockEventConsumer(
            producer=mock_producer, topic_manager=topic_mgr
        )
        bridge = KafkaStreamingBridge(
            consumer=mock_consumer,
            connection_manager=get_connection_manager(),
        )
        await bridge.start()
        _GLOBAL_CONSUMER = mock_consumer
        _GLOBAL_STREAMING_BRIDGE = bridge

        logger.info("kafka.lifecycle.started", mode="mock_in_memory")
    else:
        try:
            kafka_producer = AIOKafkaEventProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                topic_manager=topic_mgr,
                acks=settings.kafka_producer_acks,
                linger_ms=settings.kafka_producer_linger_ms,
            )
            await kafka_producer.start()
            _GLOBAL_PRODUCER = kafka_producer

            kafka_consumer = AIOKafkaEventConsumer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=f"{settings.kafka_consumer_group_id}-streaming-bridge",
                topic_manager=topic_mgr,
            )
            bridge = KafkaStreamingBridge(
                consumer=kafka_consumer,
                connection_manager=get_connection_manager(),
            )
            await bridge.start()
            _GLOBAL_CONSUMER = kafka_consumer
            _GLOBAL_STREAMING_BRIDGE = bridge

            logger.info(
                "kafka.lifecycle.started",
                mode="aiokafka",
                bootstrap=settings.kafka_bootstrap_servers,
            )
        except Exception as exc:
            logger.warning(
                "kafka.lifecycle.fallback_to_mock",
                error=str(exc),
                reason="Broker connection failed, fallback to mock producer/consumer",
            )
            fallback_producer = MockEventProducer(topic_manager=topic_mgr)
            await fallback_producer.start()
            _GLOBAL_PRODUCER = fallback_producer

            mock_consumer = MockEventConsumer(
                producer=fallback_producer, topic_manager=topic_mgr
            )
            bridge = KafkaStreamingBridge(
                consumer=mock_consumer,
                connection_manager=get_connection_manager(),
            )
            await bridge.start()
            _GLOBAL_CONSUMER = mock_consumer
            _GLOBAL_STREAMING_BRIDGE = bridge


async def _shutdown_kafka() -> None:
    """Stop streaming bridge, consumer, and producer."""
    global _GLOBAL_PRODUCER, _GLOBAL_CONSUMER, _GLOBAL_STREAMING_BRIDGE

    if _GLOBAL_STREAMING_BRIDGE is not None and hasattr(_GLOBAL_STREAMING_BRIDGE, "stop"):
        try:
            await _GLOBAL_STREAMING_BRIDGE.stop()
            logger.info("streaming_bridge.lifecycle.stopped")
        except Exception as exc:
            logger.warning("streaming_bridge.lifecycle.stop_error", error=str(exc))
        finally:
            _GLOBAL_STREAMING_BRIDGE = None

    if _GLOBAL_CONSUMER is not None and hasattr(_GLOBAL_CONSUMER, "stop"):
        try:
            await _GLOBAL_CONSUMER.stop()
            logger.info("kafka_consumer.lifecycle.stopped")
        except Exception as exc:
            logger.warning("kafka_consumer.lifecycle.stop_error", error=str(exc))
        finally:
            _GLOBAL_CONSUMER = None

    if _GLOBAL_PRODUCER is not None and hasattr(_GLOBAL_PRODUCER, "stop"):
        try:
            await _GLOBAL_PRODUCER.stop()
            logger.info("kafka.lifecycle.stopped")
        except Exception as exc:
            logger.warning("kafka.lifecycle.stop_error", error=str(exc))
        finally:
            _GLOBAL_PRODUCER = None


# ------------------------------------------------------------------------------
# Model adapter lifecycle stubs (Phase 1 will replace these)
# ------------------------------------------------------------------------------


def _startup_models(settings: object) -> None:
    """
    Phase 1 placeholder.

    Real implementation will:
      - Load ONNX session(s) from model paths
      - Warm up inference with a dummy batch
      - Verify adapter contract compliance
    """
    logger.debug(
        "models.startup.skipped",
        reason="Phase 0 — running in mock mode, no model artefacts required",
    )


def _shutdown_models() -> None:
    """Phase 1 placeholder — will release ONNX session resources."""
    logger.debug("models.shutdown.skipped", reason="Phase 0 — nothing to release")
