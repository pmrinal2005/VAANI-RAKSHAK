# ==============================================================================
# Unit & Integration tests — Simulated Real-Time Telephony Pipeline
# Verifies CallSessionManager, TelephonySimulator, and Call REST endpoints.
# ==============================================================================

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_audit_ledger,
    get_cascade_orchestrator,
    get_event_producer,
    get_explanation_engine,
    get_fusion_engine,
    get_language_router,
    get_policy_engine,
    get_prosody_detector,
    get_speaker_verifier,
    get_tier0_detector,
    get_tier1_detector,
    get_tier2_detector,
)
from app.core.config import get_settings
from app.domain.enums import MockScenario
from app.main import create_app
from app.schemas.context import CallContext
from app.telephony.session import (
    CallSessionManager,
    CallStatus,
    SimulationPattern,
    SimulationRequest,
)
from app.telephony.simulator import TelephonySimulator


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def simulator() -> TelephonySimulator:
    settings = get_settings()
    t0 = get_tier0_detector(settings)
    t1 = get_tier1_detector(settings)
    t2 = get_tier2_detector(settings)
    prosody = get_prosody_detector(settings)
    speaker = get_speaker_verifier(settings)
    lang = get_language_router(settings)
    orchestrator = get_cascade_orchestrator(
        tier0=t0,
        tier1=t1,
        tier2=t2,
        prosody=prosody,
        speaker=speaker,
        language=lang,
        settings=settings,
    )
    explanation = get_explanation_engine(settings)
    policy = get_policy_engine()
    fusion = get_fusion_engine(explanation, policy, settings)
    producer = get_event_producer(settings)
    audit = get_audit_ledger(settings)
    return TelephonySimulator(
        orchestrator=orchestrator,
        fusion_engine=fusion,
        event_producer=producer,
        audit_ledger=audit,
    )


class TestCallSessionManager:
    """Test unit behavior of the CallSessionManager."""

    @pytest.mark.asyncio
    async def test_session_lifecycle_crud(self) -> None:
        mgr = CallSessionManager()
        req = SimulationRequest(
            call_id="call-mgr-01",
            caller_number="+919876543210",
            total_duration_sec=5.0,
            chunk_duration_sec=1.0,
        )
        session = await mgr.create_session(req)
        assert session.call_id == "call-mgr-01"
        assert session.status == CallStatus.RINGING

        retrieved = mgr.get_session("call-mgr-01")
        assert retrieved is not None
        assert retrieved.call_id == "call-mgr-01"

        all_sessions = mgr.list_sessions(active_only=False)
        assert len(all_sessions) == 1

        active_sessions = mgr.list_sessions(active_only=True)
        assert len(active_sessions) == 1

        stopped = await mgr.stop_session("call-mgr-01")
        assert stopped is True
        assert session.status == CallStatus.COMPLETED

        # Non-existent session
        assert await mgr.stop_session("non-existent") is False
        assert mgr.get_session("non-existent") is None


class TestTelephonySimulatorExecution:
    """Test simulated continuous RTP audio chunk processing & temporal transitions."""

    @pytest.mark.asyncio
    async def test_steady_authentic_call_completes_normally(
        self, simulator: TelephonySimulator
    ) -> None:
        mgr = CallSessionManager()
        req = SimulationRequest(
            call_id="call-sim-steady",
            scenario=MockScenario.LOW_RISK,
            pattern=SimulationPattern.STEADY,
            total_duration_sec=3.0,
            chunk_duration_sec=1.0,
            playback_speed=50.0,  # Fast execution for tests
        )
        session = await mgr.create_session(req)
        await simulator.run_call(session)

        assert session.status == CallStatus.COMPLETED
        assert session.current_segment_index == 3
        assert len(session.risk_history) == 3
        assert all(score < 40 for score in session.risk_history)
        assert all(action == "ALLOW" for action in session.action_history)

    @pytest.mark.asyncio
    async def test_authentic_to_clone_triggers_interception_and_block(
        self, simulator: TelephonySimulator
    ) -> None:
        mgr = CallSessionManager()
        req = SimulationRequest(
            call_id="call-sim-midcall-clone",
            pattern=SimulationPattern.AUTHENTIC_TO_CLONE,
            total_duration_sec=5.0,
            chunk_duration_sec=1.0,
            playback_speed=50.0,
            context=CallContext(
                transaction_type="wire-transfer",
                transaction_value_inr=300000,
            ),
        )
        session = await mgr.create_session(req)
        await simulator.run_call(session)

        # Call should be intercepted and stopped prematurely
        assert session.status == CallStatus.INTERCEPTED
        assert session.current_risk_score >= 85
        assert session.recommended_action == "BLOCK"
        assert session.requires_out_of_band is True
        # Verify trajectory started authentic and escalated
        assert session.risk_history[0] < 40
        assert session.risk_history[-1] >= 85

    @pytest.mark.asyncio
    async def test_speaker_takeover_triggers_challenge(
        self, simulator: TelephonySimulator
    ) -> None:
        mgr = CallSessionManager()
        req = SimulationRequest(
            call_id="call-sim-takeover",
            pattern=SimulationPattern.SPEAKER_TAKEOVER,
            total_duration_sec=4.0,
            chunk_duration_sec=1.0,
            playback_speed=50.0,
            claimed_speaker="Rahul Roy",
            context=CallContext(
                claimed_speaker="Rahul Roy",
                transaction_type="inquiry",
                transaction_value_inr=5000,
            ),
        )
        session = await mgr.create_session(req)
        await simulator.run_call(session)

        assert session.status == CallStatus.COMPLETED
        assert session.current_segment_index == 4
        # In second half, speaker mismatch occurs
        assert session.requires_out_of_band is True
        assert session.action_history[-1] in ("CHALLENGE", "HOLD")


class TestTelephonyRestEndpoints:
    """Test POST /api/v1/calls/simulate, GET /status, POST /stop, GET /."""

    def test_start_and_get_simulation_status(self, client: TestClient) -> None:
        payload = {
            "callerNumber": "+919876543210",
            "claimedSpeaker": "Rahul Roy",
            "scenario": "LOW_RISK",
            "pattern": "STEADY",
            "totalDurationSec": 5.0,
            "chunkDurationSec": 1.0,
            "playbackSpeed": 50.0,
        }
        res = client.post("/api/v1/calls/simulate", json=payload)
        assert res.status_code == 202
        data = res.json()
        assert "callId" in data
        call_id = data["callId"]
        assert data["status"] in ("RINGING", "ACTIVE")
        assert "websocketUrl" in data

        # Inspect status
        status_res = client.get(f"/api/v1/calls/{call_id}/status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["callId"] == call_id

        # List calls
        list_res = client.get("/api/v1/calls")
        assert list_res.status_code == 200
        calls_list = list_res.json()
        assert len(calls_list) >= 1
        assert any(c["callId"] == call_id for c in calls_list)

        # Stop call
        stop_res = client.post(f"/api/v1/calls/{call_id}/stop")
        assert stop_res.status_code == 200
        stop_data = stop_res.json()
        assert stop_data["status"] == "COMPLETED"

    def test_get_non_existent_call_404(self, client: TestClient) -> None:
        res = client.get("/api/v1/calls/telephony-non-existent-999/status")
        assert res.status_code == 404

    def test_stop_non_existent_call_404(self, client: TestClient) -> None:
        res = client.post("/api/v1/calls/telephony-non-existent-999/stop")
        assert res.status_code == 404
