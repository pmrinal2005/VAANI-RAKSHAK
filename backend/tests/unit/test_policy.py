# ==============================================================================
# Unit tests — Enterprise Policy & Interceptor Engine
# Verifies zero-trust banking interceptor actions: ALLOW, CHALLENGE, HOLD, BLOCK.
# ==============================================================================

from __future__ import annotations

import pytest

from app.api.dependencies import get_policy_engine
from app.domain.enums import Decision, RiskBand, RiskVerdict
from app.fusion.policy import EnterprisePolicyEngine
from app.schemas.context import CallContext
from app.schemas.detection import FusionOutput, SpeakerCheckResult


@pytest.fixture
def policy_engine() -> EnterprisePolicyEngine:
    return EnterprisePolicyEngine()


def _make_fusion_output(
    risk_score: int,
    band: RiskBand,
    mismatch: bool = False,
) -> FusionOutput:
    return FusionOutput(
        fused_score=round(float(risk_score) / 100.0, 3),
        risk_score=risk_score,
        band=band,
        verdict=RiskVerdict.AUTHENTIC if risk_score < 40 else RiskVerdict.LIKELY_CLONE,
        confidence=0.90,
        acoustic_score=float(risk_score) / 100,
        context_score=0.10,
        signals={},
        tiers=[],
        shap_values={},
        top_contributors=[],
        explanation="Test explanation",
        requires_out_of_band=False,
        recommended_action="ALLOW",
        speaker_check=SpeakerCheckResult(
            enrolled=True,
            claimed_speaker="Rahul Roy",
            cosine_similarity=0.35 if mismatch else 0.88,
            mismatch=mismatch,
        ),
    )


class TestEnterprisePolicyRules:
    """Verify banking workflow decisions across risk tiers and transaction contexts."""

    def test_allow_low_risk(self, policy_engine: EnterprisePolicyEngine) -> None:
        fusion = _make_fusion_output(risk_score=15, band=RiskBand.LOW)
        ctx = CallContext(transaction_type="balance-inquiry", transaction_value_inr=0)
        decision = policy_engine.evaluate(fusion, ctx)

        assert decision.decision == Decision.ALLOW
        assert decision.requires_out_of_band is False
        assert "ALLOW" in decision.action_code

    def test_speaker_mismatch_forces_challenge_and_oob(
        self, policy_engine: EnterprisePolicyEngine
    ) -> None:
        """Speaker mismatch overrides low acoustic risk and demands OOB challenge."""
        fusion = _make_fusion_output(risk_score=20, band=RiskBand.LOW, mismatch=True)
        ctx = CallContext(transaction_type="balance-inquiry", transaction_value_inr=5000)
        decision = policy_engine.evaluate(fusion, ctx)

        assert decision.decision == Decision.CHALLENGE
        assert decision.requires_out_of_band is True
        assert "SPEAKER_MISMATCH" in decision.interceptor_rule

    def test_speaker_mismatch_critical_forces_block(
        self, policy_engine: EnterprisePolicyEngine
    ) -> None:
        fusion = _make_fusion_output(risk_score=92, band=RiskBand.CRITICAL, mismatch=True)
        ctx = CallContext(transaction_type="wire-transfer", transaction_value_inr=300_000)
        decision = policy_engine.evaluate(fusion, ctx)

        assert decision.decision == Decision.BLOCK
        assert decision.requires_out_of_band is True
        assert "SPEAKER_MISMATCH_CRITICAL" in decision.interceptor_rule

    def test_critical_risk_financial_forces_block(
        self, policy_engine: EnterprisePolicyEngine
    ) -> None:
        fusion = _make_fusion_output(risk_score=88, band=RiskBand.CRITICAL)
        ctx = CallContext(transaction_type="funds-transfer", transaction_value_inr=250_000)
        decision = policy_engine.evaluate(fusion, ctx)

        assert decision.decision == Decision.BLOCK
        assert decision.requires_out_of_band is True

    def test_critical_risk_inquiry_forces_hold(
        self, policy_engine: EnterprisePolicyEngine
    ) -> None:
        fusion = _make_fusion_output(risk_score=88, band=RiskBand.CRITICAL)
        ctx = CallContext(transaction_type="general-inquiry", transaction_value_inr=0)
        decision = policy_engine.evaluate(fusion, ctx)

        assert decision.decision == Decision.HOLD
        assert decision.requires_out_of_band is True

    def test_high_risk_forces_supervisor_hold(
        self, policy_engine: EnterprisePolicyEngine
    ) -> None:
        fusion = _make_fusion_output(risk_score=72, band=RiskBand.HIGH)
        ctx = CallContext(transaction_type="password-reset", transaction_value_inr=0)
        decision = policy_engine.evaluate(fusion, ctx)

        assert decision.decision == Decision.HOLD
        assert decision.requires_out_of_band is True

    def test_elevated_risk_high_stakes_forces_challenge(
        self, policy_engine: EnterprisePolicyEngine
    ) -> None:
        fusion = _make_fusion_output(risk_score=52, band=RiskBand.ELEVATED)
        ctx = CallContext(transaction_type="funds-transfer", transaction_value_inr=100_000)
        decision = policy_engine.evaluate(fusion, ctx)

        assert decision.decision == Decision.CHALLENGE
        assert decision.requires_out_of_band is True

    def test_elevated_risk_low_stakes_monitored_allow(
        self, policy_engine: EnterprisePolicyEngine
    ) -> None:
        fusion = _make_fusion_output(risk_score=48, band=RiskBand.ELEVATED)
        ctx = CallContext(transaction_type="general-inquiry", transaction_value_inr=0)
        decision = policy_engine.evaluate(fusion, ctx)

        assert decision.decision == Decision.ALLOW
        assert decision.requires_out_of_band is False
        assert "MONITORED" in decision.action_code

    def test_dependency_injection(self) -> None:
        engine = get_policy_engine()
        assert isinstance(engine, EnterprisePolicyEngine)
