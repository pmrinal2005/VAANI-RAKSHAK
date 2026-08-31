# ==============================================================================
# VAANI-RAKSHAK — Audit Ledger Protocol Interface (R4 Boundary)
# Prepares R2 for future Hyperledger Fabric anchoring without implementing R4 infrastructure.
# NO RAW AUDIO IS EVER ANCHORED — only cryptographic digests and decision summaries.
# ==============================================================================

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AuditBlockType


class AuditBlock(BaseModel):
    """Canonical representation of an immutable ledger block."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    index: int = Field(..., ge=0)
    timestamp: int = Field(..., description="Epoch milliseconds")
    type: AuditBlockType = Field(...)
    call_id: str | None = Field(
        default=None,
        alias="callId",
        description="Associated call session ID",
    )
    segment_id: str | None = Field(default=None, alias="segmentId", description="Audio segment ID")
    payload_hash: str = Field(..., alias="payloadHash", description="SHA-256 digest of payload")
    summary: str = Field(...)
    risk_score: int | None = Field(default=None, alias="riskScore", ge=0, le=100)
    actor: str = Field(default="detection-node")
    prev_hash: str = Field(..., alias="prevHash", description="SHA-256 digest of predecessor block")
    hash: str = Field(..., description="SHA-256 block hash")
    nonce: int = Field(default=0, ge=0)


@runtime_checkable
class AuditLedger(Protocol):
    """
    Interface for anchoring risk assessments, policy overrides, and consent records.
    Future Fabric implementation (R4), MockAuditLedger, and CryptographicAuditLedger
    all implement this interface.
    """

    async def append_block(
        self,
        event_type: AuditBlockType,
        payload_plaintext: str,
        summary: str,
        actor: str = "detection-node",
        risk_score: int | None = None,
        call_id: str | None = None,
        segment_id: str | None = None,
    ) -> AuditBlock:
        """Append an event to the ledger and return the newly formed block."""
        ...

    async def verify_chain(self) -> tuple[bool, int | None, str | None]:
        """
        Verify the cryptographic integrity of the ledger.
        Returns (is_valid, broken_at_index, reason).
        """
        ...

    async def get_blocks(
        self,
        call_id: str | None = None,
        block_type: AuditBlockType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditBlock]:
        """Return blocks matching query parameters."""
        ...
