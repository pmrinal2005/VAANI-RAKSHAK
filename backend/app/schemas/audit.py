# ==============================================================================
# VAANI-RAKSHAK — Audit Ledger Schemas (R4 Boundary)
# Strongly typed Pydantic models for cryptographic audit blocks, chain proofs,
# and tamper verification reports.
# ==============================================================================

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AuditBlockType


class AuditBlockResponse(BaseModel):
    """Canonical representation of an immutable audit ledger block."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    index: int = Field(..., ge=0, description="Sequential monotonic block index")
    timestamp: int = Field(..., description="Epoch milliseconds when block was anchored")
    type: AuditBlockType = Field(..., description="Classification category of the audit event")
    call_id: str | None = Field(
        default=None,
        alias="callId",
        description="Associated call session ID",
    )
    segment_id: str | None = Field(default=None, alias="segmentId", description="Audio segment ID")
    payload_hash: str = Field(
        ...,
        alias="payloadHash",
        description="Irreversible SHA-256 digest of the canonical payload",
    )
    summary: str = Field(..., description="Human-readable event summary")
    risk_score: int | None = Field(
        default=None,
        alias="riskScore",
        ge=0,
        le=100,
        description="Assigned calibrated risk score",
    )
    actor: str = Field(default="detection-node", description="Signing authority or service")
    prev_hash: str = Field(
        ...,
        alias="prevHash",
        description="SHA-256 hash of previous block in the chain",
    )
    hash: str = Field(..., description="SHA-256 cryptographic digest of this block")
    nonce: int = Field(default=0, ge=0, description="Proof-of-work or sequence nonce")


class ChainVerificationResponse(BaseModel):
    """Integrity audit verification status report for the entire hash chain."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    is_valid: bool = Field(
        ...,
        alias="isValid",
        description="Whether cryptographic chain is intact",
    )
    total_blocks: int = Field(
        ...,
        alias="totalBlocks",
        description="Total blocks currently in ledger",
    )
    tampered_block_index: int | None = Field(
        default=None,
        alias="tamperedBlockIndex",
        description="Index of first broken/tampered block if invalid",
    )
    message: str = Field(..., description="Verification status summary")
    verified_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        alias="verifiedAt",
        description="Verification timestamp in UTC",
    )


class AuditProofBundle(BaseModel):
    """
    Cryptographic verification receipt for a specific call session,
    structured for consumption by downstream R4 blockchain anchoring.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    call_id: str = Field(..., alias="callId")
    block_count: int = Field(..., alias="blockCount")
    blocks: list[AuditBlockResponse] = Field(default_factory=list)
    chain_head_index: int = Field(..., alias="chainHeadIndex")
    chain_head_hash: str = Field(..., alias="chainHeadHash")
    is_valid: bool = Field(..., alias="isValid")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        alias="generatedAt",
    )
