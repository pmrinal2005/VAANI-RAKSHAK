# ==============================================================================
# Unit tests — Cascade Orchestration Engine
# Verifies 3-tier cascade progression, early-exit decisions, disagreement escalation,
# parallel sidecars, timeouts, and error resilience.
# ==============================================================================

from __future__ import annotations

import pytest

from app.api.dependencies import get_cascade_orchestrator
from app.cascade.orchestrator import CascadeOrchestrator
from app.core.config import Settings
from app.detection.language import MockLanguageRouter
from app.detection.prosody import MockProsodyDetector
from app.detection.speaker import MockSpeakerVerifier
from app.detection.tier0 import MockTier0Detector
from app.detection.tier1 import MockTier1Detector
from app.detection.tier2 import MockTier2Detector
from app.domain.enums import DetectionStatus, MockScenario
from app.schemas.audio import AudioFeatures, AudioSegment
from app.schemas.context import CallContext
from app.schemas.detection import DetectionRequest, DetectionResult


@pytest.fixture
def default_orchestrator() -> CascadeOrchestrator:
    settings = Settings()
    return CascadeOrchestrator(
        tier0_detector=MockTier0Detector(default_scenario=MockScenario.LOW_RISK),
        tier1_detector=MockTier1Detector(default_scenario=MockScenario.LOW_RISK),
        tier2_detector=MockTier2Detector(default_scenario=MockScenario.LOW_RISK),
        prosody_detector=MockProsodyDetector(default_scenario=MockScenario.LOW_RISK),
        speaker_verifier=MockSpeakerVerifier(default_scenario=MockScenario.LOW_RISK),
        language_router=MockLanguageRouter(default_scenario=MockScenario.LOW_RISK),
        settings=settings,
    )


class TestCascadeEarlyExits:
    """Verify early exit decision thresholds at Tier 0 and Tier 1."""

    @pytest.mark.asyncio
    async def test_tier0_early_exit(self, default_orchestrator: CascadeOrchestrator) -> None:
        """Low risk authentic audio triggers early exit at Tier 0 (< 3ms)."""
        req = DetectionRequest(
            segment=AudioSegment(call_id="call-ee0", segment_id="seg-001"),
            context=CallContext(transaction_type="inquiry", transaction_value_inr=0),
            scenario_override=MockScenario.LOW_RISK,
        )
        fusion_input, summary = await default_orchestrator.run_cascade(req)

        assert summary.tier0_early_exit is True
        assert summary.tier1_invoked is False
        assert summary.tier2_invoked is False
        assert fusion_input.tier0_result is not None
        assert fusion_input.tier0_result.status == DetectionStatus.SUCCESS
        assert fusion_input.tier1_result is not None
        assert fusion_input.tier1_result.status == DetectionStatus.SKIPPED
        assert fusion_input.tier2_result is not None
        assert fusion_input.tier2_result.status == DetectionStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_tier1_early_exit(self) -> None:
        """Ambiguous Tier 0 (0.30) -> Tier 1 evaluates (0.15) -> Early exit at Tier 1."""
        settings = Settings()

        class _CustomT0(MockTier0Detector):
            async def predict(self, request: DetectionRequest) -> DetectionResult:
                res = await super().predict(request)
                res.score = 0.30  # > 0.22 (no T0 exit)
                return res

        orch = CascadeOrchestrator(
            tier0_detector=_CustomT0(),
            tier1_detector=MockTier1Detector(default_scenario=MockScenario.LOW_RISK),  # score ~0.15
            tier2_detector=MockTier2Detector(default_scenario=MockScenario.LOW_RISK),
            prosody_detector=MockProsodyDetector(),
            speaker_verifier=MockSpeakerVerifier(),
            language_router=MockLanguageRouter(),
            settings=settings,
        )
        req = DetectionRequest(
            segment=AudioSegment(call_id="call-ee1", segment_id="seg-001"),
            context=CallContext(transaction_type="balance-check", transaction_value_inr=1000),
        )
        fusion_input, summary = await orch.run_cascade(req)

        assert summary.tier0_early_exit is False
        assert summary.tier1_invoked is True
        assert summary.tier1_early_exit is True
        assert summary.tier2_invoked is False
        assert fusion_input.tier2_result is not None
        assert fusion_input.tier2_result.status == DetectionStatus.SKIPPED


class TestCascadeEscalations:
    """Verify conditions that mandate progression to Deep Multilingual SSL Tier 2."""

    @pytest.mark.asyncio
    async def test_tier_disagreement_escalates(self) -> None:
        """Tier 0 authentic (0.12) vs Tier 1 clone (0.86) forces escalation to Tier 2."""
        settings = Settings()
        orch = CascadeOrchestrator(
            tier0_detector=MockTier0Detector(default_scenario=MockScenario.TIER_DISAGREEMENT),
            tier1_detector=MockTier1Detector(default_scenario=MockScenario.TIER_DISAGREEMENT),
            tier2_detector=MockTier2Detector(default_scenario=MockScenario.TIER_DISAGREEMENT),
            prosody_detector=MockProsodyDetector(),
            speaker_verifier=MockSpeakerVerifier(),
            language_router=MockLanguageRouter(),
            settings=settings,
        )
        req = DetectionRequest(
            segment=AudioSegment(call_id="call-disagree", segment_id="seg-001"),
            context=CallContext(transaction_type="login", transaction_value_inr=0),
        )
        fusion_input, summary = await orch.run_cascade(req)

        assert summary.tier_disagreement is True
        assert summary.disagreement_delta >= 0.30
        assert summary.tier2_invoked is True
        assert fusion_input.tier2_result is not None
        assert fusion_input.tier2_result.status == DetectionStatus.SUCCESS
        assert fusion_input.tier2_result.score > 0.80

    @pytest.mark.asyncio
    async def test_high_stakes_value_escalates(self) -> None:
        """High transaction value (>= INR 200,000) prevents early exit and executes Tier 2."""
        settings = Settings()
        orch = CascadeOrchestrator(
            tier0_detector=MockTier0Detector(default_scenario=MockScenario.LOW_RISK),
            tier1_detector=MockTier1Detector(default_scenario=MockScenario.LOW_RISK),
            tier2_detector=MockTier2Detector(default_scenario=MockScenario.LOW_RISK),
            prosody_detector=MockProsodyDetector(),
            speaker_verifier=MockSpeakerVerifier(),
            language_router=MockLanguageRouter(),
            settings=settings,
        )
        req = DetectionRequest(
            segment=AudioSegment(call_id="call-high-val", segment_id="seg-001"),
            context=CallContext(
                transaction_type="funds-transfer",
                transaction_value_inr=500_000,  # > 200,000 INR
            ),
        )
        _, summary = await orch.run_cascade(req)

        assert summary.tier0_early_exit is False
        assert summary.tier1_early_exit is False
        assert summary.tier2_invoked is True

    @pytest.mark.asyncio
    async def test_force_tier2_override(self) -> None:
        """force_tier2=True forces execution through all 3 tiers."""
        settings = Settings()
        orch = CascadeOrchestrator(
            tier0_detector=MockTier0Detector(default_scenario=MockScenario.LOW_RISK),
            tier1_detector=MockTier1Detector(default_scenario=MockScenario.LOW_RISK),
            tier2_detector=MockTier2Detector(default_scenario=MockScenario.LOW_RISK),
            prosody_detector=MockProsodyDetector(),
            speaker_verifier=MockSpeakerVerifier(),
            language_router=MockLanguageRouter(),
            settings=settings,
        )
        req = DetectionRequest(
            segment=AudioSegment(call_id="call-force", segment_id="seg-001"),
            force_tier2=True,
        )
        _, summary = await orch.run_cascade(req)

        assert summary.tier0_early_exit is False
        assert summary.tier2_invoked is True


class TestCascadeSidecarsAndResilience:
    """Verify parallel sidecars, timeout trapping, and error degradation."""

    @pytest.mark.asyncio
    async def test_sidecars_collected(self, default_orchestrator: CascadeOrchestrator) -> None:
        req = DetectionRequest(
            segment=AudioSegment(
                call_id="call-sidecars",
                segment_id="seg-001",
                features=AudioFeatures(f0RangeHz=22.0, jitter=0.009),
            ),
            context=CallContext(claimed_speaker="Rahul Roy", language="ta"),
            language_override="ta",
        )
        fusion_input, _ = await default_orchestrator.run_cascade(req)

        assert fusion_input.prosody_vote is not None
        assert fusion_input.prosody_vote.id == "prosody"
        assert fusion_input.speaker_check is not None
        assert fusion_input.speaker_check.claimed_speaker == "Rahul Roy"
        assert fusion_input.language_routing is not None
        assert fusion_input.language_routing.code == "ta"

    @pytest.mark.asyncio
    async def test_tier1_timeout_graceful_degradation(self) -> None:
        """Cascade does not crash when Tier 1 times out; marks degraded & status=TIMEOUT."""
        settings = Settings()
        orch = CascadeOrchestrator(
            tier0_detector=MockTier0Detector(default_scenario=MockScenario.HIGH_RISK),
            tier1_detector=MockTier1Detector(default_scenario=MockScenario.MODEL_TIMEOUT),
            tier2_detector=MockTier2Detector(default_scenario=MockScenario.HIGH_RISK),
            prosody_detector=MockProsodyDetector(),
            speaker_verifier=MockSpeakerVerifier(),
            language_router=MockLanguageRouter(),
            settings=settings,
        )
        req = DetectionRequest(
            segment=AudioSegment(call_id="call-to", segment_id="seg-001"),
            context=CallContext(transaction_value_inr=50000),
        )
        fusion_input, summary = await orch.run_cascade(req)

        assert fusion_input.tier1_result is not None
        assert fusion_input.tier1_result.status == DetectionStatus.TIMEOUT
        assert summary.tier2_invoked is True  # Continues to Tier 2 on Tier 1 timeout

    @pytest.mark.asyncio
    async def test_dependency_injection_provider(self) -> None:
        settings = Settings()
        t0 = MockTier0Detector()
        t1 = MockTier1Detector()
        t2 = MockTier2Detector()
        p = MockProsodyDetector()
        spk = MockSpeakerVerifier()
        lang = MockLanguageRouter()

        orch = get_cascade_orchestrator(
            tier0=t0,
            tier1=t1,
            tier2=t2,
            prosody=p,
            speaker=spk,
            language=lang,
            settings=settings,
        )
        assert isinstance(orch, CascadeOrchestrator)
