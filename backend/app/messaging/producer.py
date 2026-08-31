# ==============================================================================
# VAANI-RAKSHAK — Kafka Event Producers
# Provides production AIOKafkaEventProducer and zero-dependency MockEventProducer.
# ==============================================================================

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.exceptions import KafkaError
from app.domain.topics import KafkaTopic, TopicManager
from app.schemas.events import DeadLetterPayload, EventEnvelope, EventHeader

if TYPE_CHECKING:
    from aiokafka import AIOKafkaProducer

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------------------
# Mock Event Producer (In-Memory Testing & Development)
# ------------------------------------------------------------------------------


class MockEventProducer:
    """
    In-memory mock producer that stores published events in FIFO queues.
    Enables deterministic testing of pipeline flows without a live Kafka broker.
    """

    def __init__(self, topic_manager: TopicManager | None = None) -> None:
        self.topic_manager = topic_manager or TopicManager()
        self._events: dict[str, list[EventEnvelope[Any]]] = defaultdict(list)
        self._dlq_events: list[EventEnvelope[DeadLetterPayload]] = []
        self._started = False
        self._subscribers: dict[str, list[Any]] = defaultdict(list)
        self._background_tasks: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        self._started = True
        logger.debug("mock_producer.started")

    async def stop(self) -> None:
        self._started = False
        logger.debug("mock_producer.stopped")

    async def send(
        self,
        topic: str,
        envelope: EventEnvelope[Any],
        key: str | None = None,
    ) -> None:
        resolved_topic = self.topic_manager.resolve(topic)
        self._events[resolved_topic].append(envelope)
        logger.debug(
            "mock_producer.sent",
            topic=resolved_topic,
            event_id=envelope.header.event_id,
            correlation_id=envelope.header.correlation_id,
            key=key,
        )

        # Notify any in-memory subscribers
        for handler in self._subscribers.get(resolved_topic, []):
            task = asyncio.create_task(handler(resolved_topic, envelope))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def send_dlq(
        self,
        original_topic: str,
        original_payload: object,
        error: Exception,
        retry_count: int = 0,
        correlation_id: str = "unknown",
    ) -> None:
        dlq_payload = DeadLetterPayload(
            original_topic=original_topic,
            original_payload=str(original_payload),
            error_message=str(error),
            error_class=type(error).__name__,
            retry_count=retry_count,
        )
        envelope: EventEnvelope[DeadLetterPayload] = EventEnvelope(
            header=EventHeader(
                correlation_id=correlation_id,
                event_type="deadletter",
            ),
            payload=dlq_payload,
        )
        self._dlq_events.append(envelope)
        dlq_topic = self.topic_manager.resolve(KafkaTopic.DEADLETTER)
        self._events[dlq_topic].append(envelope)
        logger.warning(
            "mock_producer.dlq_routed",
            original_topic=original_topic,
            error=str(error),
        )

    def is_healthy(self) -> bool:
        return self._started

    def get_published_events(self, topic: str) -> list[EventEnvelope[Any]]:
        """Return all published events for a given topic."""
        resolved = self.topic_manager.resolve(topic)
        return list(self._events.get(resolved, []))

    def get_dlq_events(self) -> list[EventEnvelope[DeadLetterPayload]]:
        """Return all dead-letter queue events."""
        return list(self._dlq_events)

    def register_subscriber(self, topic: str, handler: object) -> None:
        """Attach an in-memory consumer handler for a topic."""
        resolved = self.topic_manager.resolve(topic)
        self._subscribers[resolved].append(handler)

    def clear(self) -> None:
        """Clear all stored events (useful between test runs)."""
        self._events.clear()
        self._dlq_events.clear()


# ------------------------------------------------------------------------------
# Production AIOKafka Event Producer
# ------------------------------------------------------------------------------


class AIOKafkaEventProducer:
    """
    Production-grade asynchronous Kafka producer using aiokafka.
    Features idempotent delivery, acks=all, retries, and DLQ routing.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic_manager: TopicManager | None = None,
        linger_ms: int = 5,
        acks: str = "all",
    ) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.topic_manager = topic_manager or TopicManager()
        self.linger_ms = linger_ms
        self.acks = acks
        self._producer: AIOKafkaProducer | None = None
        self._started = False

    async def start(self) -> None:
        if self._started and self._producer:
            return

        try:
            from aiokafka import AIOKafkaProducer

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                acks=self.acks,
                linger_ms=self.linger_ms,
                enable_idempotence=(self.acks == "all"),
            )
            await self._producer.start()
            self._started = True
            logger.info("kafka_producer.started", bootstrap_servers=self.bootstrap_servers)
        except Exception as exc:
            self._started = False
            logger.error("kafka_producer.start_failed", error=str(exc))
            raise KafkaError(f"Failed to start AIOKafkaProducer: {exc}") from exc

    async def stop(self) -> None:
        if self._producer and self._started:
            try:
                await self._producer.flush()
                await self._producer.stop()
            except Exception as exc:
                logger.warning("kafka_producer.stop_error", error=str(exc))
            finally:
                self._started = False
                self._producer = None
                logger.info("kafka_producer.stopped")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _send_with_retry(
        self,
        topic: str,
        value_bytes: bytes,
        key_bytes: bytes | None,
    ) -> None:
        if not self._producer or not self._started:
            msg = "AIOKafkaProducer is not running"
            raise KafkaError(msg)
        await self._producer.send_and_wait(topic, value=value_bytes, key=key_bytes)

    async def send(
        self,
        topic: str,
        envelope: EventEnvelope[Any],
        key: str | None = None,
    ) -> None:
        resolved_topic = self.topic_manager.resolve(topic)
        value_bytes = envelope.model_dump_json().encode("utf-8")
        partition_key = key or envelope.header.correlation_id
        key_bytes = partition_key.encode("utf-8") if partition_key else None

        try:
            await self._send_with_retry(resolved_topic, value_bytes, key_bytes)
            logger.debug(
                "kafka_producer.message_sent",
                topic=resolved_topic,
                event_id=envelope.header.event_id,
                correlation_id=envelope.header.correlation_id,
            )
        except Exception as exc:
            logger.error(
                "kafka_producer.send_failed_routing_to_dlq",
                topic=resolved_topic,
                error=str(exc),
            )
            await self.send_dlq(
                original_topic=resolved_topic,
                original_payload=envelope.model_dump(),
                error=exc,
                retry_count=3,
                correlation_id=envelope.header.correlation_id,
            )

    async def send_dlq(
        self,
        original_topic: str,
        original_payload: object,
        error: Exception,
        retry_count: int = 0,
        correlation_id: str = "unknown",
    ) -> None:
        dlq_topic = self.topic_manager.resolve(KafkaTopic.DEADLETTER)
        dlq_payload = DeadLetterPayload(
            original_topic=original_topic,
            original_payload=str(original_payload),
            error_message=str(error),
            error_class=type(error).__name__,
            retry_count=retry_count,
        )
        envelope: EventEnvelope[DeadLetterPayload] = EventEnvelope(
            header=EventHeader(
                correlation_id=correlation_id,
                event_type="deadletter",
            ),
            payload=dlq_payload,
        )
        value_bytes = envelope.model_dump_json().encode("utf-8")
        key_bytes = correlation_id.encode("utf-8")

        try:
            if self._producer and self._started:
                await self._producer.send_and_wait(dlq_topic, value=value_bytes, key=key_bytes)
                logger.warning(
                    "kafka_producer.dlq_delivered",
                    dlq_topic=dlq_topic,
                    original_topic=original_topic,
                )
        except Exception as dlq_exc:
            logger.critical(
                "kafka_producer.dlq_delivery_failed",
                error=str(dlq_exc),
                original_error=str(error),
            )

    def is_healthy(self) -> bool:
        return self._started and self._producer is not None
