# ==============================================================================
# VAANI-RAKSHAK — Speaker Verification Mock Adapter (ECAPA-TDNN Proxy)
# Compares live voice embeddings against enrolled voiceprints.
# Clearly marked as MOCK implementation.
# ==============================================================================

from __future__ import annotations

import math

from app.domain.enums import MockScenario
from app.schemas.detection import DetectionRequest, SpeakerCheckResult


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class MockSpeakerVerifier:
    """
    Mock implementation of SpeakerVerifier protocol.
    Simulates cross-session speaker verification using embedding cosine similarity.
    """

    def __init__(self, default_scenario: MockScenario = MockScenario.LOW_RISK) -> None:
        self.default_scenario = default_scenario

    async def verify(self, request: DetectionRequest) -> SpeakerCheckResult:
        scenario = request.scenario_override or self.default_scenario

        # Handle explicit mismatch scenario
        if scenario == MockScenario.SPEAKER_MISMATCH:
            return SpeakerCheckResult(
                enrolled=True,
                claimed_speaker=request.context.claimed_speaker or "Enrolled Account Holder",
                cosine_similarity=0.28,
                mismatch=True,
                note=(
                    "Voiceprint MISMATCH (cosine=0.28 vs enrolled embedding — "
                    "possible impersonator)."
                ),
            )

        # Real vector cosine comparison if both vectors are available
        if (
            request.enrolled_mfcc is not None
            and request.segment.features is not None
            and request.segment.features.mfcc
        ):
            sim = _cosine(request.enrolled_mfcc, request.segment.features.mfcc)
            mismatch = sim < 0.55
            note = (
                f"Voiceprint MISMATCH (cosine={sim:.3f})"
                if mismatch
                else f"Voiceprint consistent with claimed identity (cosine={sim:.3f})"
            )
            return SpeakerCheckResult(
                enrolled=True,
                claimed_speaker=request.context.claimed_speaker or "Enrolled Speaker",
                cosine_similarity=round(sim, 3),
                mismatch=mismatch,
                note=note,
            )

        # Default fallback when no enrolled voiceprint exists
        if request.context.claimed_speaker:
            return SpeakerCheckResult(
                enrolled=False,
                claimed_speaker=request.context.claimed_speaker,
                cosine_similarity=None,
                mismatch=False,
                note=(
                    "No enrolled voiceprint for claimed speaker — "
                    "cross-session check unavailable."
                ),
            )

        return SpeakerCheckResult(
            enrolled=False,
            claimed_speaker=None,
            cosine_similarity=None,
            mismatch=False,
            note="No claimed identity specified.",
        )
