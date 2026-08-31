# ==============================================================================
# VAANI-RAKSHAK — Telephony Simulation Execution Engine
# Generates realistic RTP/SIP audio chunks, simulates temporal risk transitions,
# and executes live detection with automatic zero-trust interceptor triggers.
# ==============================================================================

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog

from app.cascade.orchestrator import CascadeOrchestrator
from app.domain.enums import MockScenario
from app.fusion.base import FusionEngine
from app.integrations.audit.base import AuditLedger
from app.messaging.base import EventProducer
from app.schemas.audio import AudioFeatures, AudioSegment
from app.schemas.detection import DetectionRequest
from app.telephony.session import CallSimulationSession, CallStatus, SimulationPattern

logger = structlog.get_logger(__name__)

class TelephonySimulator:
    """
    Simulates inbound telephony streams with realistic RTP chunking,
    driving the cascade, fusion, Kafka, and WebSocket pipelines.
    """

    def __init__(
        self,
        orchestrator: CascadeOrchestrator,
        fusion_engine: FusionEngine,
        event_producer: EventProducer,
        audit_ledger: AuditLedger,
    ) -> None:
        self.orchestrator = orchestrator
        self.fusion_engine = fusion_engine
        self.event_producer = event_producer
        self.audit_ledger = audit_ledger

    async def run_call(self, session: CallSimulationSession) -> None:
        """
        Execute the continuous RTP chunking simulation loop for a call session.
        """
        from app.api.routes.score import score_audio_segment

        session.status = CallStatus.ACTIVE
        total_chunks = max(1, int(session.total_duration_sec / session.chunk_duration_sec))

        logger.info(
            "telephony_sim.call_started",
            call_id=session.call_id,
            pattern=session.pattern.value,
            total_duration=session.total_duration_sec,
            chunks=total_chunks,
        )

        try:
            for idx in range(total_chunks):
                # 1. Determine scenario for this chunk based on the temporal pattern
                chunk_scenario = self._resolve_chunk_scenario(
                    pattern=session.pattern,
                    base_scenario=session.request.scenario,
                    chunk_index=idx,
                    total_chunks=total_chunks,
                )

                # 2. Build synthetic audio features for the chunk
                segment_id = f"seg-{idx + 1:03d}"
                features = self._build_features_for_scenario(chunk_scenario)

                segment = AudioSegment(
                    call_id=session.call_id,
                    segment_id=segment_id,
                    sequence_number=idx,
                    duration_ms=session.chunk_duration_sec * 1000.0,
                    features=features,
                )

                detection_req = DetectionRequest(
                    segment=segment,
                    context=session.request.context,
                    scenario_override=chunk_scenario,
                )

                # 3. Execute unified scoring pipeline
                # (Executes Cascade -> Fusion -> Kafka -> WebSocket Bridge -> Audit Ledger)
                fusion_output = await score_audio_segment(
                    request=detection_req,
                    orchestrator=self.orchestrator,
                    fusion_engine=self.fusion_engine,
                    event_producer=self.event_producer,
                    audit_ledger=self.audit_ledger,
                )

                # 4. Update session trajectory and risk state
                session.current_segment_index = idx + 1
                session.processed_duration_sec = (idx + 1) * session.chunk_duration_sec
                session.current_risk_score = fusion_output.risk_score
                session.current_band = fusion_output.band
                session.current_verdict = fusion_output.verdict
                session.recommended_action = fusion_output.recommended_action
                session.requires_out_of_band = fusion_output.requires_out_of_band

                session.risk_history.append(fusion_output.risk_score)
                session.verdict_history.append(fusion_output.verdict.value)
                session.action_history.append(fusion_output.recommended_action)

                logger.debug(
                    "telephony_sim.chunk_processed",
                    call_id=session.call_id,
                    chunk=f"{idx + 1}/{total_chunks}",
                    risk_score=fusion_output.risk_score,
                    action=fusion_output.recommended_action,
                )

                # 5. Check for Banking Zero-Trust Interception (BLOCK)
                if fusion_output.recommended_action == "BLOCK":
                    session.status = CallStatus.INTERCEPTED
                    session.completed_at = datetime.now(UTC)
                    logger.warning(
                        "telephony_sim.call_intercepted_and_blocked",
                        call_id=session.call_id,
                        chunk=idx + 1,
                        risk_score=fusion_output.risk_score,
                        reason=fusion_output.smart_explanation,
                    )
                    return

                # 6. Sleep for real-time chunk interval (adjusted by playback_speed)
                delay = max(0.005, session.chunk_duration_sec / session.playback_speed)
                await asyncio.sleep(delay)

            # Call completed full duration without interception
            session.status = CallStatus.COMPLETED
            session.completed_at = datetime.now(UTC)
            logger.info("telephony_sim.call_completed", call_id=session.call_id)

        except asyncio.CancelledError:
            session.status = CallStatus.COMPLETED
            session.completed_at = datetime.now(UTC)
            logger.info("telephony_sim.call_cancelled", call_id=session.call_id)
        except Exception as exc:
            session.status = CallStatus.FAILED
            session.completed_at = datetime.now(UTC)
            logger.error("telephony_sim.call_failed", call_id=session.call_id, error=str(exc))

    def _resolve_chunk_scenario(
        self,
        pattern: SimulationPattern,
        base_scenario: MockScenario | None,
        chunk_index: int,
        total_chunks: int,
    ) -> MockScenario | None:
        """Evaluate temporal scenario transitions based on simulation pattern."""
        if pattern == SimulationPattern.STEADY:
            return base_scenario or MockScenario.LOW_RISK

        if pattern == SimulationPattern.AUTHENTIC_TO_CLONE:
            # Starts authentic, injects critical clone after 40% duration
            threshold = max(1, int(total_chunks * 0.4))
            return (
                MockScenario.CRITICAL_RISK
                if chunk_index >= threshold
                else MockScenario.LOW_RISK
            )

        if pattern == SimulationPattern.CLONE_BURST:
            # Authentic -> Brief high risk burst -> Authentic
            start_burst = max(1, int(total_chunks * 0.3))
            end_burst = max(start_burst + 1, int(total_chunks * 0.7))
            return (
                MockScenario.HIGH_RISK
                if start_burst <= chunk_index < end_burst
                else MockScenario.LOW_RISK
            )

        if pattern == SimulationPattern.SPEAKER_TAKEOVER:
            # First half authentic, second half triggers speaker verification mismatch
            midpoint = max(1, total_chunks // 2)
            return (
                MockScenario.SPEAKER_MISMATCH
                if chunk_index >= midpoint
                else MockScenario.LOW_RISK
            )

        return base_scenario

    def _build_features_for_scenario(
        self, scenario: MockScenario | None
    ) -> AudioFeatures:
        """Construct representative acoustic & biomarker features for scenario."""
        if scenario in (MockScenario.HIGH_RISK, MockScenario.CRITICAL_RISK):
            return AudioFeatures(
                spectral_flatness_voiced=0.38,
                hf_energy_ratio=0.16,
                jitter=0.0008,
                shimmer=0.005,
                f0_range_hz=12.0,
            )
        if scenario == MockScenario.SPEAKER_MISMATCH:
            return AudioFeatures(
                spectral_flatness_voiced=0.12,
                hf_energy_ratio=0.04,
                jitter=0.005,
                shimmer=0.02,
                f0_range_hz=45.0,
            )
        # Authentic default
        return AudioFeatures(
            spectral_flatness_voiced=0.06,
            hf_energy_ratio=0.02,
            jitter=0.004,
            shimmer=0.02,
            f0_range_hz=60.0,
        )
