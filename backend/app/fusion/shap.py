# ==============================================================================
# VAANI-RAKSHAK — SHAP Explainability Engine Mock Adapter
# Computes feature contribution breakdowns explaining the risk score.
# Clearly marked as MOCK/heuristic explainer — not a kernel SHAP on LightGBM.
# ==============================================================================

from __future__ import annotations

from typing import TypedDict

from app.schemas.detection import FusionInput, ShapContribution, SignalVote


class _ShapItem(TypedDict):
    feature: str
    raw: float
    detail: str


class MockExplanationEngine:
    """
    Mock implementation of ExplanationEngine protocol.
    Calculates normalized feature contribution breakdowns for XAI transparency.
    """

    async def explain(
        self,
        fusion_input: FusionInput,
        risk_score: int,
        votes: list[SignalVote],
    ) -> list[ShapContribution]:
        f = fusion_input.features or (
            fusion_input.segment.features if fusion_input.segment else None
        )
        ctx = fusion_input.context

        dsp_score = next((v.score for v in votes if v.id == "dsp"), 0.15)
        neural_score = next((v.score for v in votes if v.id == "neural"), 0.15)
        prosody_score = next((v.score for v in votes if v.id == "prosody"), 0.15)
        speaker_score = next((v.score for v in votes if v.id == "speaker"), 0.15)

        dsp_detail = (
            f"Voiced flatness {f.spectral_flatness_voiced:.2f} · HF ratio {f.hf_energy_ratio:.3f}"
            if f
            else "Spectral texture metrics"
        )
        prosody_detail = (
            f"jitter {f.jitter:.4f} · shimmer {f.shimmer:.3f} · F0 range {f.f0_range_hz:.1f}Hz"
            if f
            else "Micro-tremor and pitch metrics"
        )
        speaker_detail = next(
            (v.detail for v in votes if v.id == "speaker"), "Cross-session voiceprint comparison"
        )
        ctx_detail = (
            f"{ctx.transaction_type} · INR {ctx.transaction_value_inr:,.0f} · ANI "
            f"{ctx.ani_reputation:.2f}"
        )

        items: list[_ShapItem] = [
            {
                "feature": "Voiced spectral texture",
                "raw": dsp_score * 28.0 - 8.0,
                "detail": dsp_detail,
            },
            {
                "feature": "Neural countermeasure",
                "raw": neural_score * 32.0 - 7.0,
                "detail": next(
                    (v.detail for v in votes if v.id == "neural"),
                    "Deep neural graph representations",
                ),
            },
            {
                "feature": "Prosody / micro-tremor",
                "raw": prosody_score * 24.0 - 6.0,
                "detail": prosody_detail,
            },
            {
                "feature": "Speaker voiceprint",
                "raw": speaker_score * 18.0 - 5.0,
                "detail": speaker_detail,
            },
            {
                "feature": "Call context",
                "raw": (1.0 - ctx.ani_reputation) * 16.0 - 4.0,
                "detail": ctx_detail,
            },
        ]

        total = sum(abs(i["raw"]) for i in items) or 1.0
        contributions: list[ShapContribution] = []

        for item in items:
            contribution = round((item["raw"] / total) * risk_score, 1)
            contributions.append(
                ShapContribution(
                    feature=item["feature"],
                    contribution=contribution,
                    direction="increases" if contribution >= 0 else "decreases",
                    detail=item["detail"],
                )
            )

        contributions.sort(key=lambda x: abs(x.contribution), reverse=True)
        return contributions
