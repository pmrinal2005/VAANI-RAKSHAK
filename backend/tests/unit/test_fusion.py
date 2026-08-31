# ==============================================================================
# Unit tests — Multi-Modal Fusion Engine
# Verifies acoustic + prosody + speaker + context fusion, risk banding, and SHAP explainability.
# ==============================================================================

from __future__ import annotations

import pytest

from app.domain.enums import (
    DetectionLabel,
    DetectionStatus,
    RiskBand,
    RiskVerdict,
)
from app.fusion.engine import MultiModalFusionEngine
from app.schemas.audio import AudioFeatures, AudioSegment
from app.schemas.context import CallContext
from app.schemas.detection import (
    DetectionResult,
    FusionInput,
    SignalVote,
    SpeakerCheckResult,
)


@pytest.fixture
def fusion_engine() -> MultiModalFusionEngine:
    return MultiModalFusionEngine()


class TestMultiModalFusion:
    """Verify calibrated risk scoring and categorical banding across multi-modal inputs."""

    @pytest.mark.asyncio
    async def test_authentic_low_risk_fusion(
        self, fusion_engine: MultiModalFusionEngine
    ) -> None:
        """Clean authentic voice -> score < 40, LOW band, AUTHENTIC verdict, ALLOW."""
        input_data = FusionInput(
            segment=AudioSegment(call_id="call-low", segment_id="seg-1"),
            features=AudioFeatures(),
            tier0_result=DetectionResult(
                tier=0,
                score=0.10,
                confidence=0.95,
                label=DetectionLabel.AUTHENTIC,
                latency_ms=1.2,
                model_name="mock-tier0",
                model_version="1.0",
                status=DetectionStatus.SUCCESS,
            ),
            tier1_result=DetectionResult(
                tier=1,
                score=0.0,
                confidence=1.0,
                label=DetectionLabel.AUTHENTIC,
                latency_ms=0.0,
                model_name="tier1-skipped",
                model_version="1.0",
                status=DetectionStatus.SKIPPED,
            ),
            prosody_vote=SignalVote(
                id="prosody",
                label="Prosody",
                score=0.10,
                weight=0.15,
                detail="Low pitch deviation",
            ),
            speaker_check=SpeakerCheckResult(
                enrolled=True,
                claimed_speaker="Rahul Roy",
                cosine_similarity=0.88,
                mismatch=False,
            ),
            context=CallContext(transaction_type="balance-inquiry", transaction_value_inr=0),
        )

        output = await fusion_engine.fuse(input_data)

        assert output.risk_score < 40
        assert output.band == RiskBand.LOW
        assert output.verdict == RiskVerdict.AUTHENTIC
        assert output.recommended_action == "ALLOW"
        assert output.requires_out_of_band is False
        assert len(output.shap) >= 1
        assert len(output.votes) >= 2

    @pytest.mark.asyncio
    async def test_deepfake_critical_risk_fusion(
        self, fusion_engine: MultiModalFusionEngine
    ) -> None:
        """High confidence synthetic clone on high-value transfer -> CRITICAL band, BLOCK, OOB."""
        input_data = FusionInput(
            segment=AudioSegment(call_id="call-crit", segment_id="seg-1"),
            features=AudioFeatures(),
            tier0_result=DetectionResult(
                tier=0,
                score=0.85,
                confidence=0.90,
                label=DetectionLabel.LIKELY_CLONE,
                latency_ms=2.5,
                model_name="mock-tier0",
                model_version="1.0",
                status=DetectionStatus.SUCCESS,
            ),
            tier1_result=DetectionResult(
                tier=1,
                score=0.92,
                confidence=0.95,
                label=DetectionLabel.LIKELY_CLONE,
                latency_ms=18.0,
                model_name="mock-tier1",
                model_version="1.0",
                status=DetectionStatus.SUCCESS,
            ),
            tier2_result=DetectionResult(
                tier=2,
                score=0.95,
                confidence=0.98,
                label=DetectionLabel.LIKELY_CLONE,
                latency_ms=75.0,
                model_name="mock-tier2",
                model_version="1.0",
                status=DetectionStatus.SUCCESS,
            ),
            prosody_vote=SignalVote(
                id="prosody",
                label="Prosody",
                score=0.80,
                weight=0.15,
                detail="Monotone synthetic prosody",
            ),
            speaker_check=SpeakerCheckResult(
                enrolled=True,
                claimed_speaker="Priya Sharma",
                cosine_similarity=0.42,
                mismatch=True,
            ),
            context=CallContext(
                transaction_type="wire-transfer",
                transaction_value_inr=500_000,
                known_contact=False,
                ani_reputation=0.15,
            ),
        )

        output = await fusion_engine.fuse(input_data)

        assert output.risk_score >= 85
        assert output.band == RiskBand.CRITICAL
        assert output.verdict == RiskVerdict.LIKELY_CLONE
        assert output.recommended_action == "BLOCK"
        assert output.requires_out_of_band is True

    @pytest.mark.asyncio
    async def test_degraded_tier_inconclusive_verdict(
        self, fusion_engine: MultiModalFusionEngine
    ) -> None:
        """When an active tier times out on moderate risk, surfaces INCONCLUSIVE verdict."""
        input_data = FusionInput(
            segment=AudioSegment(call_id="call-inc", segment_id="seg-1"),
            features=AudioFeatures(),
            tier0_result=DetectionResult(
                tier=0,
                score=0.50,
                confidence=0.0,
                label=DetectionLabel.INCONCLUSIVE,
                latency_ms=100.0,
                model_name="tier0-timeout",
                model_version="1.0",
                status=DetectionStatus.TIMEOUT,
                error="Timeout",
            ),
            tier1_result=DetectionResult(
                tier=1,
                score=0.45,
                confidence=0.60,
                label=DetectionLabel.SUSPICIOUS,
                latency_ms=15.0,
                model_name="mock-tier1",
                model_version="1.0",
                status=DetectionStatus.SUCCESS,
            ),
            prosody_vote=SignalVote(
                id="prosody",
                label="Prosody",
                score=0.30,
                weight=0.15,
                detail="Elevated jitter",
            ),
            context=CallContext(transaction_type="inquiry", transaction_value_inr=1000),
        )

        output = await fusion_engine.fuse(input_data)

        assert output.verdict == RiskVerdict.INCONCLUSIVE
