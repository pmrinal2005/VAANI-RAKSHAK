# ==============================================================================
# Unit tests — Domain & Data Schemas
# Verifies Audio, CallContext, Detection, and Fusion Pydantic v2 contracts.
# ==============================================================================

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.enums import (
    AudioQualityFlag,
    AuditBlockType,
    DetectionLabel,
    DetectionStatus,
    LanguageRoutingSource,
    RiskBand,
    RiskVerdict,
)
from app.integrations.audit.base import AuditBlock
from app.schemas.audio import AudioFeatures, AudioReference, AudioSegment
from app.schemas.context import CallContext
from app.schemas.detection import (
    DetectionResult,
    FusionOutput,
    LanguageDistributionItem,
    LanguageRoutingResult,
    ShapContribution,
    SignalVote,
    SpeakerCheckResult,
    TierResult,
)


class TestAudioSchemas:
    """Test AudioSegment, AudioFeatures, and AudioReference schemas."""

    def test_audio_reference_defaults(self) -> None:
        ref = AudioReference(uri="local:///tmp/sample.wav")
        assert ref.uri == "local:///tmp/sample.wav"
        assert ref.storage_backend == "memory"
        assert ref.mime_type == "audio/wav"

    def test_audio_features_camel_case_parsing(self) -> None:
        """Verify frontend-style camelCase keys populate correctly."""
        raw_data = {
            "durationSec": 2.5,
            "sampleRate": 16000,
            "rmsDb": -18.2,
            "spectralFlatnessVoiced": 0.42,
            "f0RangeHz": 32.0,
            "qualityFlag": "ok",
            "mfcc": [0.1, 0.2, 0.3],
        }
        feats = AudioFeatures.model_validate(raw_data)
        assert feats.duration_sec == 2.5
        assert feats.sample_rate == 16000
        assert feats.spectral_flatness_voiced == 0.42
        assert feats.f0_range_hz == 32.0
        assert feats.quality_flag == AudioQualityFlag.OK
        assert len(feats.mfcc) == 3

    def test_audio_segment_defaults(self) -> None:
        seg = AudioSegment(call_id="call-001", segment_id="seg-001")
        assert seg.call_id == "call-001"
        assert seg.segment_id == "seg-001"
        assert seg.sample_rate == 16000
        assert seg.channels == 1
        assert seg.duration_ms == 2000.0
        assert seg.codec == "pcm_s16le"


class TestContextSchema:
    """Test CallContext validation and field aliases."""

    def test_call_context_defaults(self) -> None:
        ctx = CallContext()
        assert ctx.ani_reputation == 0.6
        assert ctx.known_contact is True
        assert ctx.transaction_type == "customer-service"
        assert ctx.transaction_value_inr == 0.0

    def test_call_context_camel_case_parsing(self) -> None:
        data = {
            "aniReputation": 0.15,
            "knownContact": False,
            "transactionType": "wire-transfer",
            "transactionValueInr": 850000,
            "claimedSpeaker": "Vikram Singh",
        }
        ctx = CallContext.model_validate(data)
        assert ctx.ani_reputation == 0.15
        assert ctx.known_contact is False
        assert ctx.transaction_type == "wire-transfer"
        assert ctx.transaction_value_inr == 850000.0
        assert ctx.claimed_speaker == "Vikram Singh"

    def test_ani_reputation_bounds(self) -> None:
        with pytest.raises(ValidationError):
            CallContext(ani_reputation=1.5)  # > 1.0

        with pytest.raises(ValidationError):
            CallContext(ani_reputation=-0.1)  # < 0.0


class TestDetectionSchemas:
    """Test DetectionResult, TierResult, SignalVote, and FusionOutput schemas."""

    def test_detection_result_validation(self) -> None:
        res = DetectionResult(
            tier=1,
            score=0.82,
            confidence=0.95,
            label=DetectionLabel.LIKELY_CLONE,
            latency_ms=15.4,
            model_name="mock-tier1",
            model_version="v1.0",
        )
        assert res.tier == 1
        assert res.score == 0.82
        assert res.label == DetectionLabel.LIKELY_CLONE
        assert res.status == DetectionStatus.SUCCESS
        assert res.error is None

    def test_tier_result_frontend_compat(self) -> None:
        tr = TierResult(
            tier=0,
            name="Micro-DSP Pre-Filter",
            invoked=True,
            score=0.12,
            latencyMs=1.8,
            reason="Voiced spectral check",
        )
        assert tr.tier == 0
        assert tr.latency_ms == 1.8
        data = tr.model_dump(by_alias=True)
        assert "latencyMs" in data

    def test_signal_vote_schema(self) -> None:
        vote = SignalVote(
            id="dsp",
            label="DSP Heuristics",
            score=0.72,
            weight=0.20,
            detail="High frequency spectral whitening",
        )
        assert vote.id == "dsp"
        assert vote.score == 0.72

    def test_speaker_check_result(self) -> None:
        spk = SpeakerCheckResult(
            enrolled=True,
            claimedSpeaker="Priya Sharma",
            cosineSimilarity=0.88,
            mismatch=False,
            note="Consistent",
        )
        assert spk.enrolled is True
        assert spk.claimed_speaker == "Priya Sharma"
        assert spk.cosine_similarity == 0.88
        assert spk.mismatch is False

    def test_language_routing_result(self) -> None:
        lang = LanguageRoutingResult(
            detected="Hindi",
            code="hi",
            confidence=0.98,
            distribution=[LanguageDistributionItem(language="Hindi", code="hi", prob=0.98)],
            adapter="lora-hi-v2",
            codeSwitching=False,
            source=LanguageRoutingSource.ONNX_LID,
        )
        assert lang.detected == "Hindi"
        assert lang.source == LanguageRoutingSource.ONNX_LID
        assert lang.code_switching is False

    def test_shap_contribution(self) -> None:
        shap = ShapContribution(
            feature="Voiced spectral texture",
            contribution=28.5,
            direction="increases",
            detail="Flatness 0.62",
        )
        assert shap.contribution == 28.5
        assert shap.direction == "increases"

    def test_fusion_output_validation(self) -> None:
        out = FusionOutput(
            fused_score=0.85,
            riskScore=85,
            band=RiskBand.CRITICAL,
            verdict=RiskVerdict.LIKELY_CLONE,
            requiresOutOfBand=True,
            smartExplanation="High risk clone detected.",
        )
        assert out.risk_score == 85
        assert out.band == RiskBand.CRITICAL
        assert out.verdict == RiskVerdict.LIKELY_CLONE
        assert out.requires_out_of_band is True


class TestAuditSchema:
    """Test AuditBlock serialization and validation."""

    def test_audit_block_creation(self) -> None:
        block = AuditBlock(
            index=0,
            timestamp=1725100000000,
            type=AuditBlockType.GENESIS,
            payloadHash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            summary="Genesis Block",
            actor="consortium",
            prevHash="0" * 64,
            hash="000123abc456",
            nonce=42,
        )
        assert block.index == 0
        assert block.type == AuditBlockType.GENESIS
        assert block.nonce == 42
        assert block.payload_hash.startswith("e3b0")
