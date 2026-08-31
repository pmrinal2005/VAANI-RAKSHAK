# ==============================================================================
# Unit & Integration tests — Cryptographic Audit Ledger & R4 Boundary API
# Verifies CryptographicAuditLedger, SHA-256 chaining, proof generation, & REST routes.
# ==============================================================================

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domain.enums import AuditBlockType
from app.integrations.audit.ledger import CryptographicAuditLedger
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestCryptographicAuditLedger:
    """Test cryptographic SHA-256 audit ledger functionality."""

    @pytest.mark.asyncio
    async def test_genesis_block_and_chain_integrity(self) -> None:
        ledger = CryptographicAuditLedger()
        blocks = await ledger.get_blocks()
        assert len(blocks) == 1

        genesis = blocks[0]
        assert genesis.index == 0
        assert genesis.type == AuditBlockType.GENESIS
        assert genesis.prev_hash == "0" * 64
        assert len(genesis.hash) == 64
        assert len(genesis.payload_hash) == 64

        is_valid, broken_idx, _ = await ledger.verify_chain()
        assert is_valid is True
        assert broken_idx is None

    @pytest.mark.asyncio
    async def test_append_blocks_and_hash_continuity(self) -> None:
        ledger = CryptographicAuditLedger()

        b1 = await ledger.append_block(
            event_type=AuditBlockType.RISK_SCORE,
            payload_plaintext={"riskScore": 25, "verdict": "AUTHENTIC"},
            summary="Low risk authentic call segment",
            call_id="call-audit-01",
            segment_id="seg-001",
            risk_score=25,
        )
        assert b1.index == 1
        assert b1.prev_hash == (await ledger.get_block_by_index(0)).hash  # type: ignore[union-attr]
        assert b1.call_id == "call-audit-01"

        b2 = await ledger.append_block(
            event_type=AuditBlockType.ESCALATION,
            payload_plaintext={"action": "BLOCK", "reason": "Clone detected"},
            summary="Zero-trust supervisor block",
            call_id="call-audit-01",
            segment_id="seg-002",
            risk_score=95,
        )
        assert b2.index == 2
        assert b2.prev_hash == b1.hash

        is_valid, broken_idx, _ = await ledger.verify_chain()
        assert is_valid is True
        assert broken_idx is None

    @pytest.mark.asyncio
    async def test_tamper_detection_flags_corrupted_block(self) -> None:
        ledger = CryptographicAuditLedger()

        await ledger.append_block(
            event_type=AuditBlockType.RISK_SCORE,
            payload_plaintext={"riskScore": 10},
            summary="Authentic",
            call_id="call-tamper-01",
        )
        await ledger.append_block(
            event_type=AuditBlockType.RISK_SCORE,
            payload_plaintext={"riskScore": 90},
            summary="Synthetic clone",
            call_id="call-tamper-01",
        )

        # Verify initial chain is valid
        is_valid, _, _ = await ledger.verify_chain()
        assert is_valid is True

        # Tamper block at index 1
        ledger.tamper_block(index=1, new_payload="FRAUDULENTLY_ALTERED_PAYLOAD")

        # Verify tamper detection flags exact index
        is_valid_after, broken_idx, msg = await ledger.verify_chain()
        assert is_valid_after is False
        assert broken_idx == 1
        assert "Tampered block hash at index 1" in str(msg)

    @pytest.mark.asyncio
    async def test_generate_call_proof_bundle(self) -> None:
        ledger = CryptographicAuditLedger()

        await ledger.append_block(
            event_type=AuditBlockType.RISK_SCORE,
            payload_plaintext={"riskScore": 30},
            summary="Initial chunk",
            call_id="call-proof-test",
            segment_id="seg-01",
        )
        await ledger.append_block(
            event_type=AuditBlockType.OOB_CHALLENGE,
            payload_plaintext={"decision": "ALLOW"},
            summary="Policy allow",
            call_id="call-proof-test",
            segment_id="seg-02",
        )

        proof = await ledger.generate_call_proof("call-proof-test")
        assert proof is not None
        assert proof.call_id == "call-proof-test"
        assert proof.block_count == 2
        assert proof.is_valid is True
        assert proof.chain_head_index == 2
        assert len(proof.chain_head_hash) == 64

        # Non-existent call returns None
        assert await ledger.generate_call_proof("non-existent-call") is None


class TestAuditRestApiEndpoints:
    """Test REST API routes in app/api/routes/audit.py."""

    def test_list_blocks_and_query_genesis(self, client: TestClient) -> None:
        res = client.get("/api/v1/audit/blocks")
        assert res.status_code == 200
        blocks = res.json()
        assert len(blocks) >= 1
        assert blocks[0]["index"] == 0
        assert blocks[0]["type"] == "GENESIS"

    def test_get_block_by_index(self, client: TestClient) -> None:
        res = client.get("/api/v1/audit/blocks/0")
        assert res.status_code == 200
        data = res.json()
        assert data["index"] == 0
        assert data["type"] == "GENESIS"
        assert "prevHash" in data
        assert "payloadHash" in data

        # Non-existent block returns 404
        res_404 = client.get("/api/v1/audit/blocks/999999")
        assert res_404.status_code == 404

    def test_verify_chain_endpoint(self, client: TestClient) -> None:
        res = client.get("/api/v1/audit/verify")
        assert res.status_code == 200
        data = res.json()
        assert data["isValid"] is True
        assert data["totalBlocks"] >= 1
        assert data["tamperedBlockIndex"] is None

    def test_call_audit_trail_and_proof_endpoints(self, client: TestClient) -> None:
        call_id = "call-api-audit-trail-01"

        # Score a segment to generate an audit record
        score_payload = {
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
        }
        score_res = client.post("/api/v1/score", json=score_payload)
        assert score_res.status_code == 200

        # Retrieve call audit trail
        trail_res = client.get(f"/api/v1/audit/calls/{call_id}")
        assert trail_res.status_code == 200
        trail = trail_res.json()
        assert len(trail) >= 1
        assert trail[0]["callId"] == call_id

        # Generate cryptographic audit proof bundle
        proof_res = client.get(f"/api/v1/audit/proof/{call_id}")
        assert proof_res.status_code == 200
        proof = proof_res.json()
        assert proof["callId"] == call_id
        assert proof["blockCount"] >= 1
        assert proof["isValid"] is True
        assert "chainHeadHash" in proof

    def test_proof_for_non_existent_call_returns_404(self, client: TestClient) -> None:
        res = client.get("/api/v1/audit/proof/non-existent-call-xyz")
        assert res.status_code == 404
