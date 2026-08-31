# ==============================================================================
# VAANI-RAKSHAK — Kafka to WebSocket & SSE Streaming Event Bridge
# Reuses the existing EventConsumer abstraction to bridge Kafka events into
# active WebSocket call rooms, global SOC channels, and SSE subscribers.
# ==============================================================================

from __future__ import annotations

from typing import Any, ClassVar

import structlog

from app.domain.topics import KafkaTopic
from app.messaging.base import EventConsumer
from app.schemas.events import EventEnvelope
from app.streaming.manager import ConnectionManager

logger = structlog.get_logger(__name__)


class KafkaStreamingBridge:
    """
    Consumes events from Kafka event pipeline and dispatches them in real time
    to WebSocket and Server-Sent Events subscribers via ConnectionManager.
    """

    BRIDGE_TOPICS: ClassVar[list[KafkaTopic]] = [
        KafkaTopic.FUSION_RESULT,
        KafkaTopic.RISK_EVENTS,
        KafkaTopic.WORKFLOW_EVENTS,
    ]

    def __init__(
        self,
        consumer: EventConsumer,
        connection_manager: ConnectionManager,
    ) -> None:
        self.consumer = consumer
        self.connection_manager = connection_manager
        self._is_running = False

    async def start(self) -> None:
        """Start the consumer and register event dispatch handlers."""
        if self._is_running:
            return

        topic_names = [t.value for t in self.BRIDGE_TOPICS]
        logger.info("streaming_bridge.starting", topics=topic_names)

        await self.consumer.subscribe(
            topics=topic_names,
            handler=self.handle_envelope,
        )
        await self.consumer.start()
        self._is_running = True
        logger.info("streaming_bridge.started")

    async def stop(self) -> None:
        """Stop the consumer and cease dispatch."""
        if not self._is_running:
            return

        logger.info("streaming_bridge.stopping")
        await self.consumer.stop()
        self._is_running = False
        logger.info("streaming_bridge.stopped")

    async def handle_envelope(self, topic: str, envelope: EventEnvelope[Any]) -> None:
        """
        Process incoming Kafka event envelope and dispatch to WebSocket / SSE.
        """
        event_type = envelope.header.event_type
        correlation_id = envelope.header.correlation_id

        # Derive call_id from correlation_id or payload if available
        call_id = correlation_id
        if hasattr(envelope.payload, "call_id"):
            call_id = envelope.payload.call_id
        elif isinstance(envelope.payload, dict) and "call_id" in envelope.payload:
            call_id = envelope.payload["call_id"]

        event_data = envelope.model_dump(mode="json", by_alias=True)

        logger.debug(
            "streaming_bridge.event_received",
            topic=topic,
            event_type=event_type,
            call_id=call_id,
            event_id=envelope.header.event_id,
        )

        # 1. Broadcast to specific active call room if call_id is known
        if call_id:
            await self.connection_manager.broadcast_to_call(call_id, event_data)

        # 2. Broadcast all risk, fusion, and workflow events to global SOC clients
        await self.connection_manager.broadcast_global(event_data)

        # 3. Push to all active SSE queues
        self.connection_manager.broadcast_sse(event_type=event_type, data=event_data)
