# ==============================================================================
# Unit tests — Dependency Injection Providers
# Verifies dependency resolution and configuration-based provider switching.
# ==============================================================================

from __future__ import annotations

from app.api.dependencies import (
    get_audit_ledger,
    get_event_producer,
    get_fusion_engine,
    get_language_router,
    get_prosody_detector,
    get_speaker_verifier,
    get_tier0_detector,
    get_tier1_detector,
    get_tier2_detector,
)
from app.core.config import Settings
from app.detection.base import (
    LanguageRouter,
    ProsodyDetector,
    SpeakerVerifier,
    Tier0Detector,
    Tier1Detector,
    Tier2Detector,
)
from app.detection.tier0 import MockTier0Detector
from app.domain.enums import MockScenario
from app.fusion.base import FusionEngine
from app.integrations.audit.base import AuditLedger


class TestDependencyProviders:
    """Verify that all FastAPI dependency providers instantiate expected protocols."""

    def test_tier0_provider(self) -> None:
        settings = Settings(detection_mode="mock", mock_scenario="HIGH_RISK")
        detector = get_tier0_detector(settings)
        assert isinstance(detector, Tier0Detector)
        assert isinstance(detector, MockTier0Detector)
        assert detector.default_scenario == MockScenario.HIGH_RISK

    def test_tier1_provider(self) -> None:
        settings = Settings(detection_mode="mock", mock_scenario="CRITICAL_RISK")
        detector = get_tier1_detector(settings)
        assert isinstance(detector, Tier1Detector)

    def test_tier2_provider(self) -> None:
        settings = Settings(detection_mode="mock", mock_scenario="TIER_DISAGREEMENT")
        detector = get_tier2_detector(settings)
        assert isinstance(detector, Tier2Detector)

    def test_fusion_provider(self) -> None:
        from app.api.dependencies import get_policy_engine
        from app.fusion.shap import MockExplanationEngine

        settings = Settings()
        expl = MockExplanationEngine()
        policy = get_policy_engine()
        engine = get_fusion_engine(explanation_engine=expl, policy_engine=policy, settings=settings)
        assert isinstance(engine, FusionEngine)

    def test_policy_provider(self) -> None:
        from app.api.dependencies import get_policy_engine
        from app.fusion.policy import EnterprisePolicyEngine

        policy = get_policy_engine()
        assert isinstance(policy, EnterprisePolicyEngine)

    def test_prosody_provider(self) -> None:
        settings = Settings()
        prosody = get_prosody_detector(settings)
        assert isinstance(prosody, ProsodyDetector)

    def test_speaker_provider(self) -> None:
        settings = Settings(detection_mode="mock")
        speaker = get_speaker_verifier(settings)
        assert isinstance(speaker, SpeakerVerifier)

    def test_language_provider(self) -> None:
        settings = Settings(detection_mode="mock")
        router = get_language_router(settings)
        assert isinstance(router, LanguageRouter)

    def test_audit_ledger_provider(self) -> None:
        settings = Settings(audit_mode="mock")
        ledger = get_audit_ledger(settings)
        assert isinstance(ledger, AuditLedger)

    def test_event_producer_provider(self) -> None:
        from app.messaging.base import EventProducer

        settings = Settings()
        producer = get_event_producer(settings)
        assert isinstance(producer, EventProducer)
