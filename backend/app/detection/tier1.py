# ==============================================================================
# VAANI-RAKSHAK — Tier 1 Mock Detector: Compact Neural Countermeasure (AASIST-L Proxy)
# Simulates graph-attention spectro-temporal countermeasure inference.
# Clearly marked as MOCK implementation — not a production neural network.
# ==============================================================================

from __future__ import annotations

import math
import time

from app.core.exceptions import ModelTimeoutError, ModelUnavailableError
from app.domain.enums import DetectionLabel, DetectionStatus, MockScenario
from app.schemas.audio import AudioFeatures
from app.schemas.detection import DetectionRequest, DetectionResult


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class MockTier1Detector:
    """
    Mock implementation of Tier1Detector protocol.
    Simulates compact neural countermeasure inference (e.g. AASIST-L / RawNet3).
    """

    def __init__(
        self,
        default_scenario: MockScenario = MockScenario.LOW_RISK,
        raise_exceptions: bool = False,
    ) -> None:
        self.default_scenario = default_scenario
        self.raise_exceptions = raise_exceptions
        self.model_name = "mock-tier1-aasist-l"
        self.model_version = "dev-mock-1.0"

    async def predict(self, request: DetectionRequest) -> DetectionResult:
        start_time = time.perf_counter()
        scenario = request.scenario_override or self.default_scenario

        # Handle failure and timeout scenarios explicitly
        if scenario == MockScenario.MODEL_TIMEOUT:
            if self.raise_exceptions:
                raise ModelTimeoutError("AASIST-L mock inference timed out after 500ms")
            return DetectionResult(
                tier=1,
                score=0.5,
                confidence=0.0,
                label=DetectionLabel.INCONCLUSIVE,
                latency_ms=500.0,
                model_name=self.model_name,
                model_version=self.model_version,
                signals={"mock_scenario": scenario.value},
                status=DetectionStatus.TIMEOUT,
                error="AASIST-L mock inference timed out after 500ms",
            )

        if scenario == MockScenario.MODEL_FAILURE:
            if self.raise_exceptions:
                raise ModelUnavailableError("AASIST-L ONNX runtime session failed to initialize")
            return DetectionResult(
                tier=1,
                score=0.5,
                confidence=0.0,
                label=DetectionLabel.INCONCLUSIVE,
                latency_ms=10.0,
                model_name=self.model_name,
                model_version=self.model_version,
                signals={"mock_scenario": scenario.value},
                status=DetectionStatus.ERROR,
                error="AASIST-L ONNX runtime session execution error",
            )

        if request.segment.features is not None and request.scenario_override is None:
            score, label, reason = self._evaluate_features(request.segment.features)
        else:
            score, label, reason = self._evaluate_scenario(scenario)

        latency_ms = round((time.perf_counter() - start_time) * 1000 + 10.5, 2)

        return DetectionResult(
            tier=1,
            score=round(score, 3),
            confidence=0.88,
            label=label,
            latency_ms=latency_ms,
            model_name=self.model_name,
            model_version=self.model_version,
            signals={
                "graph_attention_activation": score * 0.9,
                "mock_scenario": scenario.value,
                "reason": reason,
            },
            status=DetectionStatus.SUCCESS,
            error=None,
        )

    def _evaluate_features(self, f: AudioFeatures) -> tuple[float, DetectionLabel, str]:
        vocoder_hf = 0.0 if f.is_likely_codec else _clamp01((0.02 - f.hf_energy_ratio) / 0.02)
        e_flat = _clamp01((f.spectral_flatness_voiced - 0.44) / 0.22)
        e_jit = _clamp01((0.006 - f.jitter) / 0.006)
        e_shim = _clamp01((0.02 - f.shimmer) / 0.02)
        e_range = _clamp01((8.0 - f.f0_range_hz) / 8.0)
        e_mod = _clamp01((0.05 - f.modulation_4hz) / 0.05)

        evidence = (
            0.28 * e_flat
            + 0.22 * e_jit
            + 0.16 * e_shim
            + 0.14 * vocoder_hf
            + 0.12 * e_range
            + 0.08 * e_mod
        )
        z = 5.8 * evidence - 1.7
        score = _clamp01(_sigmoid(z))

        if score > 0.70:
            label = DetectionLabel.LIKELY_CLONE
            reason = "Neural CM (AASIST-L) detects graph-attention spectro-temporal artefacts."
        elif score < 0.35:
            label = DetectionLabel.AUTHENTIC
            reason = "Neural CM consistent with bona-fide speech — no vocoder signature detected."
        else:
            label = DetectionLabel.SUSPICIOUS
            reason = "Neural CM mildly elevated — corroborating with deep multilingual SSL."

        return score, label, reason

    def _evaluate_scenario(self, scenario: MockScenario) -> tuple[float, DetectionLabel, str]:
        if scenario == MockScenario.LOW_RISK:
            return 0.15, DetectionLabel.AUTHENTIC, "Neural CM indicates authentic organic speech."
        if scenario == MockScenario.MEDIUM_RISK:
            return 0.52, DetectionLabel.SUSPICIOUS, "Mild spectro-temporal anomalies observed."
        if scenario == MockScenario.HIGH_RISK:
            return (
                0.78,
                DetectionLabel.LIKELY_CLONE,
                "AASIST-L detects clear neural vocoder fingerprints.",
            )
        if scenario == MockScenario.CRITICAL_RISK:
            return (
                0.94,
                DetectionLabel.LIKELY_CLONE,
                "Strong neural synthesis cues detected across multiple frequency bands.",
            )
        if scenario == MockScenario.TIER_DISAGREEMENT:
            return (
                0.86,
                DetectionLabel.LIKELY_CLONE,
                "Neural CM flags strong synthetic artefacts (disagrees with Tier 0).",
            )
        if scenario == MockScenario.SPEAKER_MISMATCH:
            return (
                0.20,
                DetectionLabel.AUTHENTIC,
                "Neural countermeasure finds no synthetic voice artefacts.",
            )
        return 0.20, DetectionLabel.AUTHENTIC, "Default baseline authentic voice."
