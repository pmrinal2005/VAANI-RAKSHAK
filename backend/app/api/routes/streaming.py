# ==============================================================================
# VAANI-RAKSHAK — Real-Time WebSocket & Server-Sent Events (SSE) Routes
# Interactive bi-directional audio chunk streaming and global SOC telemetry.
# ==============================================================================

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

import structlog
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    AuditDep,
    CascadeOrchestratorDep,
    ConnectionManagerDep,
    EventProducerDep,
    FusionDep,
)
from app.api.routes.score import score_audio_segment
from app.schemas.detection import DetectionRequest

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Streaming"])


@router.websocket("/ws/calls/{call_id}")
async def websocket_call_stream(
    websocket: WebSocket,
    call_id: str,
    manager: ConnectionManagerDep,
    orchestrator: CascadeOrchestratorDep,
    fusion_engine: FusionDep,
    event_producer: EventProducerDep,
    audit_ledger: AuditDep,
) -> None:
    """
    Bi-directional interactive WebSocket connection for a specific call session.
    Receives real-time audio chunks, executes the 3-tier cascade and multi-modal fusion,
    and returns immediate detection results with policy recommendations.
    """
    await manager.connect_call(call_id, websocket)

    # Send initial welcome payload
    await manager.send_personal_message(
        {
            "type": "connection_established",
            "callId": call_id,
            "message": f"Connected to real-time risk stream for call '{call_id}'.",
        },
        websocket,
    )

    max_msg_bytes = 5 * 1024 * 1024
    max_chunk_bytes = 10 * 1024 * 1024
    max_rate_per_sec = 20

    window_start = asyncio.get_event_loop().time()
    message_count = 0

    try:
        while True:
            raw_text = await websocket.receive_text()

            # 1. Check message size
            if len(raw_text.encode("utf-8")) > max_msg_bytes:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "code": "MESSAGE_TOO_LARGE",
                        "message": "WebSocket message exceeds maximum allowed size.",
                    },
                    websocket,
                )
                continue

            # 2. Check message rate limit (sliding 1-second window)
            now = asyncio.get_event_loop().time()
            if now - window_start >= 1.0:
                window_start = now
                message_count = 0
            message_count += 1
            if message_count > max_rate_per_sec:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "WebSocket message rate limit exceeded (max 20 msg/sec).",
                    },
                    websocket,
                )
                continue

            try:
                data = json.loads(raw_text)
            except Exception:
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON format payload."},
                    websocket,
                )
                continue

            msg_type = data.get("type", "audio_chunk")

            # Handle Heartbeat Ping
            if msg_type == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)
                continue

            # Handle Audio Chunk or Detection Request
            try:
                payload_dict = data.get("request", data)

                # Check audio chunk size in payload
                if isinstance(payload_dict, dict) and "segment" in payload_dict:
                    seg_dict = payload_dict["segment"]
                    if isinstance(seg_dict, dict):
                        seg_dict["callId"] = call_id
                        raw_b64 = seg_dict.get("rawPcmB64", "")
                        if isinstance(raw_b64, str) and len(raw_b64) > max_chunk_bytes:
                            await manager.send_personal_message(
                                {
                                    "type": "error",
                                    "code": "CHUNK_TOO_LARGE",
                                    "message": "Audio chunk payload exceeds maximum allowed size.",
                                },
                                websocket,
                            )
                            continue

                detection_req = DetectionRequest.model_validate(payload_dict)

                # Execute scoring pipeline (reuses orchestrator, fusion, kafka, and audit)
                fusion_output = await score_audio_segment(
                    request=detection_req,
                    orchestrator=orchestrator,
                    fusion_engine=fusion_engine,
                    event_producer=event_producer,
                    audit_ledger=audit_ledger,
                )

                # Return detection result directly to the stream caller
                await manager.send_personal_message(
                    {
                        "type": "detection_result",
                        "callId": call_id,
                        "payload": fusion_output.model_dump(mode="json", by_alias=True),
                    },
                    websocket,
                )

            except Exception as exc:
                logger.warning(
                    "ws_call.processing_error",
                    call_id=call_id,
                    error=str(exc),
                )
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": f"Failed to process detection chunk: {exc}",
                    },
                    websocket,
                )

    except WebSocketDisconnect:
        logger.info("ws_call.client_disconnected", call_id=call_id)
    except Exception as exc:
        logger.warning("ws_call.connection_error", call_id=call_id, error=str(exc))
    finally:
        await manager.disconnect_call(call_id, websocket)


@router.websocket("/ws/events")
async def websocket_global_events(
    websocket: WebSocket,
    manager: ConnectionManagerDep,
) -> None:
    """
    Broadcast WebSocket channel for Security Operations Center (SOC) dashboards
    and fraud investigator queues. Receives all risk, fusion, and workflow events.
    """
    await manager.connect_global(websocket)

    await manager.send_personal_message(
        {
            "type": "connection_established",
            "channel": "soc_global_broadcast",
            "message": "Connected to VAANI-RAKSHAK global SOC event stream.",
        },
        websocket,
    )

    try:
        while True:
            # Keepalive / incoming ping listener
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)
    except WebSocketDisconnect:
        logger.info("ws_global.client_disconnected")
    except Exception as exc:
        logger.warning("ws_global.connection_error", error=str(exc))
    finally:
        await manager.disconnect_global(websocket)


@router.get(
    "/events/stream",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Server-Sent Events (SSE) live telemetry feed",
    description=(
        "Standard EventSource compatible HTTP stream delivering real-time "
        "risk alerts and fusion events."
    ),
)
async def sse_event_stream(
    manager: ConnectionManagerDep,
) -> StreamingResponse:
    """
    Streams Server-Sent Events (SSE) to connected HTTP clients.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = manager.subscribe_sse()
        # Initial greeting packet
        yield f"event: ping\ndata: {json.dumps({'status': 'connected'})}\n\n"

        try:
            while True:
                try:
                    # Wait for next event or send keepalive ping every 15s
                    item = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_type = item.get("event", "message")
                    event_data = json.dumps(item.get("data", {}))
                    yield f"event: {event_type}\ndata: {event_data}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            manager.unsubscribe_sse(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
