# ==============================================================================
# VAANI-RAKSHAK — Prosody & Behavioural Biomarker Mock Detector
# Analyzes pitch drift, jitter/shimmer smoothness, and speech cadence.
# Clearly marked as MOCK implementation.
# ==============================================================================

from __future__ import annotations

from app.domain.enums import MockScenario
from app.schemas.audio import AudioFeatures
from app.schemas.detection import DetectionRequest, SignalVote


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


class MockProsodyDetector:
    """
    Mock implementation of ProsodyDetector protocol.
    Evaluates behavioural biomarkers and micro-tremor regularity.
    """

    def __init__(self, default_scenario: MockScenario = MockScenario.LOW_RISK) -> None:
        self.default_scenario = default_scenario

    async def analyze(self, request: DetectionRequest) -> SignalVote:
        scenario = request.scenario_override or self.default_scenario

        if request.segment.features is not None and request.scenario_override is None:
            score, detail = self._evaluate_features(request.segment.features)
        else:
            score, detail = self._evaluate_scenario(scenario)

        return SignalVote(
            id="prosody",
            label="Prosody / behavioural biomarkers",
            score=round(score, 3),
            weight=0.22,
            detail=detail,
        )

    def _evaluate_features(self, f: AudioFeatures) -> tuple[float, str]:
        over_smooth = (
            _clamp01((0.006 - f.jitter) / 0.006) * 0.32
            + _clamp01((0.02 - f.shimmer) / 0.02) * 0.24
            + _clamp01((8.0 - f.f0_range_hz) / 8.0) * 0.24
            + _clamp01((0.05 - f.modulation_4hz) / 0.05) * 0.20
        )
        is_synthetic = over_smooth > 0.5
        note = (
            "unnaturally smooth micro-tremor/prosody (TTS-like)"
            if is_synthetic
            else "natural micro-variation"
        )
        detail = (
            f"F0 range={f.f0_range_hz:.1f}Hz jitter={f.jitter:.4f} "
            f"shimmer={f.shimmer:.3f} mod4Hz={f.modulation_4hz:.3f} — {note}."
        )
        return over_smooth, detail

    def _evaluate_scenario(self, scenario: MockScenario) -> tuple[float, str]:
        if scenario == MockScenario.LOW_RISK:
            return (
                0.12,
                "Natural pitch drift (F0 range=28Hz) and physiological micro-tremor observed.",
            )
        if scenario == MockScenario.MEDIUM_RISK:
            return 0.48, "Slightly flattened F0 contour with reduced natural shimmer."
        if scenario == MockScenario.HIGH_RISK:
            return (
                0.75,
                "Unnaturally smoothed micro-tremor and flat prosodic dynamics (TTS signature).",
            )
        if scenario == MockScenario.CRITICAL_RISK:
            return (
                0.91,
                "Robotic monotone cadence with near-total suppression of vocal fold jitter.",
            )
        if scenario == MockScenario.TIER_DISAGREEMENT:
            return (
                0.30,
                "Prosodic indicators border between natural speech and synthetic smoothness.",
            )
        return 0.15, "Normal behavioural vocal biomarkers."
