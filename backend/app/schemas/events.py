# ==============================================================================
# VAANI-RAKSHAK — Event Envelopes & Kafka Message Schemas
# Standardized Pydantic v2 event envelopes with OpenTelemetry-ready tracing.
# ALL EVENTS ARE KEYED BY call_id TO GUARANTEE PARTITION-LEVEL ORDERING.
# ==============================================================================

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from ulid import ULID

from app.domain.enums import AuditBlockType, Decision, RiskBand, RiskVerdict
from app.schemas.audio import AudioReference, AudioSegment
from app.schemas.context import CallContext
from app.schemas.detection import (
    DetectionResult,
    FusionOutput,
    LanguageRoutingResult,
    SignalVote,
    SpeakerCheckResult,
)

T = TypeVar("T")


class EventHeader(BaseModel):
    """Metadata header attached to every event published to Kafka."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    event_id: str = Field(
        default_factory=lambda: str(ULID()),
        alias="eventId",
        description="Unique event ULID",
    )
    correlation_id: str = Field(
        ...,
        alias="correlationId",
        description="Trace/Session identifier (typically call_id)",
    )
    event_type: str = Field(
        ...,
        alias="eventType",
        description="Logical event name, e.g. fusion.result",
    )
    trace_id: str = Field(
        default_factory=lambda: uuid4().hex,
        alias="traceId",
        description="Distributed tracing W3C trace ID",
    )
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        alias="occurredAt",
        description="Event emission timestamp in UTC",
    )
    producer: str = Field(default="vaani-backend", description="Originating service identifier")
    version: str = Field(default="1.0.0", description="Schema version of this event")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary routing metadata")


class EventEnvelope(BaseModel, Generic[T]):
    """Generic event container wrapping a strongly-typed payload with an EventHeader."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    header: EventHeader
    payload: T


# ------------------------------------------------------------------------------
# Concrete Event Payloads
# ------------------------------------------------------------------------------


class AudioIngestPayload(BaseModel):
    """Event emitted when a raw audio stream or file upload enters the system."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str = Field(..., alias="callId")
    channel: str
    audio_reference: AudioReference | str = Field(..., alias="audioReference")
    context: CallContext = Field(default_factory=CallContext)


class AudioSegmentPayload(BaseModel):
    """Event emitted when an audio stream is segmented into a discrete analysis chunk."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    segment: AudioSegment
    context: CallContext = Field(default_factory=CallContext)


class TierDetectionPayload(BaseModel):
    """Event emitted when a tier detector produces a detection score."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str = Field(..., alias="callId")
    segment_id: str = Field(..., alias="segmentId")
    result: DetectionResult


class ProsodyPayload(BaseModel):
    """Event emitted when prosodic biomarker extraction finishes."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str = Field(..., alias="callId")
    segment_id: str = Field(..., alias="segmentId")
    vote: SignalVote


class SpeakerPayload(BaseModel):
    """Event emitted when cross-session speaker verification finishes."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str = Field(..., alias="callId")
    segment_id: str = Field(..., alias="segmentId")
    result: SpeakerCheckResult


class LanguagePayload(BaseModel):
    """Event emitted when spoken language identification finishes."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str = Field(..., alias="callId")
    segment_id: str = Field(..., alias="segmentId")
    result: LanguageRoutingResult


class FusionResultPayload(BaseModel):
    """Event emitted when multi-modal acoustic & contextual fusion completes."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str = Field(..., alias="callId")
    segment_id: str = Field(..., alias="segmentId")
    output: FusionOutput


class RiskEventPayload(BaseModel):
    """High-level risk decision emitted for downstream UI dashboards & alerting."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str = Field(..., alias="callId")
    risk_score: int = Field(ge=0, le=100, alias="riskScore")
    band: RiskBand
    verdict: RiskVerdict
    requires_out_of_band: bool = Field(..., alias="requiresOutOfBand")
    explanation: str


class WorkflowEventPayload(BaseModel):
    """Operational workflow action (ALLOW, BLOCK, HOLD, CHALLENGE) dispatched to telephony/core."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str = Field(..., alias="callId")
    decision: Decision
    reason: str
    action_taken: str = Field(..., alias="actionTaken")


class AuditEventPayload(BaseModel):
    """Event dispatched to immutable audit ledger (R4 Boundary)."""

    model_config = ConfigDict(extra="ignore")

    call_id: str
    block_index: int
    block_type: AuditBlockType
    block_hash: str
    payload_hash: str
    summary: str


class DeadLetterPayload(BaseModel):
    """Poison-pill or unprocessable message redirected to the dead-letter queue."""

    model_config = ConfigDict(extra="ignore")

    original_topic: str
    original_payload: str | dict[str, Any]
    error_message: str
    error_class: str
    retry_count: int = 0
    failed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
