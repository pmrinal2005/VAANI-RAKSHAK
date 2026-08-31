from __future__ import annotations

from enum import StrEnum


class DetectionLabel(StrEnum):
    """Classification label produced by tier detectors."""

    AUTHENTIC = "authentic"
    SUSPICIOUS = "suspicious"
    LIKELY_CLONE = "likely_clone"
    INCONCLUSIVE = "inconclusive"


class DetectionStatus(StrEnum):
    """Operational status of a detection model invocation."""

    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"


class RiskBand(StrEnum):
    """
    Categorical risk level.
    Uses 'ELEVATED' to preserve 100% compatibility with the frontend contract.
    """

    LOW = "LOW"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskVerdict(StrEnum):
    """Actionable verdict matching frontend RiskAssessment contract."""

    AUTHENTIC = "AUTHENTIC"
    SUSPICIOUS = "SUSPICIOUS"
    LIKELY_CLONE = "LIKELY_CLONE"
    INCONCLUSIVE = "INCONCLUSIVE"


class Decision(StrEnum):
    """Workflow decision resulting from risk evaluation."""

    ALLOW = "ALLOW"
    HOLD = "HOLD"
    BLOCK = "BLOCK"
    CHALLENGE = "CHALLENGE"


class MockScenario(StrEnum):
    """
    Deterministic test scenarios supported by all mock adapters.
    Allows automated end-to-end pipeline verification without real ML models.
    """

    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL_RISK = "CRITICAL_RISK"
    TIER_DISAGREEMENT = "TIER_DISAGREEMENT"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_FAILURE = "MODEL_FAILURE"
    SPEAKER_MISMATCH = "SPEAKER_MISMATCH"


class LanguageRoutingSource(StrEnum):
    """Source that identified caller spoken language."""

    ONNX_LID = "onnx-lid"
    ACOUSTIC_HEURISTIC = "acoustic-heuristic"
    UNDETERMINED = "undetermined"
    USER_SELECTED = "user-selected"


class AudioQualityFlag(StrEnum):
    """Quality assessment of raw audio chunk."""

    OK = "ok"
    TOO_SHORT = "too_short"
    TOO_SILENT = "too_silent"
    LOW_SNR = "low_snr"


class AuditBlockType(StrEnum):
    """Types of blocks/events anchored in the audit ledger."""

    GENESIS = "GENESIS"
    CONSENT = "CONSENT"
    RISK_SCORE = "RISK_SCORE"
    ESCALATION = "ESCALATION"
    OOB_CHALLENGE = "OOB_CHALLENGE"
    OVERRIDE = "OVERRIDE"
