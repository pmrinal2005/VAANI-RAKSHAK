# ==============================================================================
# Unit tests — Kafka Producer & Consumer Abstractions
# Verifies Protocol compliance, in-memory mock pub/sub, keying, and DLQ routing.
# ==============================================================================

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.domain.topics import KafkaTopic, TopicManager
from app.messaging.base import EventConsumer, EventProducer
from app.messaging.consumer import MockEventConsumer
from app.messaging.producer import MockEventProducer
from app.schemas.events import EventEnvelope, EventHeader


@pytest.fixture
def topic_mgr() -> TopicManager:
    return TopicManager(prefix="vaani.test")


@pytest.fixture
def mock_producer(topic_mgr: TopicManager) -> MockEventProducer:
    return MockEventProducer(topic_manager=topic_mgr)


@pytest.fixture
def mock_consumer(mock_producer: MockEventProducer, topic_mgr: TopicManager) -> MockEventConsumer:
    return MockEventConsumer(producer=mock_producer, topic_manager=topic_mgr)


class TestMessagingProtocols:
    """Verify mock implementations fulfill EventProducer and EventConsumer protocols."""

    def test_producer_protocol_compliance(self, mock_producer: MockEventProducer) -> None:
        assert isinstance(mock_producer, EventProducer)

    def test_consumer_protocol_compliance(self, mock_consumer: MockEventConsumer) -> None:
        assert isinstance(mock_consumer, EventConsumer)


class TestMockEventProducer:
    """Test MockEventProducer publish, queue retrieval, and DLQ handling."""

    @pytest.mark.asyncio
    async def test_send_and_retrieve_events(self, mock_producer: MockEventProducer) -> None:
        await mock_producer.start()
        assert mock_producer.is_healthy() is True

        envelope = EventEnvelope[dict[str, Any]](
            header=EventHeader(correlation_id="call-001", event_type="audio.ingest"),
            payload={"audio_uri": "s3://bucket/audio.wav"},
        )
        await mock_producer.send("audio.ingest", envelope, key="call-001")

        events = mock_producer.get_published_events("audio.ingest")
        assert len(events) == 1
        assert events[0].header.correlation_id == "call-001"
        assert events[0].payload["audio_uri"] == "s3://bucket/audio.wav"

        await mock_producer.stop()
        assert mock_producer.is_healthy() is False

    @pytest.mark.asyncio
    async def test_send_to_unprefixed_and_prefixed_topic(
        self, mock_producer: MockEventProducer
    ) -> None:
        await mock_producer.start()
        env1 = EventEnvelope[dict[str, Any]](
            header=EventHeader(correlation_id="call-1", event_type="test"),
            payload={"n": 1},
        )
        await mock_producer.send(KafkaTopic.DETECTION_TIER0, env1)

        # Both resolves should match
        events1 = mock_producer.get_published_events(KafkaTopic.DETECTION_TIER0)
        events2 = mock_producer.get_published_events("vaani.test.detection.tier0")
        assert len(events1) == 1
        assert len(events2) == 1

    @pytest.mark.asyncio
    async def test_send_dlq_routing(self, mock_producer: MockEventProducer) -> None:
        await mock_producer.start()
        exc = ValueError("Invalid audio frame format")
        await mock_producer.send_dlq(
            original_topic="vaani.test.audio.segment",
            original_payload={"raw_chunk": "corrupt_data"},
            error=exc,
            retry_count=3,
            correlation_id="call-dlq-01",
        )

        dlq_events = mock_producer.get_dlq_events()
        assert len(dlq_events) == 1
        assert dlq_events[0].header.correlation_id == "call-dlq-01"
        assert dlq_events[0].payload.error_class == "ValueError"
        assert dlq_events[0].payload.retry_count == 3
        assert "Invalid audio frame" in dlq_events[0].payload.error_message

    @pytest.mark.asyncio
    async def test_clear_events(self, mock_producer: MockEventProducer) -> None:
        await mock_producer.start()
        env = EventEnvelope[dict[str, Any]](
            header=EventHeader(correlation_id="c1", event_type="t"), payload={}
        )
        await mock_producer.send("audio.ingest", env)
        assert len(mock_producer.get_published_events("audio.ingest")) == 1

        mock_producer.clear()
        assert len(mock_producer.get_published_events("audio.ingest")) == 0
        assert len(mock_producer.get_dlq_events()) == 0


class TestMockEventConsumer:
    """Test MockEventConsumer subscription and async message dispatch."""

    @pytest.mark.asyncio
    async def test_pub_sub_flow(
        self,
        mock_producer: MockEventProducer,
        mock_consumer: MockEventConsumer,
    ) -> None:
        await mock_producer.start()
        await mock_consumer.start()

        received_events: list[EventEnvelope[Any]] = []

        async def handler(topic: str, envelope: EventEnvelope[Any]) -> None:
            received_events.append(envelope)

        await mock_consumer.subscribe(["audio.segment", "detection.tier0"], handler)

        env1 = EventEnvelope[dict[str, Any]](
            header=EventHeader(correlation_id="call-sub-1", event_type="audio.segment"),
            payload={"seq": 0},
        )
        env2 = EventEnvelope[dict[str, Any]](
            header=EventHeader(correlation_id="call-sub-2", event_type="detection.tier0"),
            payload={"score": 0.12},
        )
        env3 = EventEnvelope[dict[str, Any]](
            header=EventHeader(correlation_id="call-sub-3", event_type="fusion.result"),
            payload={"score": 0.12},
        )

        await mock_producer.send("audio.segment", env1)
        await mock_producer.send("detection.tier0", env2)
        await mock_producer.send("fusion.result", env3)  # Not subscribed

        # Allow async handler tasks to execute
        await asyncio.sleep(0.05)

        assert len(received_events) == 2
        corr_ids = [e.header.correlation_id for e in received_events]
        assert "call-sub-1" in corr_ids
        assert "call-sub-2" in corr_ids
        assert "call-sub-3" not in corr_ids

        await mock_consumer.stop()
        await mock_producer.stop()
