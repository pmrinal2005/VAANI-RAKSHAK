# ==============================================================================
# VAANI-RAKSHAK — Cryptographic Audit Ledger API Routes (R4 Boundary)
# Verifiable tamper-evident compliance endpoints, block queries, and proof bundles.
# ==============================================================================

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import AuditDep
from app.domain.enums import AuditBlockType
from app.integrations.audit.ledger import CryptographicAuditLedger
from app.schemas.audit import (
    AuditBlockResponse,
    AuditProofBundle,
    ChainVerificationResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit & Ledger"])


@router.get(
    "/blocks",
    response_model=list[AuditBlockResponse],
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Query audit ledger blocks",
    description=(
        "Retrieve paginated cryptographic blocks with optional call ID "
        "and block type filters."
    ),
)
async def list_audit_blocks(
    ledger: AuditDep,
    call_id: Annotated[
        str | None,
        Query(description="Filter by specific call session ID", alias="callId"),
    ] = None,
    block_type: Annotated[
        AuditBlockType | None,
        Query(description="Filter by event block category", alias="blockType"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Max blocks to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> list[AuditBlockResponse]:
    blocks = await ledger.get_blocks(
        call_id=call_id,
        block_type=block_type,
        limit=limit,
        offset=offset,
    )
    return [
        AuditBlockResponse(
            index=b.index,
            timestamp=b.timestamp,
            type=b.type,
            call_id=b.call_id,
            segment_id=b.segment_id,
            payload_hash=b.payload_hash,
            summary=b.summary,
            risk_score=b.risk_score,
            actor=b.actor,
            prev_hash=b.prev_hash,
            hash=b.hash,
            nonce=b.nonce,
        )
        for b in blocks
    ]


@router.get(
    "/blocks/{block_index}",
    response_model=AuditBlockResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Get single audit block by monotonic index",
)
async def get_audit_block_by_index(
    block_index: int,
    ledger: AuditDep,
) -> AuditBlockResponse:
    if isinstance(ledger, CryptographicAuditLedger):
        block = await ledger.get_block_by_index(block_index)
    else:
        blocks = await ledger.get_blocks()
        block = blocks[block_index] if 0 <= block_index < len(blocks) else None

    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit block at index {block_index} not found.",
        )

    return AuditBlockResponse(
        index=block.index,
        timestamp=block.timestamp,
        type=block.type,
        call_id=block.call_id,
        segment_id=block.segment_id,
        payload_hash=block.payload_hash,
        summary=block.summary,
        risk_score=block.risk_score,
        actor=block.actor,
        prev_hash=block.prev_hash,
        hash=block.hash,
        nonce=block.nonce,
    )


@router.get(
    "/calls/{call_id}",
    response_model=list[AuditBlockResponse],
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Get full audit trail for a specific call session",
)
async def get_call_audit_trail(
    call_id: str,
    ledger: AuditDep,
) -> list[AuditBlockResponse]:
    blocks = await ledger.get_blocks(call_id=call_id, limit=5000)
    return [
        AuditBlockResponse(
            index=b.index,
            timestamp=b.timestamp,
            type=b.type,
            call_id=b.call_id,
            segment_id=b.segment_id,
            payload_hash=b.payload_hash,
            summary=b.summary,
            risk_score=b.risk_score,
            actor=b.actor,
            prev_hash=b.prev_hash,
            hash=b.hash,
            nonce=b.nonce,
        )
        for b in blocks
    ]


@router.get(
    "/verify",
    response_model=ChainVerificationResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Verify cryptographic integrity of the entire audit ledger",
    description=(
        "Validates sequential block indexing, previous block hash linkage, "
        "and SHA-256 block hash integrity."
    ),
)
async def verify_audit_chain(
    ledger: AuditDep,
) -> ChainVerificationResponse:
    is_valid, broken_index, msg = await ledger.verify_chain()
    if isinstance(ledger, CryptographicAuditLedger):
        total_blocks = await ledger.get_total_count()
    else:
        blocks = await ledger.get_blocks()
        total_blocks = len(blocks)

    return ChainVerificationResponse(
        is_valid=is_valid,
        total_blocks=total_blocks,
        tampered_block_index=broken_index,
        message=msg or "",
    )


@router.get(
    "/proof/{call_id}",
    response_model=AuditProofBundle,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Generate verifiable audit proof bundle for R4 blockchain anchoring",
)
async def generate_audit_proof(
    call_id: str,
    ledger: AuditDep,
) -> AuditProofBundle:
    if isinstance(ledger, CryptographicAuditLedger):
        proof = await ledger.generate_call_proof(call_id)
        if proof is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No audit blocks found for call '{call_id}'.",
            )
        return proof

    # Fallback for mock ledger
    blocks = await ledger.get_blocks(call_id=call_id)
    if not blocks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit blocks found for call '{call_id}'.",
        )

    all_blocks = await ledger.get_blocks()
    is_valid, _, _ = await ledger.verify_chain()

    return AuditProofBundle(
        call_id=call_id,
        block_count=len(blocks),
        blocks=[
            AuditBlockResponse(
                index=b.index,
                timestamp=b.timestamp,
                type=b.type,
                call_id=b.call_id,
                segment_id=b.segment_id,
                payload_hash=b.payload_hash,
                summary=b.summary,
                risk_score=b.risk_score,
                actor=b.actor,
                prev_hash=b.prev_hash,
                hash=b.hash,
                nonce=b.nonce,
            )
            for b in blocks
        ],
        chain_head_index=all_blocks[-1].index,
        chain_head_hash=all_blocks[-1].hash,
        is_valid=is_valid,
    )
