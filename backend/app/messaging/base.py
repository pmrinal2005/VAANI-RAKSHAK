# ==============================================================================
# VAANI-RAKSHAK — Messaging Protocol Interfaces
# Defines async producer and consumer contracts for Kafka event streaming.
# ==============================================================================

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from app.schemas.events import EventEnvelope

MessageHandler = Callable[[str, EventEnvelope[Any]], Awaitable[None]]


@runtime_checkable
class EventProducer(Protocol):
    """Async event publisher interface."""

    async def start(self) -> None:
        """Initialize connection pool / client."""
        ...

    async def stop(self) -> None:
        """Flush pending batches and close connections."""
        ...

    async def send(
        self,
        topic: str,
        envelope: EventEnvelope[Any],
        key: str | None = None,
    ) -> None:
        """
        Publish an event to the designated Kafka topic.
        Partition key (e.g. call_id) ensures partition-level ordering.
        """
        ...

    async def send_dlq(
        self,
        original_topic: str,
        original_payload: object,
        error: Exception,
        retry_count: int = 0,
        correlation_id: str = "unknown",
    ) -> None:
        """Route failed or unprocessable message to the dead-letter queue."""
        ...

    def is_healthy(self) -> bool:
        """Return True if producer is operational and ready to send messages."""
        ...


@runtime_checkable
class EventConsumer(Protocol):
    """Async event consumer group interface."""

    async def start(self) -> None:
        """Start background consumer loop."""
        ...

    async def stop(self) -> None:
        """Stop consumer loop and drain in-flight messages."""
        ...

    async def subscribe(
        self,
        topics: list[str],
        handler: MessageHandler,
    ) -> None:
        """Subscribe to a set of topics and attach a processing handler."""
        ...

    def is_healthy(self) -> bool:
        """Return True if consumer loop is running and connected."""
        ...
