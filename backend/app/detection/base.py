# ==============================================================================
# VAANI-RAKSHAK — Detection Protocol Interfaces (R1 <-> R2 Boundary)
# Defines structural typing contracts using Python Protocols.
# Both Mock adapters and future real ONNX / PyTorch model wrappers implement these.
# ==============================================================================

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.detection import (
    DetectionRequest,
    DetectionResult,
    LanguageRoutingResult,
    SignalVote,
    SpeakerCheckResult,
)


@runtime_checkable
class Tier0Detector(Protocol):
    """
    Interface for Tier 0: Micro-DSP Pre-Filter / Spectral Anomaly Detector.
    Evaluates spectral flatness, micro-tremor, vocoder cutoffs, and voicing quality.
    """

    async def predict(self, request: DetectionRequest) -> DetectionResult:
        """Run fast acoustic/DSP pre-filtering and return tier 0 detection result."""
        ...


@runtime_checkable
class Tier1Detector(Protocol):
    """
    Interface for Tier 1: Compact Neural Countermeasure (e.g. AASIST-L / RawNet3).
    Evaluates spectro-temporal graph attention representations for synthesis artefacts.
    """

    async def predict(self, request: DetectionRequest) -> DetectionResult:
        """Run compact neural countermeasure inference and return tier 1 detection result."""
        ...


@runtime_checkable
class Tier2Detector(Protocol):
    """
    Interface for Tier 2: Deep Multilingual Self-Supervised Learning (e.g. IndicWav2Vec + AASIST3).
    Provides cross-lingual, high-capacity deep verification for escalated or high-stakes calls.
    """

    async def predict(
        self, request: DetectionRequest, tier1_score: float | None = None
    ) -> DetectionResult:
        """Run deep SSL countermeasure with LoRA adapters and return tier 2 result."""
        ...


@runtime_checkable
class ProsodyDetector(Protocol):
    """
    Interface for behavioural prosodic biomarker extraction.
    Examines unnatural pitch flatness, jitter suppression, and shimmer regularities.
    """

    async def analyze(self, request: DetectionRequest) -> SignalVote:
        """Evaluate prosody/behavioural biomarkers and return an independent signal vote."""
        ...


@runtime_checkable
class SpeakerVerifier(Protocol):
    """
    Interface for cross-session speaker verification (e.g. ECAPA-TDNN).
    Extracts speaker embeddings and performs cosine comparison against enrolled identity.
    """

    async def verify(self, request: DetectionRequest) -> SpeakerCheckResult:
        """Verify claimed speaker identity against enrolled voiceprint."""
        ...


@runtime_checkable
class LanguageRouter(Protocol):
    """
    Interface for Indic Spoken Language Identification (LID) & LoRA Routing.
    Routes audio chunks to language-specific adapters or manages code-switching soft ensembles.
    """

    async def route(self, request: DetectionRequest) -> LanguageRoutingResult:
        """Identify spoken language and select target LoRA adapter configuration."""
        ...
