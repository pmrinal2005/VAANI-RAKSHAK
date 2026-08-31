# ==============================================================================
# VAANI-RAKSHAK - End-to-End Pipeline Integration Test Suite (Phase 10)
# Validates complete end-to-end flows across all Phase 0-9 subsystems:
# REST Scoring -> Cascade -> Fusion -> Policy -> Kafka -> Audit -> WebSocket / SSE
# ==============================================================================

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.enums import AuditBlockType, Decision, RiskBand, RiskVerdict
from app.integrations.audit.ledger import CryptographicAuditLedger
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestE2ERestScoringToAudit:
    """
    E2E Flow 1:
    POST /api/v1/score → Cascade → Fusion → Policy → Kafka → Audit Ledger → Verification
    """

    def test_e2e_scoring_authentic_call_to_audit_proof(self, client: TestClient) -> None:
        call_id = "call-e2e-auth-01"
        payload = {
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
                "transactionValueInr": 5000,
                "callerAni": "+919876543210",
                "aniReputationScore": 95,
            },
            "scenarioOverride": "LOW_RISK",
        }

        # 1. Execute Scoring API
        score_res = client.post("/api/v1/score", json=payload)
        assert score_res.status_code == 200
        score_data = score_res.json()

        assert score_data["band"] == RiskBand.LOW.value
        assert score_data["verdict"] == RiskVerdict.AUTHENTIC.value
        assert score_data["recommendedAction"] == Decision.ALLOW.value
        assert score_data["riskScore"] < 30
        assert "shap" in score_data
        assert "tiers" in score_data

        # 2. Verify Cryptographic Audit Ledger Trail
        trail_res = client.get(f"/api/v1/audit/calls/{call_id}")
        assert trail_res.status_code == 200
        trail = trail_res.json()
        assert len(trail) >= 1
        block = trail[0]
        assert block["callId"] == call_id
        assert block["segmentId"] == "seg-001"
        assert "payloadHash" in block
        assert len(block["payloadHash"]) == 64
        assert len(block["hash"]) == 64
        # Verify privacy: Raw audio & Base64 audio must NEVER be stored
        assert "rawPcmB64" not in str(block)

        # 3. Export Verifiable Audit Proof Bundle for R4
        proof_res = client.get(f"/api/v1/audit/proof/{call_id}")
        assert proof_res.status_code == 200
        proof = proof_res.json()
        assert proof["callId"] == call_id
        assert proof["blockCount"] >= 1
        assert proof["isValid"] is True
        assert "chainHeadHash" in proof

        # 4. Verify Entire Hash Chain Cryptographic Integrity
        verify_res = client.get("/api/v1/audit/verify")
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["isValid"] is True
        assert verify_data["tamperedBlockIndex"] is None

    def test_e2e_scoring_critical_clone_triggers_block(self, client: TestClient) -> None:
        call_id = "call-e2e-clone-01"
        payload = {
            "segment": {
                "callId": call_id,
                "segmentId": "seg-002",
                "features": {
                    "spectralFlatnessVoiced": 0.45,
                    "hfEnergyRatio": 0.25,
                    "jitter": 0.035,
                    "shimmer": 0.15,
                    "f0RangeHz": 12.0,
                },
            },
            "context": {
                "transactionType": "fund_transfer",
                "transactionValueInr": 500000,
                "callerAni": "+919876500000",
                "aniReputationScore": 20,
            },
            "scenarioOverride": "CRITICAL_RISK",
        }

        score_res = client.post("/api/v1/score", json=payload)
        assert score_res.status_code == 200
        score_data = score_res.json()

        assert score_data["band"] == RiskBand.CRITICAL.value
        assert score_data["verdict"] == RiskVerdict.LIKELY_CLONE.value
        assert score_data["recommendedAction"] == Decision.BLOCK.value
        assert score_data["riskScore"] >= 80


class TestE2EWebSocketCallStreaming:
    """
    E2E Flow 2:
    WebSocket /api/v1/ws/calls/{call_id} -> Audio chunk -> Cascade
    -> Fusion -> Policy -> Detection response
    """

    def test_websocket_streaming_authentic_to_clone(self, client: TestClient) -> None:
        call_id = "call-e2e-ws-stream-01"

        with client.websocket_connect(f"/api/v1/ws/calls/{call_id}") as ws:
            # 1. Receive connection handshake
            greeting = ws.receive_json()
            assert greeting["type"] == "connection_established"
            assert greeting["callId"] == call_id

            # 2. Send ping, verify pong
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"

            # 3. Stream Chunk 1: Authentic audio segment
            chunk1 = {
                "type": "audio_chunk",
                "request": {
                    "segment": {
                        "callId": call_id,
                        "segmentId": "chunk-01",
                        "sampleRate": 16000,
                    },
                    "scenarioOverride": "LOW_RISK",
                },
            }
            ws.send_json(chunk1)
            resp1 = None
            for _ in range(5):
                msg = ws.receive_json()
                if msg.get("type") == "detection_result":
                    resp1 = msg
                    break
            assert resp1 is not None
            assert resp1["callId"] == call_id
            payload1 = resp1["payload"]
            assert payload1["band"] == RiskBand.LOW.value
            assert payload1["recommendedAction"] == Decision.ALLOW.value

            # 4. Stream Chunk 2: Synthetic clone attack
            chunk2 = {
                "type": "audio_chunk",
                "request": {
                    "segment": {
                        "callId": call_id,
                        "segmentId": "chunk-02",
                        "sampleRate": 16000,
                    },
                    "scenarioOverride": "CRITICAL_RISK",
                },
            }
            ws.send_json(chunk2)
            resp2 = None
            for _ in range(5):
                msg = ws.receive_json()
                if msg.get("type") == "detection_result":
                    resp2 = msg
                    break
            assert resp2 is not None
            payload2 = resp2["payload"]
            assert payload2["band"] == RiskBand.CRITICAL.value
            assert payload2["recommendedAction"] in (Decision.BLOCK.value, Decision.HOLD.value)


class TestE2ETelephonySimulationToSOCStreaming:
    """
    E2E Flow 3:
    POST /api/v1/calls/simulate → CallSessionManager → TelephonySimulator → Kafka → SOC Broadcast
    """

    def test_telephony_simulation_lifecycle_and_status(self, client: TestClient) -> None:
        call_id = "call-e2e-telephony-sim-01"

        # 1. Start simulation session
        sim_req = {
            "callId": call_id,
            "callerNumber": "+919876543210",
            "claimedSpeaker": "Rahul Roy",
            "pattern": "AUTHENTIC_TO_CLONE",
            "totalDurationSec": 6.0,
            "chunkDurationSec": 1.0,
            "playbackSpeed": 10.0,
        }
        start_res = client.post("/api/v1/calls/simulate", json=sim_req)
        assert start_res.status_code == 202
        start_data = start_res.json()
        assert start_data["callId"] == call_id
        assert start_data["status"] in ("ACTIVE", "RINGING")
        assert start_data["pattern"] == "AUTHENTIC_TO_CLONE"

        # 2. Verify session status tracking
        status_res = client.get(f"/api/v1/calls/{call_id}/status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["callId"] == call_id
        assert "riskHistory" in status_data
        assert "verdictHistory" in status_data
        assert "actionHistory" in status_data

        # 3. Verify session appears in active calls list
        list_res = client.get("/api/v1/calls")
        assert list_res.status_code == 200
        calls_list = list_res.json()
        assert any(c["callId"] == call_id for c in calls_list)

        # 4. Stop simulation
        stop_res = client.post(f"/api/v1/calls/{call_id}/stop")
        assert stop_res.status_code == 200
        assert stop_res.json()["status"] in ("COMPLETED", "INTERCEPTED", "ACTIVE")

    def test_soc_global_events_websocket_and_sse(self, client: TestClient) -> None:
        # Verify SOC WebSocket connects, reads greeting, and answers ping
        with client.websocket_connect("/api/v1/ws/events") as ws:
            greeting = ws.receive_json()
            assert greeting["type"] == "connection_established"
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"


class TestE2EAuditIntegrityAndTampering:
    """
    E2E Flow 4:
    Audit Block Chaining → Cryptographic Verification → Controlled Tamper Detection
    """

    @pytest.mark.asyncio
    async def test_audit_ledger_tampering_detection(self) -> None:
        ledger = CryptographicAuditLedger()

        # Append two valid blocks
        await ledger.append_block(
            event_type=AuditBlockType.RISK_SCORE,
            payload_plaintext={"callId": "call-tamper-e2e", "score": 25},
            summary="Authentic chunk",
            call_id="call-tamper-e2e",
        )
        await ledger.append_block(
            event_type=AuditBlockType.RISK_SCORE,
            payload_plaintext={"callId": "call-tamper-e2e", "score": 85},
            summary="Clone detected",
            call_id="call-tamper-e2e",
        )

        # 1. Verify healthy chain
        is_valid_initial, broken_idx, _ = await ledger.verify_chain()
        assert is_valid_initial is True
        assert broken_idx is None

        # 2. Tamper block at index 1
        ledger.tamper_block(index=1, new_payload="ILLEGALLY_MODIFIED_RISK_PAYLOAD")

        # 3. Verify tamper detection pinpoints the exact corrupted block index
        is_valid_after, broken_after, msg = await ledger.verify_chain()
        assert is_valid_after is False
        assert broken_after == 1
        assert "Tampered block hash at index 1" in str(msg)


class TestE2ESecurityHardeningAndDegradation:
    """
    E2E Flow 5:
    Security Headers • Request Size Limits (413) • Token Bucket Rate Limiting (429) • Profiling
    """

    def test_security_and_profiling_headers(self, client: TestClient) -> None:
        res = client.get("/api/v1/health/live")
        assert res.status_code == 200

        # Security headers
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "default-src 'none'" in res.headers.get("Content-Security-Policy", "")

        # Latency Profiling headers
        assert "X-Response-Time" in res.headers
        assert "Server-Timing" in res.headers

    def test_oversized_payload_rejection_413(self, client: TestClient) -> None:
        headers = {"Content-Length": str(100 * 1024 * 1024)}  # 100MB
        res = client.post("/api/v1/score", content=b"{}", headers=headers)
        assert res.status_code == 413
        assert res.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"

    def test_mock_scenario_failure_degradation(self, client: TestClient) -> None:
        # Test model timeout degradation scenario
        payload: dict[str, Any] = {
            "segment": {"callId": "call-degrade-01", "segmentId": "seg-001"},
            "scenarioOverride": "MODEL_TIMEOUT",
        }
        res = client.post("/api/v1/score", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "riskScore" in data
        assert "verdict" in data
