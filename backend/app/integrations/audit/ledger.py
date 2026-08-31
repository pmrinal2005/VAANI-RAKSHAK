# ==============================================================================
# VAANI-RAKSHAK — Cryptographic SHA-256 Audit Ledger (R4 Boundary)
# Tamper-evident hash-chain ledger for anchoring risk assessments, zero-trust policy
# decisions, and compliance receipts for external R4 blockchain consumption.
# ==============================================================================

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel

from app.domain.enums import AuditBlockType
from app.integrations.audit.base import AuditBlock
from app.schemas.audit import AuditBlockResponse, AuditProofBundle

logger = structlog.get_logger(__name__)


def _canonical_serialize(payload: str | dict[str, Any] | BaseModel) -> str:
    """Deterministic canonical serialization for consistent payload hashing."""
    if isinstance(payload, BaseModel):
        # Dump model with sorted keys
        data = payload.model_dump(mode="json", by_alias=True)
        return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    if isinstance(payload, dict):
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    if isinstance(payload, str):
        # If string contains valid JSON, parse and canonicalize
        with contextlib.suppress(Exception):
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return json.dumps(parsed, sort_keys=True, separators=(",", ":"), default=str)
        return payload.strip()
    return str(payload).strip()


def _sha256(data: str) -> str:
    """Compute standard SHA-256 hexadecimal digest."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _compute_block_hash(
    index: int,
    timestamp: int,
    block_type: AuditBlockType,
    call_id: str | None,
    segment_id: str | None,
    payload_hash: str,
    prev_hash: str,
    nonce: int = 0,
) -> str:
    """
    Deterministic block hash calculation format:
    SHA-256("{index}:{timestamp}:{block_type}:{call_id}:{segment_id}:{payload_hash}:{prev_hash}:{nonce}")
    """
    material = (
        f"{index}:{timestamp}:{block_type.value}:{call_id or ''}:"
        f"{segment_id or ''}:{payload_hash}:{prev_hash}:{nonce}"
    )
    return _sha256(material)


class CryptographicAuditLedger:
    """
    Production-ready in-memory SHA-256 cryptographic audit ledger.
    Maintains a strictly ordered, immutable hash-chain of fraud detection decisions.
    """

    def __init__(self, genesis_actor: str = "consortium-governance") -> None:
        self.genesis_actor = genesis_actor
        self._chain: list[AuditBlock] = []
        self._lock = asyncio.Lock()
        self._initialize_genesis()

    def _initialize_genesis(self) -> None:
        """Create deterministic genesis block if ledger is uninitialized."""
        if not self._chain:
            genesis_payload = "VAANI-RAKSHAK-CONSORTIUM-GENESIS-V1"
            payload_hash = _sha256(genesis_payload)
            timestamp = 1700000000000  # Deterministic epoch ms
            prev_hash = "0" * 64

            block_hash = _compute_block_hash(
                index=0,
                timestamp=timestamp,
                block_type=AuditBlockType.GENESIS,
                call_id=None,
                segment_id=None,
                payload_hash=payload_hash,
                prev_hash=prev_hash,
                nonce=0,
            )

            genesis = AuditBlock(
                index=0,
                timestamp=timestamp,
                type=AuditBlockType.GENESIS,
                call_id=None,
                segment_id=None,
                payload_hash=payload_hash,
                summary="Consortium genesis block (RBI/CERT-In · Telecom · Banking Nodes).",
                actor=self.genesis_actor,
                prev_hash=prev_hash,
                hash=block_hash,
                nonce=0,
                risk_score=None,
            )
            self._chain.append(genesis)
            logger.info("audit_ledger.genesis_initialized", genesis_hash=genesis.hash)

    async def append_block(
        self,
        event_type: AuditBlockType,
        payload_plaintext: str | dict[str, Any] | BaseModel,
        summary: str,
        actor: str = "detection-node",
        risk_score: int | None = None,
        call_id: str | None = None,
        segment_id: str | None = None,
    ) -> AuditBlock:
        """
        Append an immutable event block to the ledger linked to the previous block hash.
        """
        canonical_str = _canonical_serialize(payload_plaintext)
        payload_hash = _sha256(canonical_str)
        timestamp = int(time.time() * 1000)

        async with self._lock:
            index = len(self._chain)
            prev_hash = self._chain[-1].hash

            block_hash = _compute_block_hash(
                index=index,
                timestamp=timestamp,
                block_type=event_type,
                call_id=call_id,
                segment_id=segment_id,
                payload_hash=payload_hash,
                prev_hash=prev_hash,
                nonce=0,
            )

            block = AuditBlock(
                index=index,
                timestamp=timestamp,
                type=event_type,
                call_id=call_id,
                segment_id=segment_id,
                payload_hash=payload_hash,
                summary=summary,
                actor=actor,
                prev_hash=prev_hash,
                hash=block_hash,
                nonce=0,
                risk_score=risk_score,
            )
            self._chain.append(block)

        logger.debug(
            "audit_ledger.block_appended",
            index=block.index,
            block_type=block.type.value,
            call_id=block.call_id,
            block_hash=block.hash,
        )
        return block

    async def verify_chain(self) -> tuple[bool, int | None, str | None]:
        """
        Verify cryptographic integrity across all blocks in the ledger.
        Returns (is_valid, broken_index, reason).
        """
        async with self._lock:
            chain_snapshot = list(self._chain)

        if not chain_snapshot:
            return False, 0, "Ledger is empty (missing genesis block)"

        for i, b in enumerate(chain_snapshot):
            # 1. Verify index ordering
            if b.index != i:
                return False, i, f"Invalid block index: expected {i}, got {b.index}"

            # 2. Verify previous hash linkage
            if i == 0:
                if b.prev_hash != "0" * 64:
                    return False, 0, "Genesis block prev_hash must be all zeros"
            else:
                prev_block = chain_snapshot[i - 1]
                if b.prev_hash != prev_block.hash:
                    return (
                        False,
                        i,
                        (
                            f"Broken hash link: block {i} prev_hash '{b.prev_hash}' != "
                            f"block {i-1} hash '{prev_block.hash}'"
                        ),
                    )

            # 3. Recompute and verify block hash
            expected_hash = _compute_block_hash(
                index=b.index,
                timestamp=b.timestamp,
                block_type=b.type,
                call_id=b.call_id,
                segment_id=b.segment_id,
                payload_hash=b.payload_hash,
                prev_hash=b.prev_hash,
                nonce=b.nonce,
            )
            if b.hash != expected_hash:
                return (
                    False,
                    i,
                    (
                        f"Tampered block hash at index {i}: "
                        f"stored '{b.hash}' != computed '{expected_hash}'"
                    ),
                )

        return True, None, "Ledger cryptographic integrity fully verified"

    async def get_blocks(
        self,
        call_id: str | None = None,
        block_type: AuditBlockType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditBlock]:
        """Query blocks with optional call_id/type filters and pagination."""
        async with self._lock:
            blocks = list(self._chain)

        if call_id is not None:
            blocks = [b for b in blocks if b.call_id == call_id]

        if block_type is not None:
            blocks = [b for b in blocks if b.type == block_type]

        return blocks[offset : offset + limit]

    async def get_block_by_index(self, index: int) -> AuditBlock | None:
        """Retrieve a specific block by its monotonic index."""
        async with self._lock:
            if 0 <= index < len(self._chain):
                return self._chain[index]
        return None

    async def get_total_count(self) -> int:
        """Return the current total number of blocks in the ledger."""
        async with self._lock:
            return len(self._chain)

    async def generate_call_proof(self, call_id: str) -> AuditProofBundle | None:
        """
        Generate cryptographic verification proof bundle for a specific call session.
        """
        call_blocks = await self.get_blocks(call_id=call_id, limit=10_000)
        if not call_blocks:
            return None

        is_valid, _, _ = await self.verify_chain()

        async with self._lock:
            chain_head = self._chain[-1]

        block_responses = [
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
            for b in call_blocks
        ]

        return AuditProofBundle(
            call_id=call_id,
            block_count=len(block_responses),
            blocks=block_responses,
            chain_head_index=chain_head.index,
            chain_head_hash=chain_head.hash,
            is_valid=is_valid,
            generated_at=datetime.now(UTC),
        )

    def tamper_block(self, index: int, new_payload: str = "CORRUPTED_PAYLOAD") -> None:
        """
        Mutate block payload to simulate tampering for integrity testing.
        """
        if 0 <= index < len(self._chain):
            old = self._chain[index]
            tampered = AuditBlock(
                index=old.index,
                timestamp=old.timestamp,
                type=old.type,
                call_id=old.call_id,
                segment_id=old.segment_id,
                payload_hash=_sha256(new_payload),
                summary=old.summary + " [TAMPERED]",
                actor=old.actor,
                prev_hash=old.prev_hash,
                hash=old.hash,  # Preserving old hash will cause verification mismatch
                nonce=old.nonce,
                risk_score=old.risk_score,
            )
            self._chain[index] = tampered
            logger.warning("audit_ledger.tamper_injected", index=index)
