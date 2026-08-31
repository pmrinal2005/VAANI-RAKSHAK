# ==============================================================================
# VAANI-RAKSHAK — Tier 0 Mock Detector: Micro-DSP Pre-Filter
# Fast, lightweight acoustic heuristic pre-filtering simulation.
# Clearly marked as MOCK implementation — not a production DSP engine.
# ==============================================================================

from __future__ import annotations

import time

from app.domain.enums import DetectionLabel, DetectionStatus, MockScenario
from app.schemas.audio import AudioFeatures
from app.schemas.detection import DetectionRequest, DetectionResult


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


class MockTier0Detector:
    """
    Mock implementation of Tier0Detector protocol.
    Simulates near-zero compute DSP feature inspection and pre-filtering.
    """

    def __init__(self, default_scenario: MockScenario = MockScenario.LOW_RISK) -> None:
        self.default_scenario = default_scenario
        self.model_name = "mock-tier0-dsp"
        self.model_version = "dev-mock-1.0"

    async def predict(self, request: DetectionRequest) -> DetectionResult:
        start_time = time.perf_counter()
        scenario = request.scenario_override or self.default_scenario

        # If audio features are provided and scenario is not explicitly forcing a synthetic profile
        if request.segment.features is not None and request.scenario_override is None:
            score, label, reason = self._evaluate_features(request.segment.features)
        else:
            score, label, reason = self._evaluate_scenario(scenario)

        latency_ms = round((time.perf_counter() - start_time) * 1000 + 1.2, 2)

        return DetectionResult(
            tier=0,
            score=round(score, 3),
            confidence=0.92,
            label=label,
            latency_ms=latency_ms,
            model_name=self.model_name,
            model_version=self.model_version,
            signals={
                "dsp_method": "spectral_flatness_and_micro_tremor",
                "mock_scenario": scenario.value,
                "reason": reason,
            },
            status=DetectionStatus.SUCCESS,
            error=None,
        )

    def _evaluate_features(self, f: AudioFeatures) -> tuple[float, DetectionLabel, str]:
        flatness = _clamp01((f.spectral_flatness_voiced - 0.42) / 0.28)
        low_jitter = _clamp01((0.006 - f.jitter) / 0.006)
        low_shimmer = _clamp01((0.02 - f.shimmer) / 0.02)
        vocoder_hf = 0.0 if f.is_likely_codec else _clamp01((0.02 - f.hf_energy_ratio) / 0.02)
        flat_prosody = (
            _clamp01((10.0 - f.f0_range_hz) / 10.0) * 0.5
            + _clamp01((0.06 - f.modulation_4hz) / 0.06) * 0.5
        )

        score = _clamp01(
            0.34 * flatness
            + 0.18 * low_jitter
            + 0.14 * low_shimmer
            + 0.14 * vocoder_hf
            + 0.2 * flat_prosody
        )

        if score < 0.22:
            label = DetectionLabel.AUTHENTIC
            reason = (
                "Natural voiced spectral texture + organic micro-tremor — early exit candidate."
            )
        elif score > 0.70:
            label = DetectionLabel.LIKELY_CLONE
            reason = (
                "Strong DSP synthesis artefacts (whitened voiced spectrum + "
                "suppressed micro-tremor)."
            )
        else:
            label = DetectionLabel.SUSPICIOUS
            reason = "Ambiguous DSP signature — escalating to compact neural countermeasure."

        return score, label, reason

    def _evaluate_scenario(self, scenario: MockScenario) -> tuple[float, DetectionLabel, str]:
        if scenario == MockScenario.LOW_RISK:
            return (
                0.10,
                DetectionLabel.AUTHENTIC,
                "Natural voiced spectral texture + organic micro-tremor.",
            )
        if scenario == MockScenario.MEDIUM_RISK:
            return (
                0.45,
                DetectionLabel.SUSPICIOUS,
                "Ambiguous DSP signature — mildly elevated spectral flatness.",
            )
        if scenario == MockScenario.HIGH_RISK:
            return 0.72, DetectionLabel.LIKELY_CLONE, "Strong DSP synthesis artefacts detected."
        if scenario == MockScenario.CRITICAL_RISK:
            return (
                0.88,
                DetectionLabel.LIKELY_CLONE,
                "Severe high-frequency suppression and robotic micro-tremor.",
            )
        if scenario == MockScenario.TIER_DISAGREEMENT:
            return (
                0.12,
                DetectionLabel.AUTHENTIC,
                "Tier 0 found no obvious DSP artefacts (clean recording).",
            )
        if scenario in (
            MockScenario.MODEL_TIMEOUT,
            MockScenario.MODEL_FAILURE,
            MockScenario.SPEAKER_MISMATCH,
        ):
            return 0.15, DetectionLabel.AUTHENTIC, "Baseline DSP metrics normal."
        return 0.15, DetectionLabel.AUTHENTIC, "Default baseline authentic voice."
