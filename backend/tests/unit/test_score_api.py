# ==============================================================================
# Unit & Integration tests — Production Scoring REST API
# Verifies POST /api/v1/score and POST /api/v1/score/upload endpoints.
# ==============================================================================

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_audit_ledger, get_event_producer
from app.core.config import get_settings
from app.domain.topics import KafkaTopic
from app.main import create_app
from app.messaging.producer import MockEventProducer


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestScoreJsonEndpoint:
    """Test POST /api/v1/score with JSON payloads."""

    def test_score_low_risk_authentic(self, client: TestClient) -> None:
        payload = {
            "segment": {
                "callId": "call-api-01",
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
                "transactionType": "balance-inquiry",
                "transactionValueInr": 0,
                "knownContact": True,
                "aniReputation": 0.85,
            },
            "scenarioOverride": "LOW_RISK",
        }
        res = client.post("/api/v1/score", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["riskScore"] < 40
        assert data["band"] == "LOW"
        assert data["verdict"] == "AUTHENTIC"
        assert data["recommendedAction"] == "ALLOW"
        assert data["requiresOutOfBand"] is False
        assert len(data["tiers"]) == 3
        assert len(data["shap"]) >= 1

    def test_score_critical_risk_clone(self, client: TestClient) -> None:
        payload = {
            "segment": {
                "callId": "call-api-02",
                "segmentId": "seg-001",
                "features": {
                    "spectralFlatnessVoiced": 0.35,
                    "hfEnergyRatio": 0.18,
                    "jitter": 0.0008,
                    "shimmer": 0.005,
                    "f0RangeHz": 12.0,
                },
            },
            "context": {
                "transactionType": "wire-transfer",
                "transactionValueInr": 500000,
                "knownContact": False,
                "aniReputation": 0.20,
            },
            "scenarioOverride": "CRITICAL_RISK",
        }
        res = client.post("/api/v1/score", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["riskScore"] >= 85
        assert data["band"] == "CRITICAL"
        assert data["verdict"] == "LIKELY_CLONE"
        assert data["recommendedAction"] == "BLOCK"
        assert data["requiresOutOfBand"] is True

    def test_score_tier_disagreement_escalation(self, client: TestClient) -> None:
        payload = {
            "segment": {"callId": "call-api-03", "segmentId": "seg-001"},
            "context": {"transactionType": "login", "transactionValueInr": 0},
            "scenarioOverride": "TIER_DISAGREEMENT",
        }
        res = client.post("/api/v1/score", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["riskScore"] >= 65
        # Verify Tier 2 was invoked
        tier2 = next((t for t in data["tiers"] if t["tier"] == 2), None)
        assert tier2 is not None
        assert tier2["invoked"] is True

    def test_score_speaker_mismatch(self, client: TestClient) -> None:
        payload = {
            "segment": {"callId": "call-api-04", "segmentId": "seg-001"},
            "context": {
                "claimedSpeaker": "Rahul Roy",
                "transactionType": "inquiry",
                "transactionValueInr": 5000,
            },
            "scenarioOverride": "SPEAKER_MISMATCH",
        }
        res = client.post("/api/v1/score", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["requiresOutOfBand"] is True
        assert data["recommendedAction"] in ("CHALLENGE", "BLOCK")

    def test_score_invalid_payload(self, client: TestClient) -> None:
        res = client.post("/api/v1/score", json={"bad": "request"})
        assert res.status_code == 422


class TestScoreUploadEndpoint:
    """Test POST /api/v1/score/upload with multipart form data."""

    def test_score_upload_wav_file(self, client: TestClient) -> None:
        # Create a dummy 16-bit PCM WAV in memory (1 second of silence)
        wav_buffer = io.BytesIO()
        # Minimal valid WAV header (44 bytes) + 16000 samples (32000 bytes)
        header = (
            b"RIFF\x24\x7d\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
            b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00}\x00\x00"
        )
        wav_buffer.write(header)
        wav_buffer.write(b"\x00" * 32000)
        wav_buffer.seek(0)

        files = {"file": ("test_call.wav", wav_buffer, "audio/wav")}
        ctx_data = {"transactionType": "funds-transfer", "transactionValueInr": 50000}
        data = {
            "context_json": json.dumps(ctx_data),
            "scenario": "LOW_RISK",
        }

        res = client.post("/api/v1/score/upload", files=files, data=data)
        assert res.status_code == 200
        result = res.json()
        assert "riskScore" in result
        assert "band" in result
        assert "verdict" in result
        assert "tiers" in result

    def test_score_upload_invalid_mime_type(self, client: TestClient) -> None:
        text_buffer = io.BytesIO(b"Not an audio file")
        files = {"file": ("test.exe", text_buffer, "application/x-msdownload")}
        res = client.post("/api/v1/score/upload", files=files)
        assert res.status_code == 400
        assert "Unsupported file format" in res.json()["detail"]

    def test_score_upload_empty_file(self, client: TestClient) -> None:
        empty_buffer = io.BytesIO(b"")
        files = {"file": ("empty.wav", empty_buffer, "audio/wav")}
        res = client.post("/api/v1/score/upload", files=files)
        assert res.status_code == 400
        assert "empty" in res.json()["detail"].lower()

    def test_score_upload_invalid_context_json(self, client: TestClient) -> None:
        wav_buffer = io.BytesIO(b"RIFF\x24\x00\x00\x00WAVE" + b"\x00" * 100)
        files = {"file": ("test.wav", wav_buffer, "audio/wav")}
        data = {"context_json": "INVALID_JSON{{{"}
        res = client.post("/api/v1/score/upload", files=files, data=data)
        assert res.status_code == 422


class TestScoreKafkaAndAuditIntegration:
    """Verify events are published to mock event bus and blocks added to audit ledger."""

    @pytest.mark.asyncio
    async def test_kafka_event_and_audit_block_logged(self, client: TestClient) -> None:
        settings = get_settings()
        producer = get_event_producer(settings)
        ledger = get_audit_ledger(settings)

        payload = {
            "segment": {"callId": "call-event-verify-01", "segmentId": "seg-001"},
            "context": {"transactionType": "wire-transfer", "transactionValueInr": 600000},
            "scenarioOverride": "CRITICAL_RISK",
        }
        res = client.post("/api/v1/score", json=payload)
        assert res.status_code == 200

        # Verify MockEventProducer received the published event
        if isinstance(producer, MockEventProducer):
            published_fusion_events = producer.get_published_events(KafkaTopic.FUSION_RESULT)
            assert len(published_fusion_events) >= 1
            call_ids = [e.header.correlation_id for e in published_fusion_events]
            assert "call-event-verify-01" in call_ids

        # Verify audit ledger has blocks
        blocks = await ledger.get_blocks()
        assert len(blocks) >= 2  # Genesis + at least 1 risk block
