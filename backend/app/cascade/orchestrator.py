# ==============================================================================
# VAANI-RAKSHAK — 3-Tier Cascade Orchestration Engine
# Orchestrates Tier 0 (Micro-DSP), Tier 1 (Compact Neural), and Tier 2 (Deep SSL)
# with early-exit logic, high-stakes escalation, and concurrent sidecar analytics.
# ==============================================================================

from __future__ import annotations

import asyncio
import re
import time

import structlog

from app.cascade.state import CascadeExecutionSummary
from app.core.config import Settings
from app.detection.base import (
    LanguageRouter,
    ProsodyDetector,
    SpeakerVerifier,
    Tier0Detector,
    Tier1Detector,
    Tier2Detector,
)
from app.domain.enums import (
    DetectionLabel,
    DetectionStatus,
    LanguageRoutingSource,
    MockScenario,
)
from app.schemas.detection import (
    DetectionRequest,
    DetectionResult,
    FusionInput,
    LanguageRoutingResult,
    SignalVote,
    SpeakerCheckResult,
)

logger = structlog.get_logger(__name__)


class CascadeOrchestrator:
    """
    Executes the multi-tiered detection cascade and manages early exit transitions.
    """

    def __init__(
        self,
        tier0_detector: Tier0Detector,
        tier1_detector: Tier1Detector,
        tier2_detector: Tier2Detector,
        prosody_detector: ProsodyDetector,
        speaker_verifier: SpeakerVerifier,
        language_router: LanguageRouter,
        settings: Settings,
    ) -> None:
        self.t0 = tier0_detector
        self.t1 = tier1_detector
        self.t2 = tier2_detector
        self.prosody = prosody_detector
        self.speaker = speaker_verifier
        self.language = language_router
        self.settings = settings

    async def run_cascade(
        self, request: DetectionRequest
    ) -> tuple[FusionInput, CascadeExecutionSummary]:
        start_time = time.perf_counter()
        call_id = request.segment.call_id
        segment_id = request.segment.segment_id

        summary = CascadeExecutionSummary(call_id=call_id, segment_id=segment_id)

        # 1. Launch sidecar tasks concurrently in background
        prosody_task = asyncio.create_task(self._safe_prosody(request, summary))
        speaker_task = asyncio.create_task(self._safe_speaker(request, summary))
        language_task = asyncio.create_task(self._safe_language(request, summary))

        # Check high-stakes context criteria
        ctx = request.context
        high_stakes = (
            ctx.transaction_value_inr >= 200_000
            or bool(
                re.search(r"transfer|wire|recovery|approval|otp|kyc", ctx.transaction_type, re.I)
            )
            or not ctx.known_contact
        )
        force_tier2 = request.force_tier2

        # 2. Execute Tier 0: Micro-DSP Pre-Filter (< 3ms)
        t0_result = await self._run_tier0(request, summary)

        t1_result: DetectionResult | None = None
        t2_result: DetectionResult | None = None

        # Check Tier 0 Early Exit
        is_disagreement_test = (
            request.scenario_override == MockScenario.TIER_DISAGREEMENT
            or t0_result.signals.get("mock_scenario") == MockScenario.TIER_DISAGREEMENT.value
        )
        can_early_exit_t0 = (
            t0_result.status == DetectionStatus.SUCCESS
            and t0_result.score < self.settings.tier0_early_exit_low
            and t0_result.confidence >= 0.85
            and not high_stakes
            and not force_tier2
            and not is_disagreement_test
        )

        if can_early_exit_t0:
            summary.tier0_early_exit = True
            logger.debug("cascade.tier0_early_exit", call_id=call_id, score=t0_result.score)
            t1_result = self._make_skipped_result(
                1, "Skipped — Tier 0 confident authentic (early exit)"
            )
            t2_result = self._make_skipped_result(2, "Skipped — Tier 0 early exit")
        else:
            # 3. Execute Tier 1: Compact Neural CM (AASIST-L, < 20ms)
            summary.tier1_invoked = True
            t1_result = await self._run_tier1(request, summary)

            # Check for Tier Disagreement
            delta = abs(t1_result.score - t0_result.score)
            summary.disagreement_delta = round(delta, 3)
            if summary.disagreement_delta > self.settings.tier_disagreement_delta:
                summary.tier_disagreement = True
                logger.info(
                    "cascade.tier_disagreement_detected",
                    call_id=call_id,
                    t0_score=t0_result.score,
                    t1_score=t1_result.score,
                    delta=delta,
                )

            # Check Tier 1 Early Exit
            can_early_exit_t1 = (
                t1_result.status == DetectionStatus.SUCCESS
                and t1_result.score < self.settings.tier1_early_exit_low
                and not summary.tier_disagreement
                and not high_stakes
                and not force_tier2
            )

            if can_early_exit_t1:
                summary.tier1_early_exit = True
                logger.debug("cascade.tier1_early_exit", call_id=call_id, score=t1_result.score)
                t2_result = self._make_skipped_result(
                    2, "Skipped — Tier 1 confident authentic (early exit)"
                )
            else:
                # 4. Execute Tier 2: Deep Multilingual SSL (IndicWav2Vec + AASIST3, < 100ms)
                summary.tier2_invoked = True
                # Ensure language routing is available for target LoRA adapter selection
                lang_res = await language_task
                t2_result = await self._run_tier2(
                    request, t1_result.score, lang_res.code, summary
                )

        # 5. Await sidecar analytics
        prosody_vote, speaker_check, language_routing = await asyncio.gather(
            prosody_task, speaker_task, language_task
        )

        total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        summary.total_latency_ms = total_latency_ms

        fusion_input = FusionInput(
            segment=request.segment,
            features=request.segment.features,
            tier0_result=t0_result,
            tier1_result=t1_result,
            tier2_result=t2_result,
            prosody_vote=prosody_vote,
            speaker_check=speaker_check,
            language_routing=language_routing,
            context=request.context,
        )

        logger.debug(
            "cascade.completed",
            call_id=call_id,
            t0_early_exit=summary.tier0_early_exit,
            t1_early_exit=summary.tier1_early_exit,
            t2_invoked=summary.tier2_invoked,
            latency_ms=total_latency_ms,
        )

        return fusion_input, summary

    # --------------------------------------------------------------------------
    # Tier Runners with Bounded Timeouts & Resilience
    # --------------------------------------------------------------------------

    async def _run_tier0(
        self, request: DetectionRequest, summary: CascadeExecutionSummary
    ) -> DetectionResult:
        try:
            return await asyncio.wait_for(self.t0.predict(request), timeout=0.10)
        except TimeoutError:
            summary.degraded = True
            summary.degradation_reasons.append("Tier 0 timed out (>100ms)")
            logger.warning("cascade.tier0_timeout", call_id=request.segment.call_id)
            return DetectionResult(
                tier=0,
                score=0.50,
                confidence=0.0,
                label=DetectionLabel.INCONCLUSIVE,
                latency_ms=100.0,
                model_name="tier0-timeout",
                model_version="1.0",
                status=DetectionStatus.TIMEOUT,
                error="Tier 0 micro-DSP timed out",
            )
        except Exception as exc:
            summary.degraded = True
            summary.degradation_reasons.append(f"Tier 0 error: {exc}")
            logger.error("cascade.tier0_error", error=str(exc))
            return DetectionResult(
                tier=0,
                score=0.50,
                confidence=0.0,
                label=DetectionLabel.INCONCLUSIVE,
                latency_ms=1.0,
                model_name="tier0-error",
                model_version="1.0",
                status=DetectionStatus.ERROR,
                error=str(exc),
            )

    async def _run_tier1(
        self, request: DetectionRequest, summary: CascadeExecutionSummary
    ) -> DetectionResult:
        try:
            return await asyncio.wait_for(self.t1.predict(request), timeout=0.50)
        except TimeoutError:
            summary.degraded = True
            summary.degradation_reasons.append("Tier 1 timed out (>500ms)")
            logger.warning("cascade.tier1_timeout", call_id=request.segment.call_id)
            return DetectionResult(
                tier=1,
                score=0.50,
                confidence=0.0,
                label=DetectionLabel.INCONCLUSIVE,
                latency_ms=500.0,
                model_name="tier1-timeout",
                model_version="1.0",
                status=DetectionStatus.TIMEOUT,
                error="Tier 1 AASIST-L timed out",
            )
        except Exception as exc:
            summary.degraded = True
            summary.degradation_reasons.append(f"Tier 1 error: {exc}")
            logger.error("cascade.tier1_error", error=str(exc))
            return DetectionResult(
                tier=1,
                score=0.50,
                confidence=0.0,
                label=DetectionLabel.INCONCLUSIVE,
                latency_ms=10.0,
                model_name="tier1-error",
                model_version="1.0",
                status=DetectionStatus.ERROR,
                error=str(exc),
            )

    async def _run_tier2(
        self,
        request: DetectionRequest,
        tier1_score: float,
        language_code: str,
        summary: CascadeExecutionSummary,
    ) -> DetectionResult:
        try:
            req_with_lang = request.model_copy()
            if not req_with_lang.language_override and language_code != "und":
                req_with_lang.language_override = language_code
            return await asyncio.wait_for(
                self.t2.predict(req_with_lang, tier1_score=tier1_score), timeout=1.50
            )
        except TimeoutError:
            summary.degraded = True
            summary.degradation_reasons.append("Tier 2 timed out (>1500ms)")
            logger.warning("cascade.tier2_timeout", call_id=request.segment.call_id)
            return DetectionResult(
                tier=2,
                score=tier1_score,  # Fallback to Tier 1 score
                confidence=0.50,
                label=DetectionLabel.SUSPICIOUS,
                latency_ms=1500.0,
                model_name="tier2-timeout",
                model_version="1.0",
                status=DetectionStatus.TIMEOUT,
                error="Tier 2 deep SSL timed out",
            )
        except Exception as exc:
            summary.degraded = True
            summary.degradation_reasons.append(f"Tier 2 error: {exc}")
            logger.error("cascade.tier2_error", error=str(exc))
            return DetectionResult(
                tier=2,
                score=tier1_score,
                confidence=0.50,
                label=DetectionLabel.SUSPICIOUS,
                latency_ms=20.0,
                model_name="tier2-error",
                model_version="1.0",
                status=DetectionStatus.ERROR,
                error=str(exc),
            )

    # --------------------------------------------------------------------------
    # Safe Sidecar Analytics
    # --------------------------------------------------------------------------

    async def _safe_prosody(
        self, request: DetectionRequest, summary: CascadeExecutionSummary
    ) -> SignalVote:
        try:
            return await self.prosody.analyze(request)
        except Exception as exc:
            summary.degraded = True
            summary.degradation_reasons.append(f"Prosody error: {exc}")
            return SignalVote(
                id="prosody",
                label="Prosody / behavioural biomarkers",
                score=0.15,
                weight=0.10,
                detail="Prosody analysis degraded or unavailable.",
            )

    async def _safe_speaker(
        self, request: DetectionRequest, summary: CascadeExecutionSummary
    ) -> SpeakerCheckResult:
        try:
            return await self.speaker.verify(request)
        except Exception as exc:
            summary.degraded = True
            summary.degradation_reasons.append(f"Speaker verification error: {exc}")
            return SpeakerCheckResult(
                enrolled=False,
                claimed_speaker=request.context.claimed_speaker,
                cosine_similarity=None,
                mismatch=False,
                note="Speaker verification unavailable due to error.",
            )

    async def _safe_language(
        self, request: DetectionRequest, summary: CascadeExecutionSummary
    ) -> LanguageRoutingResult:
        try:
            return await self.language.route(request)
        except Exception as exc:
            summary.degraded = True
            summary.degradation_reasons.append(f"Language routing error: {exc}")
            return LanguageRoutingResult(
                detected="Undetermined",
                code="und",
                confidence=0.0,
                adapter="language-agnostic",
                source=LanguageRoutingSource.UNDETERMINED,
                note="Language router unavailable.",
            )

    def _make_skipped_result(self, tier: int, reason: str) -> DetectionResult:
        return DetectionResult(
            tier=tier,
            score=0.0,
            confidence=1.0,
            label=DetectionLabel.AUTHENTIC,
            latency_ms=0.0,
            model_name=f"tier{tier}-skipped",
            model_version="1.0",
            signals={"reason": reason},
            status=DetectionStatus.SKIPPED,
            error=None,
        )
