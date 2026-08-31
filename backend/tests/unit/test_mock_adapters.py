# ==============================================================================
# Unit tests — Mock Detection & Fusion Adapters
# Verifies Protocol compliance, all 8 deterministic scenarios, and audit hash-chain.
# ==============================================================================

from __future__ import annotations

import pytest

from app.core.exceptions import ModelTimeoutError, ModelUnavailableError
from app.detection.base import (
    LanguageRouter,
    ProsodyDetector,
    SpeakerVerifier,
    Tier0Detector,
    Tier1Detector,
    Tier2Detector,
)
from app.detection.language import INDIC_LANGUAGES, MockLanguageRouter
from app.detection.prosody import MockProsodyDetector
from app.detection.speaker import MockSpeakerVerifier
from app.detection.tier0 import MockTier0Detector
from app.detection.tier1 import MockTier1Detector
from app.detection.tier2 import MockTier2Detector
from app.domain.enums import (
    AuditBlockType,
    DetectionLabel,
    DetectionStatus,
    LanguageRoutingSource,
    MockScenario,
    RiskBand,
    RiskVerdict,
)
from app.fusion.base import ExplanationEngine, FusionEngine
from app.fusion.mock import MockFusionEngine
from app.fusion.shap import MockExplanationEngine
from app.integrations.audit.base import AuditLedger
from app.integrations.audit.mock import MockAuditLedger
from app.schemas.audio import AudioFeatures, AudioSegment
from app.schemas.context import CallContext
from app.schemas.detection import DetectionRequest, FusionInput


@pytest.fixture
def base_request() -> DetectionRequest:
    return DetectionRequest(
        segment=AudioSegment(call_id="call-test-01", segment_id="seg-001"),
        context=CallContext(transaction_type="kyc", transaction_value_inr=50000),
    )


class TestProtocolCompliance:
    """Verify mock adapters satisfy Python Protocol contracts via structural subtyping."""

    def test_tier0_protocol(self) -> None:
        assert isinstance(MockTier0Detector(), Tier0Detector)

    def test_tier1_protocol(self) -> None:
        assert isinstance(MockTier1Detector(), Tier1Detector)

    def test_tier2_protocol(self) -> None:
        assert isinstance(MockTier2Detector(), Tier2Detector)

    def test_prosody_protocol(self) -> None:
        assert isinstance(MockProsodyDetector(), ProsodyDetector)

    def test_speaker_protocol(self) -> None:
        assert isinstance(MockSpeakerVerifier(), SpeakerVerifier)

    def test_language_protocol(self) -> None:
        assert isinstance(MockLanguageRouter(), LanguageRouter)

    def test_fusion_protocol(self) -> None:
        assert isinstance(MockFusionEngine(), FusionEngine)

    def test_explanation_protocol(self) -> None:
        assert isinstance(MockExplanationEngine(), ExplanationEngine)

    def test_audit_protocol(self) -> None:
        assert isinstance(MockAuditLedger(), AuditLedger)


class TestDeterministicScenarios:
    """Verify all 8 deterministic mock scenarios."""

    @pytest.mark.asyncio
    async def test_low_risk_scenario(self, base_request: DetectionRequest) -> None:
        t0 = MockTier0Detector(default_scenario=MockScenario.LOW_RISK)
        t1 = MockTier1Detector(default_scenario=MockScenario.LOW_RISK)
        t2 = MockTier2Detector(default_scenario=MockScenario.LOW_RISK)

        r0 = await t0.predict(base_request)
        r1 = await t1.predict(base_request)
        r2 = await t2.predict(base_request)

        assert r0.score <= 0.20
        assert r0.label == DetectionLabel.AUTHENTIC
        assert r1.score <= 0.25
        assert r1.label == DetectionLabel.AUTHENTIC
        assert r2.score <= 0.20
        assert r2.label == DetectionLabel.AUTHENTIC

    @pytest.mark.asyncio
    async def test_critical_risk_scenario(self, base_request: DetectionRequest) -> None:
        t0 = MockTier0Detector(default_scenario=MockScenario.CRITICAL_RISK)
        t1 = MockTier1Detector(default_scenario=MockScenario.CRITICAL_RISK)
        t2 = MockTier2Detector(default_scenario=MockScenario.CRITICAL_RISK)

        r0 = await t0.predict(base_request)
        r1 = await t1.predict(base_request)
        r2 = await t2.predict(base_request)

        assert r0.score >= 0.80
        assert r0.label == DetectionLabel.LIKELY_CLONE
        assert r1.score >= 0.90
        assert r1.label == DetectionLabel.LIKELY_CLONE
        assert r2.score >= 0.90
        assert r2.label == DetectionLabel.LIKELY_CLONE

    @pytest.mark.asyncio
    async def test_tier_disagreement_scenario(self, base_request: DetectionRequest) -> None:
        t0 = MockTier0Detector(default_scenario=MockScenario.TIER_DISAGREEMENT)
        t1 = MockTier1Detector(default_scenario=MockScenario.TIER_DISAGREEMENT)
        t2 = MockTier2Detector(default_scenario=MockScenario.TIER_DISAGREEMENT)

        r0 = await t0.predict(base_request)
        r1 = await t1.predict(base_request)
        # Disagreement: Tier 0 says authentic, Tier 1 says clone!
        assert r0.score < 0.25
        assert r1.score > 0.80
        assert abs(r0.score - r1.score) > 0.50

        # Tier 2 resolves the disagreement
        r2 = await t2.predict(base_request, tier1_score=r1.score)
        assert r2.score > 0.80
        assert r2.label == DetectionLabel.LIKELY_CLONE

    @pytest.mark.asyncio
    async def test_model_timeout_scenario(self, base_request: DetectionRequest) -> None:
        t1 = MockTier1Detector(default_scenario=MockScenario.MODEL_TIMEOUT)
        r1 = await t1.predict(base_request)
        assert r1.status == DetectionStatus.TIMEOUT
        assert r1.confidence == 0.0
        assert r1.error is not None
        assert "timed out" in r1.error

        # Exception mode
        t1_raise = MockTier1Detector(
            default_scenario=MockScenario.MODEL_TIMEOUT, raise_exceptions=True
        )
        with pytest.raises(ModelTimeoutError):
            await t1_raise.predict(base_request)

    @pytest.mark.asyncio
    async def test_model_failure_scenario(self, base_request: DetectionRequest) -> None:
        t1 = MockTier1Detector(default_scenario=MockScenario.MODEL_FAILURE)
        r1 = await t1.predict(base_request)
        assert r1.status == DetectionStatus.ERROR
        assert r1.confidence == 0.0
        assert r1.error is not None

        # Exception mode
        t1_raise = MockTier1Detector(
            default_scenario=MockScenario.MODEL_FAILURE, raise_exceptions=True
        )
        with pytest.raises(ModelUnavailableError):
            await t1_raise.predict(base_request)

    @pytest.mark.asyncio
    async def test_speaker_mismatch_scenario(self, base_request: DetectionRequest) -> None:
        spk_verifier = MockSpeakerVerifier(default_scenario=MockScenario.SPEAKER_MISMATCH)
        res = await spk_verifier.verify(base_request)
        assert res.enrolled is True
        assert res.mismatch is True
        assert res.cosine_similarity == 0.28
        assert "MISMATCH" in res.note


class TestFeatureEvaluations:
    """Verify heuristic calculations when acoustic feature vectors are supplied."""

    @pytest.mark.asyncio
    async def test_tier0_authentic_features(self) -> None:
        feats = AudioFeatures(
            spectralFlatnessVoiced=0.25,
            jitter=0.012,
            shimmer=0.04,
            hfEnergyRatio=0.04,
            f0RangeHz=35.0,
            modulation4Hz=0.08,
        )
        req = DetectionRequest(
            segment=AudioSegment(call_id="call-1", segment_id="seg-1", features=feats)
        )
        t0 = MockTier0Detector()
        res = await t0.predict(req)
        assert res.score < 0.25
        assert res.label == DetectionLabel.AUTHENTIC

    @pytest.mark.asyncio
    async def test_tier0_synthetic_features(self) -> None:
        feats = AudioFeatures(
            spectralFlatnessVoiced=0.72,
            jitter=0.001,
            shimmer=0.005,
            hfEnergyRatio=0.002,
            f0RangeHz=3.0,
            modulation4Hz=0.01,
        )
        req = DetectionRequest(
            segment=AudioSegment(call_id="call-1", segment_id="seg-1", features=feats)
        )
        t0 = MockTier0Detector()
        res = await t0.predict(req)
        assert res.score > 0.70
        assert res.label == DetectionLabel.LIKELY_CLONE

    @pytest.mark.asyncio
    async def test_speaker_cosine_similarity(self) -> None:
        vec_a = [1.0, 0.5, 0.2, 0.1]
        vec_b = [0.95, 0.48, 0.21, 0.09]  # Very close
        vec_c = [-0.8, -0.4, 0.1, -0.2]  # Dissimilar

        req_match = DetectionRequest(
            segment=AudioSegment(call_id="c1", segment_id="s1", features=AudioFeatures(mfcc=vec_b)),
            enrolled_mfcc=vec_a,
            context=CallContext(claimed_speaker="Rahul Roy"),
        )
        spk = MockSpeakerVerifier()
        res_match = await spk.verify(req_match)
        assert res_match.enrolled is True
        assert res_match.mismatch is False
        assert res_match.cosine_similarity is not None and res_match.cosine_similarity > 0.90

        req_mismatch = DetectionRequest(
            segment=AudioSegment(call_id="c1", segment_id="s1", features=AudioFeatures(mfcc=vec_c)),
            enrolled_mfcc=vec_a,
            context=CallContext(claimed_speaker="Rahul Roy"),
        )
        res_mismatch = await spk.verify(req_mismatch)
        assert res_mismatch.enrolled is True
        assert res_mismatch.mismatch is True


class TestLanguageRouter:
    """Verify Indic language routing, code-switching, and operator selection."""

    @pytest.mark.asyncio
    async def test_operator_selected_language(self, base_request: DetectionRequest) -> None:
        router = MockLanguageRouter()
        base_request.language_override = "ta"  # Tamil
        res = await router.route(base_request)
        assert res.detected == "Tamil"
        assert res.code == "ta"
        assert res.adapter == "lora-ta-v2"
        assert res.source == LanguageRoutingSource.USER_SELECTED

    @pytest.mark.asyncio
    async def test_all_12_indic_languages(self, base_request: DetectionRequest) -> None:
        router = MockLanguageRouter()
        for item in INDIC_LANGUAGES:
            base_request.language_override = item["code"]
            res = await router.route(base_request)
            assert res.code == item["code"]
            assert res.adapter == item["adapter"]

    @pytest.mark.asyncio
    async def test_code_switching(self, base_request: DetectionRequest) -> None:
        router = MockLanguageRouter()
        base_request.context.code_switching = True
        res = await router.route(base_request)
        assert res.code_switching is True
        assert "lora-hi-v2 ⊕ lora-enIN-v2" in res.adapter

    @pytest.mark.asyncio
    async def test_undetermined_fallback(self, base_request: DetectionRequest) -> None:
        router = MockLanguageRouter()
        res = await router.route(base_request)
        assert res.source == LanguageRoutingSource.UNDETERMINED
        assert res.code == "und"


class TestFusionAndExplainability:
    """Verify multi-modal fusion scoring, thresholds, and SHAP output."""

    @pytest.mark.asyncio
    async def test_fusion_low_risk_flow(self) -> None:
        t0 = MockTier0Detector(default_scenario=MockScenario.LOW_RISK)
        t1 = MockTier1Detector(default_scenario=MockScenario.LOW_RISK)
        prosody = MockProsodyDetector(default_scenario=MockScenario.LOW_RISK)
        speaker = MockSpeakerVerifier(default_scenario=MockScenario.LOW_RISK)
        fusion = MockFusionEngine()

        req = DetectionRequest(
            segment=AudioSegment(call_id="call-low", segment_id="seg-001"),
            context=CallContext(ani_reputation=0.9, known_contact=True),
        )
        r0 = await t0.predict(req)
        r1 = await t1.predict(req)
        p_vote = await prosody.analyze(req)
        spk_res = await speaker.verify(req)

        f_input = FusionInput(
            tier0_result=r0,
            tier1_result=r1,
            prosody_vote=p_vote,
            speaker_check=spk_res,
            context=req.context,
        )
        out = await fusion.fuse(f_input)
        assert out.risk_score < 30
        assert out.band == RiskBand.LOW
        assert out.verdict == RiskVerdict.AUTHENTIC
        assert out.requires_out_of_band is False
        assert len(out.shap) == 5

    @pytest.mark.asyncio
    async def test_fusion_critical_risk_flow(self) -> None:
        t0 = MockTier0Detector(default_scenario=MockScenario.CRITICAL_RISK)
        t1 = MockTier1Detector(default_scenario=MockScenario.CRITICAL_RISK)
        t2 = MockTier2Detector(default_scenario=MockScenario.CRITICAL_RISK)
        prosody = MockProsodyDetector(default_scenario=MockScenario.CRITICAL_RISK)
        speaker = MockSpeakerVerifier(default_scenario=MockScenario.SPEAKER_MISMATCH)
        fusion = MockFusionEngine()

        req = DetectionRequest(
            segment=AudioSegment(call_id="call-crit", segment_id="seg-001"),
            context=CallContext(
                ani_reputation=0.1,
                known_contact=False,
                transaction_type="wire-transfer",
                transaction_value_inr=850000,
            ),
        )
        r0 = await t0.predict(req)
        r1 = await t1.predict(req)
        r2 = await t2.predict(req, tier1_score=r1.score)
        p_vote = await prosody.analyze(req)
        spk_res = await speaker.verify(req)

        f_input = FusionInput(
            tier0_result=r0,
            tier1_result=r1,
            tier2_result=r2,
            prosody_vote=p_vote,
            speaker_check=spk_res,
            context=req.context,
        )
        out = await fusion.fuse(f_input)
        assert out.risk_score >= 80
        assert out.band == RiskBand.CRITICAL
        assert out.verdict == RiskVerdict.LIKELY_CLONE
        assert out.requires_out_of_band is True


class TestAuditLedger:
    """Verify tamper-evident hash-chain appending, verification, and tamper detection."""

    @pytest.mark.asyncio
    async def test_genesis_block_created(self) -> None:
        ledger = MockAuditLedger()
        blocks = await ledger.get_blocks()
        assert len(blocks) == 1
        assert blocks[0].index == 0
        assert blocks[0].type == AuditBlockType.GENESIS
        assert blocks[0].prev_hash == "0" * 64

    @pytest.mark.asyncio
    async def test_append_and_verify_chain(self) -> None:
        ledger = MockAuditLedger(difficulty=1)
        b1 = await ledger.append_block(
            event_type=AuditBlockType.RISK_SCORE,
            payload_plaintext='{"call_id": "call-1", "risk": 85}',
            summary="Risk packet anchored · score 85/100",
            risk_score=85,
        )
        assert b1.index == 1
        assert b1.prev_hash == (await ledger.get_blocks())[0].hash

        b2 = await ledger.append_block(
            event_type=AuditBlockType.ESCALATION,
            payload_plaintext='{"call_id": "call-1", "action": "OOB_CHALLENGE"}',
            summary="OOB challenge triggered",
        )
        assert b2.index == 2
        assert b2.prev_hash == b1.hash

        is_valid, broken_idx, _ = await ledger.verify_chain()
        assert is_valid is True
        assert broken_idx is None

    @pytest.mark.asyncio
    async def test_tamper_detection(self) -> None:
        ledger = MockAuditLedger(difficulty=1)
        await ledger.append_block(
            event_type=AuditBlockType.RISK_SCORE,
            payload_plaintext='{"call_id": "call-tamper", "risk": 20}',
            summary="Risk packet anchored",
            risk_score=20,
        )
        await ledger.append_block(
            event_type=AuditBlockType.CONSENT,
            payload_plaintext='{"call_id": "call-tamper", "consent": true}',
            summary="Consent recorded",
        )

        # Chain valid initially
        is_valid_before, _, _ = await ledger.verify_chain()
        assert is_valid_before is True

        # Tamper block index 1
        ledger.tamper_block(1)

        is_valid_after, broken_idx, _ = await ledger.verify_chain()
        assert is_valid_after is False
        assert broken_idx == 1
