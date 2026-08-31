# ==============================================================================
# VAANI-RAKSHAK — Simulated Telephony API Routes
# Manages active call simulations, live risk progression, and cancellation.
# ==============================================================================

from __future__ import annotations

import asyncio
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import (
    AuditDep,
    CallSessionManagerDep,
    CascadeOrchestratorDep,
    EventProducerDep,
    FusionDep,
    SettingsDep,
)
from app.telephony.session import (
    SimulationRequest,
    SimulationStatusResponse,
)
from app.telephony.simulator import TelephonySimulator

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/calls", tags=["Telephony Simulation"])


@router.post(
    "/simulate",
    response_model=SimulationStatusResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an asynchronous simulated telephony call",
    description=(
        "Launches a background telephony simulation emitting real-time RTP chunks. "
        "Audio chunks are processed through the cascade and multi-modal fusion pipelines, "
        "and streamed live over WebSockets and SSE."
    ),
)
async def simulate_call(
    request: SimulationRequest,
    session_manager: CallSessionManagerDep,
    orchestrator: CascadeOrchestratorDep,
    fusion_engine: FusionDep,
    event_producer: EventProducerDep,
    audit_ledger: AuditDep,
    settings: SettingsDep,
) -> SimulationStatusResponse:
    # 1. Create registered call session
    session = await session_manager.create_session(request)

    # 2. Instantiate simulator
    simulator = TelephonySimulator(
        orchestrator=orchestrator,
        fusion_engine=fusion_engine,
        event_producer=event_producer,
        audit_ledger=audit_ledger,
    )

    # 3. Launch background async simulation task
    task = asyncio.create_task(simulator.run_call(session))
    session.task = task

    logger.info(
        "calls.simulation_launched",
        call_id=session.call_id,
        pattern=session.pattern.value,
        duration=session.total_duration_sec,
    )

    return session.to_status_response(api_prefix=settings.api_prefix)


@router.get(
    "/{call_id}/status",
    response_model=SimulationStatusResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Get status and temporal risk history of a call simulation",
)
async def get_call_simulation_status(
    call_id: str,
    session_manager: CallSessionManagerDep,
    settings: SettingsDep,
) -> SimulationStatusResponse:
    session = session_manager.get_session(call_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call simulation session '{call_id}' not found.",
        )
    return session.to_status_response(api_prefix=settings.api_prefix)


@router.post(
    "/{call_id}/stop",
    response_model=SimulationStatusResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Stop an ongoing call simulation",
)
async def stop_call_simulation(
    call_id: str,
    session_manager: CallSessionManagerDep,
    settings: SettingsDep,
) -> SimulationStatusResponse:
    stopped = await session_manager.stop_session(call_id)
    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call simulation session '{call_id}' not found.",
        )
    session = session_manager.get_session(call_id)
    assert session is not None
    return session.to_status_response(api_prefix=settings.api_prefix)


@router.get(
    "",
    response_model=list[SimulationStatusResponse],
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="List active and completed telephony simulations",
)
async def list_call_simulations(
    session_manager: CallSessionManagerDep,
    settings: SettingsDep,
    active_only: Annotated[
        bool,
        Query(
            description="Filter only currently active / ringing sessions",
            alias="activeOnly",
        ),
    ] = False,
) -> list[SimulationStatusResponse]:
    sessions = session_manager.list_sessions(active_only=active_only)
    return [s.to_status_response(api_prefix=settings.api_prefix) for s in sessions]
