# ==============================================================================
# VAANI-RAKSHAK — Kafka Topic Topology & Resolution
# Defines canonical pipeline topics, naming conventions, and environment prefixing.
# ==============================================================================

from __future__ import annotations

from enum import StrEnum


class KafkaTopic(StrEnum):
    """Canonical base topic identifiers across the streaming detection pipeline."""

    AUDIO_INGEST = "audio.ingest"
    AUDIO_SEGMENT = "audio.segment"
    DETECTION_TIER0 = "detection.tier0"
    DETECTION_TIER1 = "detection.tier1"
    DETECTION_TIER2 = "detection.tier2"
    DETECTION_PROSODY = "detection.prosody"
    DETECTION_SPEAKER = "detection.speaker"
    FUSION_RESULT = "fusion.result"
    RISK_EVENTS = "risk.events"
    WORKFLOW_EVENTS = "workflow.events"
    AUDIT_EVENTS = "audit.events"
    DEADLETTER = "deadletter"


class TopicManager:
    """
    Manages fully-qualified Kafka topic names with environment prefixing.
    Ensures isolation between development, staging, and production clusters.
    """

    def __init__(self, prefix: str = "vaani") -> None:
        self.prefix = prefix.strip().rstrip(".")

    def resolve(self, topic: KafkaTopic | str) -> str:
        """
        Return fully-qualified topic name with prefix applied.
        Example: KafkaTopic.AUDIO_INGEST -> 'vaani.audio.ingest'
        """
        base = topic.value if isinstance(topic, KafkaTopic) else str(topic)
        if base.startswith(f"{self.prefix}."):
            return base
        return f"{self.prefix}.{base}"

    def get_all_topics(self) -> list[str]:
        """Return list of all fully-qualified pipeline topic names."""
        return [self.resolve(t) for t in KafkaTopic]

    def is_valid_topic(self, topic_name: str) -> bool:
        """Check if a given topic name belongs to the defined topology."""
        valid_resolved = set(self.get_all_topics())
        valid_unprefixed = {t.value for t in KafkaTopic}
        return topic_name in valid_resolved or topic_name in valid_unprefixed
