# ==============================================================================
# VAANI-RAKSHAK — Dependency Injection Providers
# Central registry for all injectable services, detectors, and integrations.
# Adapters are swapped cleanly via configuration (DETECTION_MODE, AUDIT_MODE).
# ==============================================================================

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.cascade.orchestrator import CascadeOrchestrator
from app.core.config import Settings, get_settings
from app.detection.base import (
    LanguageRouter,
    ProsodyDetector,
    SpeakerVerifier,
    Tier0Detector,
    Tier1Detector,
    Tier2Detector,
)
from app.detection.language import MockLanguageRouter
from app.detection.prosody import MockProsodyDetector
from app.detection.speaker import MockSpeakerVerifier
from app.detection.tier0 import MockTier0Detector
from app.detection.tier1 import MockTier1Detector
from app.detection.tier2 import MockTier2Detector
from app.domain.enums import MockScenario
from app.fusion.base import ExplanationEngine, FusionEngine
from app.fusion.policy import EnterprisePolicyEngine
from app.fusion.shap import MockExplanationEngine
from app.integrations.audit.base import AuditLedger
from app.integrations.audit.ledger import CryptographicAuditLedger
from app.messaging.base import EventConsumer, EventProducer
from app.messaging.consumer import MockEventConsumer
from app.messaging.producer import MockEventProducer
from app.streaming.bridge import KafkaStreamingBridge
from app.streaming.manager import ConnectionManager
from app.telephony.session import CallSessionManager

# ------------------------------------------------------------------------------
# Settings dependency
# ------------------------------------------------------------------------------

SettingsDep = Annotated[Settings, Depends(get_settings)]


def _get_mock_scenario(settings: Settings) -> MockScenario:
    try:
        return MockScenario(settings.mock_scenario)
    except ValueError:
        return MockScenario.LOW_RISK


# ------------------------------------------------------------------------------
# Detector Providers
# ------------------------------------------------------------------------------


def get_tier0_detector(settings: SettingsDep) -> Tier0Detector:
    scenario = _get_mock_scenario(settings)
    if settings.detection_mode == "mock":
        return MockTier0Detector(default_scenario=scenario)
    # Future R1 ONNX / DSP detector:
    # return RealTier0Detector(model_path=settings.tier0_model_path)
    return MockTier0Detector(default_scenario=scenario)


def get_tier1_detector(settings: SettingsDep) -> Tier1Detector:
    scenario = _get_mock_scenario(settings)
    if settings.detection_mode == "mock":
        return MockTier1Detector(default_scenario=scenario)
    # Future R1 AASIST-L ONNX adapter:
    # return RealTier1AASISTLDetector(model_path=settings.tier1_model_path)
    return MockTier1Detector(default_scenario=scenario)


def get_tier2_detector(settings: SettingsDep) -> Tier2Detector:
    scenario = _get_mock_scenario(settings)
    if settings.detection_mode == "mock":
        return MockTier2Detector(default_scenario=scenario)
    # Future R1 IndicWav2Vec+AASIST3 adapter:
    # return RealTier2DeepSSLDetector(model_path=settings.tier2_model_path)
    return MockTier2Detector(default_scenario=scenario)


def get_prosody_detector(settings: SettingsDep) -> ProsodyDetector:
    scenario = _get_mock_scenario(settings)
    return MockProsodyDetector(default_scenario=scenario)


def get_speaker_verifier(settings: SettingsDep) -> SpeakerVerifier:
    scenario = _get_mock_scenario(settings)
    if settings.detection_mode == "mock":
        return MockSpeakerVerifier(default_scenario=scenario)
    # Future R1 ECAPA-TDNN ONNX adapter:
    # return RealECAPASpeakerVerifier(model_path=settings.speaker_model_path)
    return MockSpeakerVerifier(default_scenario=scenario)


def get_language_router(settings: SettingsDep) -> LanguageRouter:
    scenario = _get_mock_scenario(settings)
    if settings.detection_mode == "mock":
        return MockLanguageRouter(default_scenario=scenario)
    # Future R1 IndicLID ONNX adapter:
    # return RealIndicLIDRouter(model_path=settings.lid_model_path)
    return MockLanguageRouter(default_scenario=scenario)


# ------------------------------------------------------------------------------
# Fusion & Policy Providers
# ------------------------------------------------------------------------------


def get_policy_engine() -> EnterprisePolicyEngine:
    """Return enterprise banking policy and interceptor engine."""
    return EnterprisePolicyEngine()


def get_explanation_engine(settings: SettingsDep) -> ExplanationEngine:
    return MockExplanationEngine()


def get_fusion_engine(
    explanation_engine: ExplanationDep,
    policy_engine: Annotated[EnterprisePolicyEngine, Depends(get_policy_engine)],
    settings: SettingsDep,
) -> FusionEngine:
    """Return multi-modal evidence fusion engine."""
    from app.fusion.engine import MultiModalFusionEngine

    return MultiModalFusionEngine(
        explanation_engine=explanation_engine,
        policy_engine=policy_engine,
        settings=settings,
    )


# ------------------------------------------------------------------------------
# Audit Ledger Provider (R4 Boundary)
# ------------------------------------------------------------------------------

# Singleton in-memory ledger instance for the mock lifetime
_GLOBAL_AUDIT_LEDGER = CryptographicAuditLedger()


def get_audit_ledger(settings: SettingsDep) -> AuditLedger:
    """Return active cryptographic audit ledger conforming to AuditLedger protocol."""
    return _GLOBAL_AUDIT_LEDGER


# ------------------------------------------------------------------------------
# Kafka / Messaging Provider
# ------------------------------------------------------------------------------

_LOCAL_MOCK_PRODUCER: MockEventProducer | None = None


def get_event_producer(settings: SettingsDep) -> EventProducer:
    """Return active event producer (from lifecycle or lazy-instantiated mock)."""
    from app.core.lifecycle import get_global_producer

    global_prod = get_global_producer()
    if global_prod is not None and isinstance(global_prod, EventProducer):
        return global_prod

    # Fallback to local singleton mock producer
    global _LOCAL_MOCK_PRODUCER
    if _LOCAL_MOCK_PRODUCER is None:
        from app.domain.topics import TopicManager

        _LOCAL_MOCK_PRODUCER = MockEventProducer(
            topic_manager=TopicManager(prefix=settings.kafka_topic_prefix)
        )
    return _LOCAL_MOCK_PRODUCER


# ------------------------------------------------------------------------------
# Cascade Orchestrator Provider
# ------------------------------------------------------------------------------


def get_cascade_orchestrator(
    tier0: Tier0Dep,
    tier1: Tier1Dep,
    tier2: Tier2Dep,
    prosody: ProsodyDep,
    speaker: SpeakerDep,
    language: LanguageDep,
    settings: SettingsDep,
) -> CascadeOrchestrator:
    """Return configured 3-tier cascade orchestration engine."""
    from app.cascade.orchestrator import CascadeOrchestrator

    return CascadeOrchestrator(
        tier0_detector=tier0,
        tier1_detector=tier1,
        tier2_detector=tier2,
        prosody_detector=prosody,
        speaker_verifier=speaker,
        language_router=language,
        settings=settings,
    )


# ------------------------------------------------------------------------------
# Real-Time Streaming & Connection Manager Provider
# ------------------------------------------------------------------------------

_GLOBAL_CONNECTION_MANAGER = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Return singleton connection manager for WebSocket rooms and SSE subscribers."""
    return _GLOBAL_CONNECTION_MANAGER


def get_event_consumer(settings: SettingsDep) -> EventConsumer:
    """Return active event consumer (from lifecycle or mock)."""
    from app.core.lifecycle import get_global_consumer

    global_cons = get_global_consumer()
    if global_cons is not None and isinstance(global_cons, EventConsumer):
        return global_cons

    from app.domain.topics import TopicManager

    prod = get_event_producer(settings)
    if isinstance(prod, MockEventProducer):
        return MockEventConsumer(
            producer=prod,
            topic_manager=TopicManager(prefix=settings.kafka_topic_prefix),
        )

    return MockEventConsumer(
        producer=MockEventProducer(
            topic_manager=TopicManager(prefix=settings.kafka_topic_prefix)
        ),
        topic_manager=TopicManager(prefix=settings.kafka_topic_prefix),
    )


def get_streaming_bridge(
    consumer: Annotated[EventConsumer, Depends(get_event_consumer)],
    manager: Annotated[ConnectionManager, Depends(get_connection_manager)],
) -> KafkaStreamingBridge:
    """Return Kafka to WebSocket/SSE streaming bridge."""
    return KafkaStreamingBridge(
        consumer=consumer,
        connection_manager=manager,
    )


# ------------------------------------------------------------------------------
# Telephony Simulation Provider
# ------------------------------------------------------------------------------

_GLOBAL_CALL_SESSION_MANAGER = CallSessionManager()


def get_call_session_manager() -> CallSessionManager:
    """Return singleton call session manager for telephony simulations."""
    return _GLOBAL_CALL_SESSION_MANAGER


# ------------------------------------------------------------------------------
# Annotated Dependency Type Aliases
# ------------------------------------------------------------------------------

EventProducerDep = Annotated[EventProducer, Depends(get_event_producer)]
EventConsumerDep = Annotated[EventConsumer, Depends(get_event_consumer)]
Tier0Dep = Annotated[Tier0Detector, Depends(get_tier0_detector)]
Tier1Dep = Annotated[Tier1Detector, Depends(get_tier1_detector)]
Tier2Dep = Annotated[Tier2Detector, Depends(get_tier2_detector)]
ProsodyDep = Annotated[ProsodyDetector, Depends(get_prosody_detector)]
SpeakerDep = Annotated[SpeakerVerifier, Depends(get_speaker_verifier)]
LanguageDep = Annotated[LanguageRouter, Depends(get_language_router)]
CascadeOrchestratorDep = Annotated[CascadeOrchestrator, Depends(get_cascade_orchestrator)]
PolicyEngineDep = Annotated[EnterprisePolicyEngine, Depends(get_policy_engine)]
FusionDep = Annotated[FusionEngine, Depends(get_fusion_engine)]
ExplanationDep = Annotated[ExplanationEngine, Depends(get_explanation_engine)]
AuditDep = Annotated[AuditLedger, Depends(get_audit_ledger)]
ConnectionManagerDep = Annotated[ConnectionManager, Depends(get_connection_manager)]
StreamingBridgeDep = Annotated[KafkaStreamingBridge, Depends(get_streaming_bridge)]
CallSessionManagerDep = Annotated[CallSessionManager, Depends(get_call_session_manager)]
