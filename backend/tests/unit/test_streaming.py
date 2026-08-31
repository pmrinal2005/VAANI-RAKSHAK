# ==============================================================================
# Unit & Integration tests — Real-Time Event Stream (WebSocket & SSE)
# Verifies ConnectionManager, KafkaStreamingBridge, and WebSocket/SSE endpoints.
# ==============================================================================

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.domain.enums import RiskBand, RiskVerdict
from app.domain.topics import KafkaTopic
from app.main import create_app
from app.messaging.consumer import MockEventConsumer
from app.messaging.producer import MockEventProducer
from app.schemas.events import EventEnvelope, EventHeader, RiskEventPayload
from app.streaming.bridge import KafkaStreamingBridge
from app.streaming.manager import ConnectionManager


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestConnectionManager:
    """Test unit behavior of the ConnectionManager."""

    @pytest.mark.asyncio
    async def test_sse_subscriber_lifecycle_and_broadcast(self) -> None:
        manager = ConnectionManager()
        queue = manager.subscribe_sse()
        assert manager.get_sse_subscriber_count() == 1

        # Broadcast event to SSE queue
        queued = manager.broadcast_sse(
            event_type="risk.events",
            data={"callId": "call-sse-1", "riskScore": 88},
        )
        assert queued == 1

        item = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert item["event"] == "risk.events"
        assert item["data"]["callId"] == "call-sse-1"

        manager.unsubscribe_sse(queue)
        assert manager.get_sse_subscriber_count() == 0


class TestKafkaStreamingBridge:
    """Test KafkaStreamingBridge consuming from MockEventProducer and broadcasting."""

    @pytest.mark.asyncio
    async def test_bridge_dispatches_to_call_and_global_and_sse(self) -> None:
        manager = ConnectionManager()
        producer = MockEventProducer()
        await producer.start()
        consumer = MockEventConsumer(producer=producer)
        await consumer.start()
        bridge = KafkaStreamingBridge(consumer=consumer, connection_manager=manager)

        await bridge.start()

        # Subscribe to SSE queue to verify dispatch
        sse_queue = manager.subscribe_sse()

        # Produce a mock risk event
        risk_payload = RiskEventPayload(
            call_id="call-bridge-01",
            risk_score=92,
            band=RiskBand.CRITICAL,
            verdict=RiskVerdict.LIKELY_CLONE,
            requires_out_of_band=True,
            explanation="Test critical clone alert",
        )
        envelope: EventEnvelope[RiskEventPayload] = EventEnvelope(
            header=EventHeader(
                correlation_id="call-bridge-01",
                event_type="risk.events",
            ),
            payload=risk_payload,
        )

        await producer.send(
            topic=KafkaTopic.RISK_EVENTS.value,
            envelope=envelope,
            key="call-bridge-01",
        )

        # Allow background task to execute
        await asyncio.sleep(0.1)

        # Verify SSE received the bridged event
        item = await asyncio.wait_for(sse_queue.get(), timeout=2.0)
        assert item["event"] == "risk.events"
        assert item["data"]["payload"]["riskScore"] == 92
        assert item["data"]["payload"]["callId"] == "call-bridge-01"

        await bridge.stop()
        await consumer.stop()
        await producer.stop()


class TestWebSocketStreamingEndpoints:
    """Test WebSocket /ws/calls/{call_id} and /ws/events routes."""

    def test_websocket_call_stream_ping_pong_and_detection(self, client: TestClient) -> None:
        call_id = "call-ws-test-01"
        with client.websocket_connect(f"/api/v1/ws/calls/{call_id}") as ws:
            # 1. Receive connection confirmation
            greeting = ws.receive_json()
            assert greeting["type"] == "connection_established"
            assert greeting["callId"] == call_id

            # 2. Test Ping/Pong
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"

            # 3. Test Audio Chunk Detection Ingestion
            chunk_payload = {
                "type": "audio_chunk",
                "request": {
                    "segment": {
                        "callId": call_id,
                        "segmentId": "seg-001",
                        "features": {
                            "spectralFlatnessVoiced": 0.05,
                            "hfEnergyRatio": 0.02,
                            "jitter": 0.003,
                            "shimmer": 0.02,
                            "f0RangeHz": 65.0,
                        },
                    },
                    "context": {
                        "transactionType": "inquiry",
                        "transactionValueInr": 0,
                    },
                    "scenarioOverride": "LOW_RISK",
                },
            }
            ws.send_json(chunk_payload)

            result = ws.receive_json()
            assert result["type"] == "detection_result"
            assert result["callId"] == call_id
            assert "payload" in result
            assert result["payload"]["riskScore"] < 40
            assert result["payload"]["verdict"] == "AUTHENTIC"

    def test_websocket_global_events_ping_pong(self, client: TestClient) -> None:
        with client.websocket_connect("/api/v1/ws/events") as ws:
            greeting = ws.receive_json()
            assert greeting["type"] == "connection_established"
            assert greeting["channel"] == "soc_global_broadcast"

            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"


class TestServerSentEventsEndpoint:
    """Test GET /api/v1/events/stream endpoint."""

    @pytest.mark.asyncio
    async def test_sse_endpoint_connects_and_receives_events(self) -> None:
        from app.api.routes.streaming import sse_event_stream

        manager = ConnectionManager()
        response = await sse_event_stream(manager=manager)
        assert response.status_code == 200
        assert response.media_type == "text/event-stream"

        gen = response.body_iterator

        # 1. Read first welcome event
        first_chunk = await anext(gen)
        assert "event: ping" in first_chunk
        assert "connected" in first_chunk

        # 2. Push an event and verify SSE formatting
        manager.broadcast_sse(
            event_type="risk.events",
            data={"callId": "call-sse-gen", "score": 90},
        )
        second_chunk = await anext(gen)
        assert "event: risk.events" in second_chunk
        assert '"callId": "call-sse-gen"' in second_chunk

        # 3. Clean up
        await gen.aclose()
