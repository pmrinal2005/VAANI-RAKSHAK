# ==============================================================================
# Unit tests — Kafka Topic Topology & Event Schemas
# Verifies topic naming, ULID header generation, generic envelopes, and payloads.
# ==============================================================================

from __future__ import annotations

from app.domain.enums import (
    AuditBlockType,
    Decision,
    DetectionLabel,
    DetectionStatus,
    RiskBand,
    RiskVerdict,
)
from app.domain.topics import KafkaTopic, TopicManager
from app.schemas.audio import AudioReference
from app.schemas.context import CallContext
from app.schemas.detection import DetectionResult
from app.schemas.events import (
    AudioIngestPayload,
    AuditEventPayload,
    DeadLetterPayload,
    EventEnvelope,
    EventHeader,
    RiskEventPayload,
    TierDetectionPayload,
    WorkflowEventPayload,
)


class TestTopicTopology:
    """Test TopicManager prefixing and validation."""

    def test_default_prefix(self) -> None:
        mgr = TopicManager()
        assert mgr.prefix == "vaani"
        assert mgr.resolve(KafkaTopic.AUDIO_INGEST) == "vaani.audio.ingest"
        assert mgr.resolve(KafkaTopic.FUSION_RESULT) == "vaani.fusion.result"
        assert mgr.resolve(KafkaTopic.DEADLETTER) == "vaani.deadletter"

    def test_custom_prefix(self) -> None:
        mgr = TopicManager(prefix="vaani.dev")
        assert mgr.resolve(KafkaTopic.AUDIO_INGEST) == "vaani.dev.audio.ingest"
        assert mgr.resolve("custom.topic") == "vaani.dev.custom.topic"

    def test_idempotent_prefixing(self) -> None:
        mgr = TopicManager(prefix="vaani")
        # If already prefixed, do not double-prefix
        assert mgr.resolve("vaani.audio.ingest") == "vaani.audio.ingest"

    def test_get_all_topics(self) -> None:
        mgr = TopicManager()
        topics = mgr.get_all_topics()
        assert len(topics) == 12
        assert "vaani.audio.ingest" in topics
        assert "vaani.deadletter" in topics

    def test_is_valid_topic(self) -> None:
        mgr = TopicManager()
        assert mgr.is_valid_topic("vaani.audio.ingest") is True
        assert mgr.is_valid_topic("audio.ingest") is True
        assert mgr.is_valid_topic("nonexistent.topic") is False


class TestEventHeaders:
    """Test ULID generation and OpenTelemetry trace headers."""

    def test_event_header_defaults(self) -> None:
        header = EventHeader(correlation_id="call-001", event_type="audio.ingest")
        assert header.correlation_id == "call-001"
        assert header.event_type == "audio.ingest"
        assert len(header.event_id) == 26  # Standard ULID length
        assert len(header.trace_id) == 32  # Hex UUID length
        assert header.producer == "vaani-backend"
        assert header.version == "1.0.0"

    def test_ulid_sortability(self) -> None:
        h1 = EventHeader(correlation_id="call-1", event_type="test")
        h2 = EventHeader(correlation_id="call-2", event_type="test")
        assert h1.event_id <= h2.event_id


class TestEventEnvelopes:
    """Test generic EventEnvelope serialization and deserialization across payloads."""

    def test_audio_ingest_envelope(self) -> None:
        payload = AudioIngestPayload(
            call_id="call-100",
            channel="SIP",
            audio_reference=AudioReference(uri="s3://bucket/call.wav"),
            context=CallContext(transaction_value_inr=50000),
        )
        envelope = EventEnvelope[AudioIngestPayload](
            header=EventHeader(correlation_id="call-100", event_type="audio.ingest"),
            payload=payload,
        )
        json_str = envelope.model_dump_json()
        assert "call-100" in json_str

        # Roundtrip deserialization
        parsed = EventEnvelope[AudioIngestPayload].model_validate_json(json_str)
        assert parsed.header.correlation_id == "call-100"
        assert parsed.payload.channel == "SIP"

    def test_tier_detection_envelope(self) -> None:
        res = DetectionResult(
            tier=1,
            score=0.85,
            confidence=0.92,
            label=DetectionLabel.LIKELY_CLONE,
            latency_ms=12.4,
            model_name="mock-tier1",
            model_version="1.0",
            status=DetectionStatus.SUCCESS,
        )
        payload = TierDetectionPayload(
            call_id="call-200",
            segment_id="seg-001",
            result=res,
        )
        envelope = EventEnvelope[TierDetectionPayload](
            header=EventHeader(correlation_id="call-200", event_type="detection.tier1"),
            payload=payload,
        )
        json_str = envelope.model_dump_json()
        parsed = EventEnvelope[TierDetectionPayload].model_validate_json(json_str)
        assert parsed.payload.result.score == 0.85
        assert parsed.payload.result.label == DetectionLabel.LIKELY_CLONE

    def test_risk_event_envelope(self) -> None:
        payload = RiskEventPayload(
            call_id="call-300",
            risk_score=88,
            band=RiskBand.CRITICAL,
            verdict=RiskVerdict.LIKELY_CLONE,
            requires_out_of_band=True,
            explanation="Critical voice clone detected on high-value transfer.",
        )
        envelope = EventEnvelope[RiskEventPayload](
            header=EventHeader(correlation_id="call-300", event_type="risk.events"),
            payload=payload,
        )
        json_str = envelope.model_dump_json()
        parsed = EventEnvelope[RiskEventPayload].model_validate_json(json_str)
        assert parsed.payload.risk_score == 88
        assert parsed.payload.band == RiskBand.CRITICAL
        assert parsed.payload.requires_out_of_band is True

    def test_workflow_event_envelope(self) -> None:
        payload = WorkflowEventPayload(
            call_id="call-400",
            decision=Decision.BLOCK,
            reason="High probability deepfake voice",
            action_taken="CALL_DISCONNECTED_AND_FLAGGED",
        )
        envelope = EventEnvelope[WorkflowEventPayload](
            header=EventHeader(correlation_id="call-400", event_type="workflow.events"),
            payload=payload,
        )
        json_str = envelope.model_dump_json()
        parsed = EventEnvelope[WorkflowEventPayload].model_validate_json(json_str)
        assert parsed.payload.decision == Decision.BLOCK

    def test_audit_event_envelope(self) -> None:
        payload = AuditEventPayload(
            call_id="call-500",
            block_index=1,
            block_type=AuditBlockType.RISK_SCORE,
            block_hash="000abc123",
            payload_hash="def456",
            summary="Risk packet anchored",
        )
        envelope = EventEnvelope[AuditEventPayload](
            header=EventHeader(correlation_id="call-500", event_type="audit.events"),
            payload=payload,
        )
        json_str = envelope.model_dump_json()
        parsed = EventEnvelope[AuditEventPayload].model_validate_json(json_str)
        assert parsed.payload.block_type == AuditBlockType.RISK_SCORE

    def test_dead_letter_envelope(self) -> None:
        payload = DeadLetterPayload(
            original_topic="vaani.detection.tier1",
            original_payload='{"bad": "json"}',
            error_message="Schema validation error",
            error_class="ValidationError",
            retry_count=3,
        )
        envelope = EventEnvelope[DeadLetterPayload](
            header=EventHeader(correlation_id="call-err", event_type="deadletter"),
            payload=payload,
        )
        json_str = envelope.model_dump_json()
        parsed = EventEnvelope[DeadLetterPayload].model_validate_json(json_str)
        assert parsed.payload.error_class == "ValidationError"
        assert parsed.payload.retry_count == 3
