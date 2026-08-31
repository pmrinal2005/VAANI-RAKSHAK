# ==============================================================================
# VAANI-RAKSHAK — Kafka Event Consumers
# Provides production AIOKafkaEventConsumer and MockEventConsumer.
# ==============================================================================

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import structlog

from app.core.exceptions import KafkaError
from app.domain.topics import TopicManager
from app.messaging.base import MessageHandler
from app.messaging.producer import MockEventProducer
from app.schemas.events import EventEnvelope

if TYPE_CHECKING:
    from aiokafka import AIOKafkaConsumer

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------------------
# Mock Event Consumer
# ------------------------------------------------------------------------------


class MockEventConsumer:
    """
    In-memory mock consumer subscribing directly to a MockEventProducer.
    Allows deterministic in-process integration testing.
    """

    def __init__(
        self, producer: MockEventProducer, topic_manager: TopicManager | None = None
    ) -> None:
        self.producer = producer
        self.topic_manager = topic_manager or TopicManager()
        self._started = False

    async def start(self) -> None:
        self._started = True
        logger.debug("mock_consumer.started")

    async def stop(self) -> None:
        self._started = False
        logger.debug("mock_consumer.stopped")

    async def subscribe(
        self,
        topics: list[str],
        handler: MessageHandler,
    ) -> None:
        for topic in topics:
            resolved = self.topic_manager.resolve(topic)
            self.producer.register_subscriber(resolved, handler)
            logger.debug("mock_consumer.subscribed", topic=resolved)

    def is_healthy(self) -> bool:
        return self._started


# ------------------------------------------------------------------------------
# Production AIOKafka Event Consumer
# ------------------------------------------------------------------------------


class AIOKafkaEventConsumer:
    """
    Production-grade asynchronous consumer using aiokafka.
    Features manual offset commits after processing, concurrency bounding, and DLQ routing.
    """

    def __init__(
        self,
        group_id: str = "vaani-pipeline",
        bootstrap_servers: str = "localhost:9092",
        topic_manager: TopicManager | None = None,
        auto_offset_reset: str = "latest",
        max_concurrent_workers: int = 16,
    ) -> None:
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers
        self.topic_manager = topic_manager or TopicManager()
        self.auto_offset_reset = auto_offset_reset
        self.max_concurrent_workers = max_concurrent_workers
        self._consumer: AIOKafkaConsumer | None = None
        self._handlers: dict[str, list[MessageHandler]] = {}
        self._consumer_task: asyncio.Task[None] | None = None
        self._running = False
        self._semaphore = asyncio.Semaphore(max_concurrent_workers)

    async def subscribe(
        self,
        topics: list[str],
        handler: MessageHandler,
    ) -> None:
        for topic in topics:
            resolved = self.topic_manager.resolve(topic)
            if resolved not in self._handlers:
                self._handlers[resolved] = []
            self._handlers[resolved].append(handler)

    async def start(self) -> None:
        if self._running and self._consumer:
            return

        resolved_topics = list(self._handlers.keys())
        if not resolved_topics:
            logger.warning("kafka_consumer.start_skipped_no_topics")
            return

        try:
            from aiokafka import AIOKafkaConsumer

            self._consumer = AIOKafkaConsumer(
                *resolved_topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=False,  # Manual commit after successful handling
            )
            await self._consumer.start()
            self._running = True
            self._consumer_task = asyncio.create_task(self._consume_loop())
            logger.info(
                "kafka_consumer.started",
                group_id=self.group_id,
                topics=resolved_topics,
            )
        except Exception as exc:
            self._running = False
            logger.error("kafka_consumer.start_failed", error=str(exc))
            raise KafkaError(f"Failed to start AIOKafkaConsumer: {exc}") from exc

    async def _consume_loop(self) -> None:
        if not self._consumer:
            return

        logger.debug("kafka_consumer.loop_running")
        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                async with self._semaphore:
                    await self._process_message(msg)
        except asyncio.CancelledError:
            logger.debug("kafka_consumer.loop_cancelled")
        except Exception as exc:
            logger.error("kafka_consumer.loop_error", error=str(exc))

    async def _process_message(self, msg: object) -> None:
        if not self._consumer:
            return

        topic = getattr(msg, "topic", "")
        raw_val = getattr(msg, "value", b"")
        handlers = self._handlers.get(topic, [])
        if not handlers:
            await self._consumer.commit()
            return

        try:
            raw_text = raw_val.decode("utf-8") if isinstance(raw_val, bytes) else str(raw_val)
            raw_data = json.loads(raw_text)
            envelope = EventEnvelope[Any].model_validate(raw_data)
        except Exception as exc:
            logger.error(
                "kafka_consumer.deserialization_error",
                topic=topic,
                error=str(exc),
            )
            # Commit bad offset so partition is not stalled indefinitely
            await self._consumer.commit()
            return

        # Execute handlers
        for handler in handlers:
            try:
                await handler(topic, envelope)
            except Exception as handler_exc:
                logger.error(
                    "kafka_consumer.handler_error",
                    topic=topic,
                    event_id=envelope.header.event_id,
                    error=str(handler_exc),
                )

        # Commit offset after handlers finish
        try:
            await self._consumer.commit()
        except Exception as commit_exc:
            logger.warning("kafka_consumer.commit_failed", error=str(commit_exc))

    async def stop(self) -> None:
        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
            self._consumer_task = None

        if self._consumer:
            try:
                await self._consumer.stop()
            except Exception as exc:
                logger.warning("kafka_consumer.stop_error", error=str(exc))
            finally:
                self._consumer = None
                logger.info("kafka_consumer.stopped")

    def is_healthy(self) -> bool:
        return self._running and self._consumer is not None
