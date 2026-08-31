# ==============================================================================
# VAANI-RAKSHAK — Telephony Simulation Session & State Management
# Tracks simulated RTP/SIP telephony calls, chunk indices, and risk trajectories.
# ==============================================================================

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import MockScenario, RiskBand, RiskVerdict
from app.schemas.context import CallContext


class CallStatus(StrEnum):
    """Lifecycle state of a simulated telephony call."""

    IDLE = "IDLE"
    RINGING = "RINGING"
    ACTIVE = "ACTIVE"
    INTERCEPTED = "INTERCEPTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SimulationPattern(StrEnum):
    """Temporal risk trajectory pattern for simulated telephony sessions."""

    STEADY = "STEADY"  # Constant scenario throughout the call
    AUTHENTIC_TO_CLONE = "AUTHENTIC_TO_CLONE"  # Starts authentic, injects clone mid-call
    CLONE_BURST = "CLONE_BURST"  # Authentic -> brief clone burst -> authentic
    SPEAKER_TAKEOVER = "SPEAKER_TAKEOVER"  # Voiceprint changes abruptly to unauthorized speaker


class SimulationRequest(BaseModel):
    """Parameters for launching an asynchronous simulated call session."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str | None = Field(default=None, alias="callId")
    caller_number: str = Field(default="+919876543210", alias="callerNumber")
    claimed_speaker: str | None = Field(default="Rahul Roy", alias="claimedSpeaker")
    scenario: MockScenario | None = Field(default=MockScenario.LOW_RISK)
    pattern: SimulationPattern = Field(default=SimulationPattern.STEADY)
    total_duration_sec: float = Field(default=10.0, ge=1.0, le=300.0, alias="totalDurationSec")
    chunk_duration_sec: float = Field(default=1.0, ge=0.5, le=5.0, alias="chunkDurationSec")
    playback_speed: float = Field(default=1.0, ge=0.1, le=100.0, alias="playbackSpeed")
    context: CallContext = Field(default_factory=CallContext)


class SimulationStatusResponse(BaseModel):
    """Live status and temporal risk summary for a simulated call session."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str = Field(..., alias="callId")
    status: CallStatus
    pattern: SimulationPattern
    total_duration_sec: float = Field(..., alias="totalDurationSec")
    processed_duration_sec: float = Field(..., alias="processedDurationSec")
    current_segment_index: int = Field(..., alias="currentSegmentIndex")
    current_risk_score: int = Field(..., alias="currentRiskScore")
    current_band: RiskBand = Field(..., alias="currentBand")
    current_verdict: RiskVerdict = Field(..., alias="currentVerdict")
    recommended_action: str = Field(..., alias="recommendedAction")
    requires_out_of_band: bool = Field(..., alias="requiresOutOfBand")
    risk_history: list[int] = Field(default_factory=list, alias="riskHistory")
    verdict_history: list[str] = Field(default_factory=list, alias="verdictHistory")
    action_history: list[str] = Field(default_factory=list, alias="actionHistory")
    websocket_url: str = Field(..., alias="websocketUrl")
    started_at: datetime = Field(..., alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class CallSimulationSession:
    """Internal mutable tracking state for an active/completed simulated call."""

    def __init__(self, request: SimulationRequest) -> None:
        self.call_id = request.call_id or f"telephony-{uuid.uuid4().hex[:8]}"
        self.request = request
        self.status = CallStatus.RINGING
        self.pattern = request.pattern
        self.total_duration_sec = request.total_duration_sec
        self.chunk_duration_sec = request.chunk_duration_sec
        self.playback_speed = request.playback_speed
        self.current_segment_index = 0
        self.processed_duration_sec = 0.0
        self.current_risk_score = 0
        self.current_band = RiskBand.LOW
        self.current_verdict = RiskVerdict.AUTHENTIC
        self.recommended_action = "ALLOW"
        self.requires_out_of_band = False
        self.risk_history: list[int] = []
        self.verdict_history: list[str] = []
        self.action_history: list[str] = []
        self.started_at = datetime.now(UTC)
        self.completed_at: datetime | None = None
        self.task: asyncio.Task[None] | None = None

    def to_status_response(self, api_prefix: str = "/api/v1") -> SimulationStatusResponse:
        return SimulationStatusResponse(
            call_id=self.call_id,
            status=self.status,
            pattern=self.pattern,
            total_duration_sec=self.total_duration_sec,
            processed_duration_sec=round(self.processed_duration_sec, 2),
            current_segment_index=self.current_segment_index,
            current_risk_score=self.current_risk_score,
            current_band=self.current_band,
            current_verdict=self.current_verdict,
            recommended_action=self.recommended_action,
            requires_out_of_band=self.requires_out_of_band,
            risk_history=list(self.risk_history),
            verdict_history=list(self.verdict_history),
            action_history=list(self.action_history),
            websocket_url=f"{api_prefix}/ws/calls/{self.call_id}",
            started_at=self.started_at,
            completed_at=self.completed_at,
        )


class CallSessionManager:
    """Singleton manager tracking simulated telephony call sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, CallSimulationSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, request: SimulationRequest) -> CallSimulationSession:
        """Create and register a new call session."""
        session = CallSimulationSession(request)
        async with self._lock:
            self._sessions[session.call_id] = session
        return session

    def get_session(self, call_id: str) -> CallSimulationSession | None:
        """Retrieve a session by its call ID."""
        return self._sessions.get(call_id)

    def list_sessions(self, active_only: bool = False) -> list[CallSimulationSession]:
        """List all sessions, optionally filtering for active ones."""
        sessions = list(self._sessions.values())
        if active_only:
            return [s for s in sessions if s.status in (CallStatus.ACTIVE, CallStatus.RINGING)]
        return sessions

    async def stop_session(self, call_id: str) -> bool:
        """Cancel the running task for a session and mark completed."""
        session = self._sessions.get(call_id)
        if session is None:
            return False

        if session.task and not session.task.done():
            session.task.cancel()

        if session.status in (CallStatus.RINGING, CallStatus.ACTIVE):
            session.status = CallStatus.COMPLETED
            session.completed_at = datetime.now(UTC)

        return True
