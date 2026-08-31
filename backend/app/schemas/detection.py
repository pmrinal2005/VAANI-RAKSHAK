# ==============================================================================
# VAANI-RAKSHAK — Detection & Scoring Contracts
# Standardised schemas for tier detection results, signal votes, and fusion outputs.
# ==============================================================================

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    DetectionLabel,
    DetectionStatus,
    LanguageRoutingSource,
    MockScenario,
    RiskBand,
    RiskVerdict,
)
from app.schemas.audio import AudioFeatures, AudioSegment
from app.schemas.context import CallContext


class DetectionRequest(BaseModel):
    """Payload passed to tier detectors and verifiers."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    segment: AudioSegment
    context: CallContext = Field(default_factory=CallContext)
    enrolled_mfcc: list[float] | None = Field(
        default=None, alias="enrolledMfcc", description="Enrolled speaker MFCC/embedding vector"
    )
    language_override: str | None = Field(
        default=None, alias="languageOverride", description="Optional manual language selection"
    )
    force_tier2: bool = Field(
        default=False,
        alias="forceTier2",
        description="Whether to bypass early exit and force deep SSL Tier-2",
    )
    scenario_override: MockScenario | None = Field(
        default=None, alias="scenarioOverride", description="Deterministic test scenario override"
    )


class DetectionResult(BaseModel):
    """Canonical result contract for all tier detectors."""

    model_config = ConfigDict(extra="ignore")

    tier: int = Field(..., ge=0, le=2, description="Detector tier level: 0, 1, or 2")
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Synthetic likelihood score (0.0=authentic, 1.0=clone)"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Model certainty in score")
    label: DetectionLabel = Field(default=DetectionLabel.AUTHENTIC, description="Categorical label")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Inference execution duration in ms")
    model_name: str = Field(..., description="Identifier of the executing model or mock adapter")
    model_version: str = Field(..., description="Semantic or development version of the model")
    signals: dict[str, Any] = Field(
        default_factory=dict, description="Extracted intermediate model activations/features"
    )
    status: DetectionStatus = Field(
        default=DetectionStatus.SUCCESS, description="Invocation operational status"
    )
    error: str | None = Field(default=None, description="Error message if status != success")


class TierResult(BaseModel):
    """Frontend-compatible tier result structure."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tier: int = Field(..., ge=0, le=2)
    name: str = Field(...)
    invoked: bool = Field(...)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_ms: float = Field(default=0.0, alias="latencyMs", ge=0.0)
    reason: str = Field(...)
    early_exit: bool | None = Field(default=None, alias="earlyExit")


class SignalVote(BaseModel):
    """Independent evidence vote contributing to multi-modal fusion."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Signal identifier (e.g. dsp, neural, prosody, speaker)")
    label: str = Field(..., description="Human-readable title of the signal")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized synthetic anomaly score")
    weight: float = Field(..., ge=0.0, le=1.0, description="Fusion weighting factor")
    detail: str = Field(..., description="Detailed diagnostic rationale")


class SpeakerCheckResult(BaseModel):
    """Verification result comparing current audio against enrolled voiceprint."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    enrolled: bool = Field(default=False)
    claimed_speaker: str | None = Field(default=None, alias="claimedSpeaker")
    cosine_similarity: float | None = Field(default=None, alias="cosineSimilarity")
    mismatch: bool = Field(default=False)
    note: str = Field(default="")


class LanguageDistributionItem(BaseModel):
    """Language probability prediction for multilingual routing."""

    model_config = ConfigDict(extra="ignore")

    language: str
    code: str
    prob: float = Field(ge=0.0, le=1.0)


class LanguageRoutingResult(BaseModel):
    """Indic spoken language routing decision and active LoRA adapter."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    detected: str = Field(default="Undetermined")
    code: str = Field(default="und")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    distribution: list[LanguageDistributionItem] = Field(default_factory=list)
    adapter: str = Field(default="language-agnostic")
    code_switching: bool = Field(default=False, alias="codeSwitching")
    source: LanguageRoutingSource = Field(default=LanguageRoutingSource.UNDETERMINED)
    note: str = Field(default="")


class ShapContribution(BaseModel):
    """Feature attribution element explaining why the risk score was reached."""

    model_config = ConfigDict(extra="ignore")

    feature: str = Field(...)
    contribution: float = Field(...)
    direction: str = Field(..., description="'increases' | 'decreases'")
    detail: str = Field(...)


class FusionInput(BaseModel):
    """Canonical feature & signal vector passed into the fusion engine."""

    model_config = ConfigDict(extra="ignore")

    segment: AudioSegment | None = None
    features: AudioFeatures | None = None
    tier0_result: DetectionResult | None = None
    tier1_result: DetectionResult | None = None
    tier2_result: DetectionResult | None = None
    prosody_vote: SignalVote | None = None
    speaker_check: SpeakerCheckResult | None = None
    language_routing: LanguageRoutingResult | None = None
    context: CallContext = Field(default_factory=CallContext)


class FusionOutput(BaseModel):
    """Output produced by the fusion and risk scoring engines."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    fused_score: float = Field(ge=0.0, le=1.0, description="Acoustic fused probability")
    risk_score: int = Field(
        ge=0, le=100, alias="riskScore", description="Final integer risk score (0-100)"
    )
    band: RiskBand = Field(
        ..., description="Categorical risk tier: LOW | ELEVATED | HIGH | CRITICAL"
    )
    verdict: RiskVerdict = Field(
        ..., description="Actionable verdict: AUTHENTIC | SUSPICIOUS | LIKELY_CLONE | INCONCLUSIVE"
    )
    tiers: list[TierResult] = Field(default_factory=list)
    votes: list[SignalVote] = Field(default_factory=list)
    shap: list[ShapContribution] = Field(default_factory=list)
    requires_out_of_band: bool = Field(default=False, alias="requiresOutOfBand")
    recommended_action: str = Field(default="ALLOW", alias="recommendedAction")
    smart_explanation: str = Field(default="", alias="smartExplanation")
    total_latency_ms: float = Field(default=0.0, alias="totalLatencyMs")
    speaker_check: SpeakerCheckResult | None = Field(default=None, alias="speakerCheck")
    language_routing: LanguageRoutingResult | None = Field(default=None, alias="languageRouting")


FusionInput.model_rebuild()
FusionOutput.model_rebuild()
