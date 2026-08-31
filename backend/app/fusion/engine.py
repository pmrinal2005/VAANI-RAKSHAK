# ==============================================================================
# VAANI-RAKSHAK — Multi-Modal Evidence Fusion Engine
# Fuses 3-tier acoustic detections, behavioural prosody, ECAPA-TDNN speaker
# verification, and contextual telephony risk into a unified calibrated risk score.
# ==============================================================================

from __future__ import annotations

import time

import structlog

from app.core.config import Settings, get_settings
from app.domain.enums import (
    DetectionStatus,
    RiskBand,
    RiskVerdict,
)
from app.fusion.base import ExplanationEngine
from app.fusion.policy import EnterprisePolicyEngine
from app.fusion.shap import MockExplanationEngine
from app.schemas.detection import (
    FusionInput,
    FusionOutput,
    SignalVote,
    TierResult,
)

logger = structlog.get_logger(__name__)


class MultiModalFusionEngine:
    """
    Combines multi-modal acoustic, biometric, and contextual signals into a
    unified risk assessment and enterprise policy decision.
    """

    def __init__(
        self,
        explanation_engine: ExplanationEngine | None = None,
        policy_engine: EnterprisePolicyEngine | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.explanation_engine = explanation_engine or MockExplanationEngine()
        self.policy_engine = policy_engine or EnterprisePolicyEngine()

    async def fuse(self, input_data: FusionInput) -> FusionOutput:
        start_time = time.perf_counter()
        call_id = input_data.segment.call_id if input_data.segment else "unknown"

        # ----------------------------------------------------------------------
        # 1. Acoustic Tier Evaluation
        # ----------------------------------------------------------------------
        t0_res = input_data.tier0_result
        t0 = t0_res.score if t0_res else 0.15
        t1_res = input_data.tier1_result
        t2_res = input_data.tier2_result

        t1_score = t1_res.score if t1_res and t1_res.status == DetectionStatus.SUCCESS else t0
        t2_score = (
            t2_res.score if t2_res and t2_res.status == DetectionStatus.SUCCESS else t1_score
        )

        # Primary neural countermeasure score
        if t2_res and t2_res.status == DetectionStatus.SUCCESS:
            cm_score = t2_score
        elif t1_res and t1_res.status == DetectionStatus.SUCCESS:
            cm_score = t1_score
        else:
            cm_score = t0

        acoustic_floor = max(t0, cm_score)

        # ----------------------------------------------------------------------
        # 2. Prosody & Biomarkers
        # ----------------------------------------------------------------------
        prosody_vote = input_data.prosody_vote
        prosody_score = prosody_vote.score if prosody_vote else 0.15

        # ----------------------------------------------------------------------
        # 3. Speaker Biometric Verification
        # ----------------------------------------------------------------------
        speaker_res = input_data.speaker_check
        speaker_risk = 0.0
        if speaker_res and speaker_res.mismatch:
            speaker_risk = 0.85
        elif speaker_res and speaker_res.cosine_similarity is not None:
            if speaker_res.cosine_similarity < 0.60:
                speaker_risk = 0.60
            elif speaker_res.cosine_similarity < 0.72:
                speaker_risk = 0.30

        # ----------------------------------------------------------------------
        # 4. Contextual Telephony / Transaction Risk
        # ----------------------------------------------------------------------
        ctx = input_data.context
        context_risk = 0.0
        if ctx.transaction_value_inr >= 200_000:
            context_risk += 0.35
        elif ctx.transaction_value_inr >= 50_000:
            context_risk += 0.15

        if ctx.ani_reputation < 0.40:
            context_risk += 0.30
        if not ctx.known_contact:
            context_risk += 0.15
        context_risk = min(1.0, context_risk)

        # ----------------------------------------------------------------------
        # 5. Multi-Modal Non-Linear Fusion
        # ----------------------------------------------------------------------
        # Weights: Acoustic (55%), Prosody (15%), Speaker (15%), Context (15%)
        raw_score = (
            (0.55 * acoustic_floor)
            + (0.15 * prosody_score)
            + (0.15 * speaker_risk)
            + (0.15 * context_risk)
        )

        # Non-linear boost if acoustic floor confirms deepfake
        if acoustic_floor >= 0.70:
            raw_score = max(raw_score, acoustic_floor * 0.95)

        risk_score = round(min(100.0, max(0.0, raw_score * 100)))

        # ----------------------------------------------------------------------
        # 6. Categorical Risk Band & Verdict
        # ----------------------------------------------------------------------
        if risk_score >= 85:
            band = RiskBand.CRITICAL
            verdict = RiskVerdict.LIKELY_CLONE
        elif risk_score >= 65:
            band = RiskBand.HIGH
            verdict = RiskVerdict.LIKELY_CLONE
        elif risk_score >= 40:
            band = RiskBand.ELEVATED
            verdict = RiskVerdict.SUSPICIOUS
        else:
            band = RiskBand.LOW
            verdict = RiskVerdict.AUTHENTIC

        # Flag inconclusive if any active tier timed out or errored
        has_error = (
            (
                t0_res is not None
                and t0_res.status in (DetectionStatus.TIMEOUT, DetectionStatus.ERROR)
            )
            or (t1_res and t1_res.status in (DetectionStatus.TIMEOUT, DetectionStatus.ERROR))
            or (t2_res and t2_res.status in (DetectionStatus.TIMEOUT, DetectionStatus.ERROR))
        )
        if has_error and risk_score < 85:
            verdict = RiskVerdict.INCONCLUSIVE

        # ----------------------------------------------------------------------
        # 7. Signal Breakdown Collection
        # ----------------------------------------------------------------------
        signals: dict[str, SignalVote] = {}
        t0_status_val = t0_res.status.value if t0_res else "UNKNOWN"
        t0_latency_val = t0_res.latency_ms if t0_res else 0.0
        signals["tier0"] = SignalVote(
            id="tier0",
            label="Micro-DSP Fast Pre-Filter",
            score=round(t0, 3),
            weight=0.20,
            detail=f"Status: {t0_status_val}",
        )
        if t1_res and t1_res.status != DetectionStatus.SKIPPED:
            signals["tier1"] = SignalVote(
                id="tier1",
                label="Compact Neural CM (AASIST-L)",
                score=round(t1_res.score, 3),
                weight=0.35,
                detail=f"Model: {t1_res.model_name}",
            )
        if t2_res and t2_res.status != DetectionStatus.SKIPPED:
            signals["tier2"] = SignalVote(
                id="tier2",
                label="Deep Multilingual SSL (IndicWav2Vec)",
                score=round(t2_res.score, 3),
                weight=0.45,
                detail=f"Model: {t2_res.model_name}",
            )
        if prosody_vote:
            signals["prosody"] = prosody_vote
        if speaker_res:
            signals["speaker"] = SignalVote(
                id="speaker",
                label="ECAPA-TDNN Speaker Verification",
                score=round(speaker_risk, 3),
                weight=0.15,
                detail=(
                    "Speaker mismatch detected"
                    if speaker_res.mismatch
                    else f"Cosine similarity: {speaker_res.cosine_similarity}"
                ),
            )
        signals["context"] = SignalVote(
            id="context",
            label="Call & Transaction Risk",
            score=round(context_risk, 3),
            weight=0.15,
            detail=f"ANI Rep: {ctx.ani_reputation}, Tx Value: INR {ctx.transaction_value_inr}",
        )

        # ----------------------------------------------------------------------
        # 8. SHAP Explainability Feature Attributions
        # ----------------------------------------------------------------------
        shap_contributions = await self.explanation_engine.explain(
            input_data, risk_score, list(signals.values())
        )
        top_feat = shap_contributions[0].feature if shap_contributions else "Acoustic analysis"
        if risk_score >= 85:
            smart_explanation = f"Critical risk voice clone flagged primarily by {top_feat}."
        elif risk_score >= 65:
            smart_explanation = f"High probability synthetic voice identified by {top_feat}."
        elif risk_score >= 40:
            smart_explanation = f"Elevated anomalies detected across {top_feat}."
        else:
            smart_explanation = f"Authentic voice confirmed across {top_feat}."

        # ----------------------------------------------------------------------
        # 9. Enterprise Policy Decision Evaluation
        # ----------------------------------------------------------------------
        t0_invoked = t0_res is not None and t0_res.status != DetectionStatus.SKIPPED
        t1_invoked = t1_res is not None and t1_res.status != DetectionStatus.SKIPPED
        t2_invoked = t2_res is not None and t2_res.status != DetectionStatus.SKIPPED

        temp_output = FusionOutput(
            fused_score=round(float(risk_score) / 100.0, 3),
            risk_score=risk_score,
            band=band,
            verdict=verdict,
            tiers=[
                TierResult(
                    tier=0,
                    name="Micro-DSP Pre-Filter",
                    invoked=t0_invoked,
                    score=round(t0, 3),
                    latency_ms=round(t0_latency_val, 2),
                    reason=f"Status: {t0_status_val}",
                ),
                TierResult(
                    tier=1,
                    name="Compact Neural Countermeasure",
                    invoked=t1_invoked,
                    score=round(t1_res.score, 3) if t1_res else 0.0,
                    latency_ms=round(t1_res.latency_ms, 2) if t1_res else 0.0,
                    reason=f"Status: {t1_res.status.value}" if t1_res else "Skipped",
                ),
                TierResult(
                    tier=2,
                    name="Deep Multilingual SSL Countermeasure",
                    invoked=t2_invoked,
                    score=round(t2_res.score, 3) if t2_res else 0.0,
                    latency_ms=round(t2_res.latency_ms, 2) if t2_res else 0.0,
                    reason=f"Status: {t2_res.status.value}" if t2_res else "Skipped",
                ),
            ],
            votes=list(signals.values()),
            shap=shap_contributions,
            requires_out_of_band=False,
            recommended_action="ALLOW",
            smart_explanation=smart_explanation,
            total_latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
            speaker_check=speaker_res,
            language_routing=input_data.language_routing,
        )

        policy_decision = self.policy_engine.evaluate(temp_output, ctx)

        temp_output.requires_out_of_band = policy_decision.requires_out_of_band
        temp_output.recommended_action = policy_decision.decision.value

        total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.debug(
            "fusion.completed",
            call_id=call_id,
            risk_score=risk_score,
            band=band.value,
            verdict=verdict.value,
            policy=policy_decision.decision.value,
            latency_ms=total_latency_ms,
        )

        return temp_output
