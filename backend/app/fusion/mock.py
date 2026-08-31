# ==============================================================================
# VAANI-RAKSHAK — Multi-Modal Mock Fusion Engine
# Fuses acoustic tiers, behavioural biomarkers, speaker voiceprint, and context.
# Clearly marked as MOCK implementation — not a trained LightGBM model.
# ==============================================================================

from __future__ import annotations

import math
import re

from app.domain.enums import RiskBand, RiskVerdict
from app.fusion.shap import MockExplanationEngine
from app.schemas.context import CallContext
from app.schemas.detection import (
    DetectionResult,
    FusionInput,
    FusionOutput,
    SignalVote,
    SpeakerCheckResult,
    TierResult,
)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


class MockFusionEngine:
    """
    Mock implementation of FusionEngine protocol.
    Provides canonical weighted fusion replicating the calibrated multi-modal framework.
    """

    def __init__(self, explanation_engine: MockExplanationEngine | None = None) -> None:
        self.explainer = explanation_engine or MockExplanationEngine()

    async def fuse(self, fusion_input: FusionInput) -> FusionOutput:
        ctx = fusion_input.context
        t0 = fusion_input.tier0_result
        t1 = fusion_input.tier1_result
        t2 = fusion_input.tier2_result

        # Build list of TierResults
        tiers = self._build_tier_results(t0, t1, t2)

        # Build independent votes
        votes = self._build_votes(fusion_input)

        # Context risk
        ctx_risk = self._context_risk(ctx)

        # Acoustic fusion
        t0_score = t0.score if t0 else 0.15
        cm_score = (
            t2.score
            if t2 and t2.status.value == "success"
            else (t1.score if t1 and t1.status.value == "success" else t0_score)
        )
        primary = max(t0_score, cm_score)
        primary_floor = (0.55 * primary + 0.45 * primary * primary) if primary > 0.60 else 0.0

        total_weight = sum(v.weight for v in votes) or 1.0
        weighted_avg = sum(v.score * v.weight for v in votes) / total_weight
        acoustic_fused = _clamp01(max(weighted_avg, primary_floor))

        fused = _clamp01(0.82 * acoustic_fused + 0.18 * ctx_risk)
        risk_score = round(fused * 100)

        # Risk band & verdict
        if risk_score >= 85:
            band = RiskBand.CRITICAL
        elif risk_score >= 65:
            band = RiskBand.HIGH
        elif risk_score >= 40:
            band = RiskBand.ELEVATED
        else:
            band = RiskBand.LOW

        if risk_score >= 65:
            verdict = RiskVerdict.LIKELY_CLONE
        elif risk_score >= 40:
            verdict = RiskVerdict.SUSPICIOUS
        else:
            verdict = RiskVerdict.AUTHENTIC

        # Policy & OOB threshold
        high_stakes = (
            ctx.transaction_value_inr >= 200_000
            or bool(
                re.search(r"transfer|wire|recovery|approval|otp|kyc", ctx.transaction_type, re.I)
            )
            or not ctx.known_contact
        )
        strict_threshold = 55 if high_stakes else 70
        speaker_mismatch = (
            fusion_input.speaker_check.mismatch if fusion_input.speaker_check else False
        )
        requires_out_of_band = risk_score >= strict_threshold or speaker_mismatch

        # Feature contributions & smart explanation
        shap = await self.explainer.explain(fusion_input, risk_score, votes)
        explanation = self._build_smart_explanation(
            fusion_input, risk_score, band, verdict, high_stakes, speaker_mismatch
        )

        total_latency_ms = round(sum(t.latency_ms for t in tiers), 2)

        return FusionOutput(
            fused_score=round(fused, 4),
            risk_score=risk_score,
            band=band,
            verdict=verdict,
            tiers=tiers,
            votes=votes,
            shap=shap,
            requires_out_of_band=requires_out_of_band,
            smart_explanation=explanation,
            total_latency_ms=total_latency_ms,
        )

    def _context_risk(self, ctx: CallContext) -> float:
        ani_r = 1.0 - ctx.ani_reputation
        known_r = 0.0 if ctx.known_contact else 0.40
        value_r = _clamp01(math.log10(max(1.0, ctx.transaction_value_inr)) / 7.0)
        high_stake_txn = (
            0.25
            if re.search(r"transfer|wire|recovery|approval|otp|kyc", ctx.transaction_type, re.I)
            else 0.0
        )
        return _clamp01(
            0.35 * ani_r
            + 0.25 * known_r
            + 0.25 * value_r
            + 0.15 * ctx.time_of_day_risk
            + high_stake_txn
        )

    def _build_tier_results(
        self, t0: DetectionResult | None, t1: DetectionResult | None, t2: DetectionResult | None
    ) -> list[TierResult]:
        tiers: list[TierResult] = []
        if t0:
            tiers.append(
                TierResult(
                    tier=0,
                    name="Micro-DSP Pre-Filter",
                    invoked=True,
                    score=t0.score,
                    latency_ms=t0.latency_ms,
                    reason=t0.signals.get("reason", "DSP spectral texture inspection."),
                )
            )
        if t1:
            tiers.append(
                TierResult(
                    tier=1,
                    name="Compact Neural CM (AASIST-L)",
                    invoked=t1.status.value != "skipped",
                    score=t1.score,
                    latency_ms=t1.latency_ms,
                    reason=t1.signals.get(
                        "reason", "Graph attention spectro-temporal countermeasure."
                    ),
                    early_exit=t1.status.value == "skipped",
                )
            )
        else:
            tiers.append(
                TierResult(
                    tier=1,
                    name="Compact Neural CM (AASIST-L)",
                    invoked=False,
                    score=0.0,
                    latency_ms=0.0,
                    reason="Skipped — Tier 0 confident (early exit).",
                    early_exit=True,
                )
            )
        if t2:
            tiers.append(
                TierResult(
                    tier=2,
                    name="Deep Multilingual SSL (IndicWav2Vec+AASIST3)",
                    invoked=t2.status.value != "skipped",
                    score=t2.score,
                    latency_ms=t2.latency_ms,
                    reason=t2.signals.get("reason", "Deep SSL cross-lingual decision."),
                    early_exit=t2.status.value == "skipped",
                )
            )
        else:
            tiers.append(
                TierResult(
                    tier=2,
                    name="Deep Multilingual SSL (IndicWav2Vec+AASIST3)",
                    invoked=False,
                    score=0.0,
                    latency_ms=0.0,
                    reason="Skipped — no tier disagreement & low-stakes context.",
                    early_exit=True,
                )
            )
        return tiers

    def _build_votes(self, fusion_input: FusionInput) -> list[SignalVote]:
        votes: list[SignalVote] = []
        t0 = fusion_input.tier0_result
        if t0:
            votes.append(
                SignalVote(
                    id="dsp",
                    label="DSP artefact heuristics (Tier-0)",
                    score=t0.score,
                    weight=0.20,
                    detail=t0.signals.get("reason", "Voiced spectrum analysis."),
                )
            )

        t1 = fusion_input.tier1_result
        t2 = fusion_input.tier2_result
        cm_score = (
            t2.score
            if t2 and t2.status.value == "success"
            else (t1.score if t1 and t1.status.value == "success" else (t0.score if t0 else 0.15))
        )
        res = t2 or t1 or t0
        reason = str(res.signals.get("reason", "Neural countermeasure.")) if res else "Neural CM."
        votes.append(
            SignalVote(
                id="neural",
                label="Neural spectro-temporal CM",
                score=cm_score,
                weight=0.22,
                detail=reason,
            )
        )

        if fusion_input.prosody_vote:
            votes.append(fusion_input.prosody_vote)

        if fusion_input.speaker_check:
            spk = fusion_input.speaker_check
            score = (
                _clamp01((0.62 - spk.cosine_similarity) / 0.50)
                if spk.enrolled and spk.cosine_similarity is not None
                else 0.15
            )
            votes.append(
                SignalVote(
                    id="speaker",
                    label="Speaker cross-session consistency (ECAPA-TDNN)",
                    score=round(score, 3),
                    weight=0.18,
                    detail=spk.note,
                )
            )

        return votes

    def _build_smart_explanation(
        self,
        fusion_input: FusionInput,
        risk_score: int,
        band: RiskBand,
        verdict: RiskVerdict,
        high_stakes: bool,
        speaker_mismatch: bool,
    ) -> str:
        ctx = fusion_input.context
        spk = fusion_input.speaker_check or SpeakerCheckResult()
        lang = fusion_input.language_routing

        if verdict == RiskVerdict.AUTHENTIC:
            head = (
                f"The voice displays natural spectral texture and organic micro-variation "
                f"(risk {risk_score}/100, {band.value})."
            )
        elif verdict == RiskVerdict.SUSPICIOUS:
            head = (
                f"The voice carries mixed signals — mild synthetic traits push the risk "
                f"score to {risk_score}/100 ({band.value})."
            )
        else:
            head = (
                f"The voice exhibits strong synthesis fingerprints, giving a high impersonation "
                f"risk of {risk_score}/100 ({band.value})."
            )

        lang_note = f" Spoken language routed to {lang.adapter} ({lang.detected})." if lang else ""
        if speaker_mismatch:
            spk_note = (
                f" Live voiceprint does NOT match {spk.claimed_speaker}'s enrolled embedding!"
            )
        elif spk.enrolled:
            spk_note = f" Voiceprint is consistent with claimed speaker {spk.claimed_speaker}."
        else:
            spk_note = ""

        if high_stakes:
            ctx_note = (
                f" Because this is a high-stakes ({ctx.transaction_type}, INR "
                f"{ctx.transaction_value_inr:,.0f}) interaction, strict security thresholds apply."
            )
        else:
            ctx_note = ""

        return f"{head}{lang_note}{spk_note}{ctx_note}"
