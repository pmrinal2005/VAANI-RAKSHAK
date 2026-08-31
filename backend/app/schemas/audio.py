# ==============================================================================
# VAANI-RAKSHAK — Audio Contracts & Schemas
# Standardised audio segment metadata and acoustic feature representations.
# RAW AUDIO IS NEVER STORED OR LOGGED DIRECTLY — only derived features & references.
# ==============================================================================

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AudioQualityFlag


class AudioReference(BaseModel):
    """Pointer to audio stored in ephemeral memory or external object store."""

    model_config = ConfigDict(extra="ignore")

    uri: str = Field(..., description="URI of the audio chunk, e.g. local://, s3://, memory://")
    storage_backend: str = Field(
        default="memory", description="Storage mechanism: memory | s3 | local"
    )
    sha256_hash: str | None = Field(
        default=None, description="SHA-256 digest of raw audio bytes (for integrity)"
    )
    size_bytes: int | None = Field(default=None, ge=0, description="Size in bytes")
    mime_type: str = Field(default="audio/wav", description="Audio MIME type")


class AudioFeatures(BaseModel):
    """
    Acoustic & behavioural features extracted from an audio segment.
    Maintains 100% field compatibility with frontend DSP feature extractors.
    Supports both camelCase and snake_case aliases.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    duration_sec: float = Field(default=2.0, alias="durationSec", ge=0.0)
    sample_rate: int = Field(default=16000, alias="sampleRate", ge=8000)
    rms_db: float = Field(default=-20.0, alias="rmsDb")
    silence_ratio: float = Field(default=0.1, alias="silenceRatio", ge=0.0, le=1.0)
    crest_factor: float = Field(default=3.5, alias="crestFactor")
    spectral_centroid_hz: float = Field(default=1800.0, alias="spectralCentroidHz", ge=0.0)
    spectral_spread_hz: float = Field(default=1200.0, alias="spectralSpreadHz", ge=0.0)
    spectral_flatness: float = Field(default=0.3, alias="spectralFlatness", ge=0.0, le=1.0)
    spectral_rolloff_hz: float = Field(default=3500.0, alias="spectralRolloffHz", ge=0.0)
    zero_crossing_rate: float = Field(default=0.08, alias="zeroCrossingRate", ge=0.0, le=1.0)
    phase_discontinuity: float = Field(default=0.02, alias="phaseDiscontinuity", ge=0.0)
    hf_energy_ratio: float = Field(default=0.03, alias="hfEnergyRatio", ge=0.0)
    cqcc_var: float = Field(default=0.15, alias="cqccVar", ge=0.0)
    lfcc_var: float = Field(default=0.18, alias="lfccVar", ge=0.0)
    f0_mean_hz: float = Field(default=140.0, alias="f0MeanHz", ge=0.0)
    f0_std: float = Field(default=15.0, alias="f0Std", ge=0.0)
    f0_range_hz: float = Field(default=25.0, alias="f0RangeHz", ge=0.0)
    jitter: float = Field(default=0.008, alias="jitter", ge=0.0)
    shimmer: float = Field(default=0.03, alias="shimmer", ge=0.0)
    speech_rate_var: float = Field(default=0.2, alias="speechRateVar", ge=0.0)
    mfcc: list[float] = Field(default_factory=lambda: [0.0] * 13, alias="mfcc")
    codec_cutoff_hz: float = Field(default=8000.0, alias="codecCutoffHz", ge=0.0)
    is_likely_codec: bool = Field(default=False, alias="isLikelyCodec")
    hnr_db: float = Field(default=18.0, alias="hnrDb")
    voiced_ratio: float = Field(default=0.75, alias="voicedRatio", ge=0.0, le=1.0)
    spectral_flatness_voiced: float = Field(
        default=0.35, alias="spectralFlatnessVoiced", ge=0.0, le=1.0
    )
    modulation_4hz: float = Field(default=0.04, alias="modulation4Hz", ge=0.0)
    f0_delta_var: float = Field(default=0.05, alias="f0DeltaVar", ge=0.0)
    quality_flag: AudioQualityFlag = Field(default=AudioQualityFlag.OK, alias="qualityFlag")


class AudioSegment(BaseModel):
    """Standardized representation of a single audio chunk in the streaming pipeline."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str = Field(..., alias="callId", description="Unique call session identifier")
    segment_id: str = Field(
        ..., alias="segmentId", description="Unique segment identifier within the call"
    )
    sequence_number: int = Field(
        default=0,
        ge=0,
        alias="sequenceNumber",
        description="Sequential sequence number (0-indexed)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when segment was captured",
    )
    sample_rate: int = Field(
        default=16000,
        ge=8000,
        le=48000,
        alias="sampleRate",
        description="Sample rate in Hz",
    )
    channels: int = Field(default=1, ge=1, le=2, description="Channel count (1=mono, 2=stereo)")
    duration_ms: float = Field(
        default=2000.0,
        ge=0.0,
        alias="durationMs",
        description="Duration of segment in milliseconds",
    )
    duration_sec: float | None = Field(default=None, alias="durationSec")
    codec: str = Field(default="pcm_s16le", description="Audio codec / format")
    audio_reference: AudioReference | str | None = Field(
        default=None, alias="audioReference", description="Reference pointer to raw audio bytes"
    )
    raw_pcm_b64: str | None = Field(
        default=None, alias="rawPcmB64", description="Base64-encoded audio chunk"
    )
    features: AudioFeatures | None = Field(
        default=None, description="Pre-extracted acoustic features, if available"
    )
