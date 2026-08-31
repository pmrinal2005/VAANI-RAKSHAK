# ==============================================================================
# VAANI-RAKSHAK — Tier 2 Mock Detector: Deep Multilingual SSL (IndicWav2Vec + AASIST3 Proxy)
# Simulates high-capacity multilingual SSL representations and LoRA adapter fusion.
# Clearly marked as MOCK implementation — not a production deep learning model.
# ==============================================================================

from __future__ import annotations

import time

from app.core.exceptions import ModelTimeoutError, ModelUnavailableError
from app.domain.enums import DetectionLabel, DetectionStatus, MockScenario
from app.schemas.audio import AudioFeatures
from app.schemas.detection import DetectionRequest, DetectionResult


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


class MockTier2Detector:
    """
    Mock implementation of Tier2Detector protocol.
    Simulates deep multilingual self-supervised learning (IndicWav2Vec + AASIST3 + LoRA adapters).
    """

    def __init__(
        self,
        default_scenario: MockScenario = MockScenario.LOW_RISK,
        raise_exceptions: bool = False,
    ) -> None:
        self.default_scenario = default_scenario
        self.raise_exceptions = raise_exceptions
        self.model_name = "mock-tier2-indic-wav2vec-aasist3"
        self.model_version = "dev-mock-1.0"

    async def predict(
        self, request: DetectionRequest, tier1_score: float | None = None
    ) -> DetectionResult:
        start_time = time.perf_counter()
        scenario = request.scenario_override or self.default_scenario

        if scenario == MockScenario.MODEL_TIMEOUT:
            if self.raise_exceptions:
                raise ModelTimeoutError("Deep SSL Tier-2 inference timed out after 1500ms")
            return DetectionResult(
                tier=2,
                score=0.5,
                confidence=0.0,
                label=DetectionLabel.INCONCLUSIVE,
                latency_ms=1500.0,
                model_name=self.model_name,
                model_version=self.model_version,
                signals={"mock_scenario": scenario.value},
                status=DetectionStatus.TIMEOUT,
                error="Deep SSL Tier-2 inference timed out after 1500ms",
            )

        if scenario == MockScenario.MODEL_FAILURE:
            if self.raise_exceptions:
                raise ModelUnavailableError(
                    "Deep SSL model checkpoint failed to load on GPU worker"
                )
            return DetectionResult(
                tier=2,
                score=0.5,
                confidence=0.0,
                label=DetectionLabel.INCONCLUSIVE,
                latency_ms=25.0,
                model_name=self.model_name,
                model_version=self.model_version,
                signals={"mock_scenario": scenario.value},
                status=DetectionStatus.ERROR,
                error="Deep SSL model worker unavailable",
            )

        base = tier1_score if tier1_score is not None else 0.5
        if request.segment.features is not None and request.scenario_override is None:
            score, label, reason = self._evaluate_features(
                request.segment.features, base, request.language_override
            )
        else:
            score, label, reason = self._evaluate_scenario(scenario)

        latency_ms = round((time.perf_counter() - start_time) * 1000 + 65.0, 2)

        return DetectionResult(
            tier=2,
            score=round(score, 3),
            confidence=0.95,
            label=label,
            latency_ms=latency_ms,
            model_name=self.model_name,
            model_version=self.model_version,
            signals={
                "ssl_layer_activations": [round(score * 0.8, 3), round(score * 0.95, 3)],
                "mock_scenario": scenario.value,
                "reason": reason,
            },
            status=DetectionStatus.SUCCESS,
            error=None,
        )

    def _evaluate_features(
        self, f: AudioFeatures, base: float, language_code: str | None
    ) -> tuple[float, DetectionLabel, str]:
        ssl = _clamp01(
            0.78 * base
            + 0.12 * _clamp01((0.008 - f.jitter) / 0.008)
            + 0.10 * _clamp01((12.0 - f.f0_range_hz) / 12.0)
        )
        adapter_boost = 0.04 if language_code else 0.0
        score = _clamp01(ssl + (adapter_boost if base > 0.5 else -adapter_boost))

        if score > 0.70:
            label = DetectionLabel.LIKELY_CLONE
            reason = (
                "Deep SSL countermeasure (IndicWav2Vec + AASIST3) confirms cross-lingual synthesis."
            )
        elif score < 0.35:
            label = DetectionLabel.AUTHENTIC
            reason = "Deep SSL features confirm authentic acoustic vocal tract dynamics."
        else:
            label = DetectionLabel.SUSPICIOUS
            reason = "Deep SSL countermeasure shows borderline synthetic likelihood."

        return score, label, reason

    def _evaluate_scenario(self, scenario: MockScenario) -> tuple[float, DetectionLabel, str]:
        if scenario == MockScenario.LOW_RISK:
            return 0.10, DetectionLabel.AUTHENTIC, "Deep SSL countermeasure confirms natural voice."
        if scenario == MockScenario.MEDIUM_RISK:
            return (
                0.55,
                DetectionLabel.SUSPICIOUS,
                "Deep SSL countermeasure indicates borderline synthesis.",
            )
        if scenario == MockScenario.HIGH_RISK:
            return (
                0.82,
                DetectionLabel.LIKELY_CLONE,
                "Deep SSL countermeasure confirms neural synthesis.",
            )
        if scenario == MockScenario.CRITICAL_RISK:
            return (
                0.96,
                DetectionLabel.LIKELY_CLONE,
                "Deep SSL countermeasure detects decisive synthetic voice clone.",
            )
        if scenario == MockScenario.TIER_DISAGREEMENT:
            return (
                0.89,
                DetectionLabel.LIKELY_CLONE,
                "Deep SSL decisively resolves tier disagreement: synthetic clone detected.",
            )
        if scenario == MockScenario.SPEAKER_MISMATCH:
            return 0.18, DetectionLabel.AUTHENTIC, "Deep SSL confirms natural vocal tract dynamics."
        return 0.15, DetectionLabel.AUTHENTIC, "Default baseline authentic voice."
