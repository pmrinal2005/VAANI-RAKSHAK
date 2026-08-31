# ==============================================================================
# VAANI-RAKSHAK — Production Scoring REST API Routes
# Handles JSON detection requests and multipart audio uploads.
# ==============================================================================

from __future__ import annotations

import base64
import json
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import (
    AuditDep,
    CascadeOrchestratorDep,
    EventProducerDep,
    FusionDep,
)
from app.domain.enums import Decision, MockScenario
from app.domain.topics import KafkaTopic
from app.schemas.audio import AudioSegment
from app.schemas.context import CallContext
from app.schemas.detection import DetectionRequest, FusionOutput
from app.schemas.events import (
    EventEnvelope,
    EventHeader,
    FusionResultPayload,
    RiskEventPayload,
    WorkflowEventPayload,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Scoring"])

ALLOWED_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/webm",
    "audio/flac",
    "audio/x-flac",
    "application/octet-stream",  # Raw PCM
}

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg", ".webm", ".flac", ".pcm", ".raw"}


@router.post(
    "/score",
    response_model=FusionOutput,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Score an audio segment or extracted feature vector",
    description=(
        "Executes the 3-tier cascade countermeasure engine, evaluates multi-modal "
        "evidence fusion, applies zero-trust banking policy, and logs an audit block."
    ),
)
async def score_audio_segment(
    request: DetectionRequest,
    orchestrator: CascadeOrchestratorDep,
    fusion_engine: FusionDep,
    event_producer: EventProducerDep,
    audit_ledger: AuditDep,
) -> FusionOutput:
    call_id = request.segment.call_id
    segment_id = request.segment.segment_id

    logger.info(
        "score.request_received",
        call_id=call_id,
        segment_id=segment_id,
        scenario=request.scenario_override.value if request.scenario_override else "auto",
        force_tier2=request.force_tier2,
    )

    # 1. Run 3-Tier Cascade Orchestrator
    fusion_input, _cascade_summary = await orchestrator.run_cascade(request)

    # 2. Run Multi-Modal Evidence Fusion & Policy Engine
    fusion_output = await fusion_engine.fuse(fusion_input)

    # 3. Publish Asynchronous Pipeline Events to Kafka / Event Bus
    try:
        # Publish Fusion Result Event
        fusion_payload = FusionResultPayload(
            call_id=call_id,
            segment_id=segment_id,
            output=fusion_output,
        )
        fusion_envelope: EventEnvelope[FusionResultPayload] = EventEnvelope(
            header=EventHeader(
                correlation_id=call_id,
                event_type="fusion.result",
            ),
            payload=fusion_payload,
        )
        await event_producer.send(
            KafkaTopic.FUSION_RESULT,
            fusion_envelope,
            key=call_id,
        )

        # Publish Risk & Workflow Interceptor Alerts if elevated/high/critical
        if fusion_output.risk_score >= 40 or fusion_output.requires_out_of_band:
            risk_payload = RiskEventPayload(
                call_id=call_id,
                risk_score=fusion_output.risk_score,
                band=fusion_output.band,
                verdict=fusion_output.verdict,
                requires_out_of_band=fusion_output.requires_out_of_band,
                explanation=fusion_output.smart_explanation,
            )
            risk_envelope: EventEnvelope[RiskEventPayload] = EventEnvelope(
                header=EventHeader(
                    correlation_id=call_id,
                    event_type="risk.events",
                ),
                payload=risk_payload,
            )
            await event_producer.send(
                KafkaTopic.RISK_EVENTS,
                risk_envelope,
                key=call_id,
            )

            # Map recommended action string to Decision enum
            try:
                dec_enum = Decision(fusion_output.recommended_action)
            except ValueError:
                dec_enum = Decision.ALLOW

            workflow_payload = WorkflowEventPayload(
                call_id=call_id,
                decision=dec_enum,
                reason=fusion_output.smart_explanation,
                action_taken=f"INTERCEPTOR_{fusion_output.recommended_action}",
            )
            workflow_envelope: EventEnvelope[WorkflowEventPayload] = EventEnvelope(
                header=EventHeader(
                    correlation_id=call_id,
                    event_type="workflow.events",
                ),
                payload=workflow_payload,
            )
            await event_producer.send(
                KafkaTopic.WORKFLOW_EVENTS,
                workflow_envelope,
                key=call_id,
            )

    except Exception as exc:
        logger.warning(
            "score.kafka_publish_failed",
            call_id=call_id,
            error=str(exc),
        )

    # 4. Append Immutable Audit Ledger Block (R4 boundary)
    try:
        from app.domain.enums import AuditBlockType

        await audit_ledger.append_block(
            event_type=AuditBlockType.RISK_SCORE,
            payload_plaintext=fusion_output.model_dump_json(),
            summary=(
                f"Risk Score {fusion_output.risk_score}/100 [{fusion_output.band.value}] — "
                f"Action: {fusion_output.recommended_action}"
            ),
            actor="detection-pipeline",
            risk_score=fusion_output.risk_score,
            call_id=call_id,
            segment_id=request.segment.segment_id,
        )
    except Exception as exc:
        logger.warning(
            "score.audit_ledger_failed",
            call_id=call_id,
            error=str(exc),
        )

    return fusion_output


@router.post(
    "/score/upload",
    response_model=FusionOutput,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Upload an audio file for deepfake scoring",
    description=(
        "Accepts multipart audio file upload (WAV, MP3, OGG, WebM, FLAC) "
        "and executes full scoring pipeline."
    ),
)
async def score_audio_upload(
    orchestrator: CascadeOrchestratorDep,
    fusion_engine: FusionDep,
    event_producer: EventProducerDep,
    audit_ledger: AuditDep,
    file: Annotated[
        UploadFile,
        File(description="Audio file payload (WAV, MP3, OGG, WebM, FLAC)"),
    ],
    context_json: Annotated[
        str | None,
        Form(description="Optional JSON serialized CallContext"),
    ] = None,
    scenario: Annotated[
        MockScenario | None,
        Form(description="Optional deterministic mock scenario override"),
    ] = None,
    force_tier2: Annotated[
        bool,
        Form(description="Force execution through all 3 tiers"),
    ] = False,
    claimed_speaker: Annotated[
        str | None,
        Form(description="Optional caller name for speaker verification"),
    ] = None,
    language_override: Annotated[
        str | None,
        Form(description="Optional ISO language code override"),
    ] = None,
) -> FusionOutput:
    # 1. Validate File Metadata & MIME type
    filename = file.filename or "upload.wav"
    has_valid_ext = any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)
    has_valid_mime = file.content_type in ALLOWED_MIME_TYPES or file.content_type is None

    if not has_valid_ext and not has_valid_mime:
        logger.warning(
            "score_upload.invalid_file_type",
            filename=filename,
            mime=file.content_type,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file format '{filename}'. "
                "Allowed formats: WAV, MP3, OGG, WebM, FLAC."
            ),
        )

    # 2. Read audio payload bytes
    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty (0 bytes).",
        )

    # 3. Parse Context & Speaker
    if context_json:
        try:
            parsed_ctx_data = json.loads(context_json)
            context = CallContext.model_validate(parsed_ctx_data)
        except Exception as exc:
            logger.warning("score_upload.invalid_context_json", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid context_json payload: {exc}",
            ) from exc
    else:
        context = CallContext()

    if claimed_speaker:
        context.claimed_speaker = claimed_speaker

    # 4. Construct DetectionRequest
    call_id = f"upload-{uuid.uuid4().hex[:8]}"
    raw_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    # Approx duration assuming 16kHz 16-bit mono PCM (32000 bytes/sec)
    approx_duration = round(len(audio_bytes) / 32000.0, 2)

    detection_req = DetectionRequest(
        segment=AudioSegment(
            call_id=call_id,
            segment_id="seg-001",
            raw_pcm_b64=raw_b64,
            duration_sec=approx_duration,
        ),
        context=context,
        force_tier2=force_tier2,
        scenario_override=scenario,
        language_override=language_override,
    )

    # 5. Execute unified scoring pipeline
    return await score_audio_segment(
        request=detection_req,
        orchestrator=orchestrator,
        fusion_engine=fusion_engine,
        event_producer=event_producer,
        audit_ledger=audit_ledger,
    )
