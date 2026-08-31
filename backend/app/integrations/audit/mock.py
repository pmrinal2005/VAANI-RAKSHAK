# ==============================================================================
# VAANI-RAKSHAK — Immutable Audit Ledger Mock Adapter (R4 Boundary)
# In-memory SHA-256 hash-chain simulating a permissioned consortium blockchain.
# DPDP-Act Privacy: RAW AUDIO IS NEVER ANCHORED — only irreversible hashes & verdicts.
# ==============================================================================

from __future__ import annotations

import hashlib
import time

from app.domain.enums import AuditBlockType
from app.integrations.audit.base import AuditBlock


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MockAuditLedger:
    """
    Mock implementation of AuditLedger protocol.
    Maintains a cryptographic SHA-256 tamper-evident hash chain in memory.
    """

    def __init__(self, difficulty: int = 2) -> None:
        self.difficulty = difficulty
        self._chain: list[AuditBlock] = []
        self._ensure_genesis()

    def _ensure_genesis(self) -> None:
        if not self._chain:
            genesis_payload = "VAANI-RAKSHAK-CONSORTIUM-GENESIS"
            genesis = self._mine_block(
                index=0,
                block_type=AuditBlockType.GENESIS,
                payload_hash=_sha256(genesis_payload),
                summary="Consortium genesis block (banks · telecom · regulator/CERT-In nodes).",
                actor="consortium",
                prev_hash="0" * 64,
                risk_score=None,
            )
            self._chain.append(genesis)

    def _mine_block(
        self,
        index: int,
        block_type: AuditBlockType,
        payload_hash: str,
        summary: str,
        actor: str,
        prev_hash: str,
        risk_score: int | None,
    ) -> AuditBlock:
        timestamp = int(time.time() * 1000)
        prefix = "0" * self.difficulty
        nonce = 0

        while nonce < 200_000:
            material = (
                f"{index}|{timestamp}|{block_type.value}|{payload_hash}|"
                f"{summary}|{actor}|{prev_hash}|{nonce}"
            )
            h = _sha256(material)
            if h.startswith(prefix):
                return AuditBlock(
                    index=index,
                    timestamp=timestamp,
                    type=block_type,
                    payload_hash=payload_hash,
                    summary=summary,
                    actor=actor,
                    prev_hash=prev_hash,
                    hash=h,
                    nonce=nonce,
                    risk_score=risk_score,
                )
            nonce += 1

        # Fallback if max nonce reached
        material = (
            f"{index}|{timestamp}|{block_type.value}|{payload_hash}|"
            f"{summary}|{actor}|{prev_hash}|{nonce}"
        )
        return AuditBlock(
            index=index,
            timestamp=timestamp,
            type=block_type,
            payload_hash=payload_hash,
            summary=summary,
            actor=actor,
            prev_hash=prev_hash,
            hash=_sha256(material),
            nonce=nonce,
            risk_score=risk_score,
        )

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
        prev = self._chain[-1]
        payload_hash = _sha256(payload_plaintext)
        block = self._mine_block(
            index=len(self._chain),
            block_type=event_type,
            payload_hash=payload_hash,
            summary=summary,
            actor=actor,
            prev_hash=prev.hash,
            risk_score=risk_score,
        )
        block.call_id = call_id
        block.segment_id = segment_id
        self._chain.append(block)
        return block

    async def verify_chain(self) -> tuple[bool, int | None, str | None]:
        for i, b in enumerate(self._chain):
            material = (
                f"{b.index}|{b.timestamp}|{b.type.value}|{b.payload_hash}|"
                f"{b.summary}|{b.actor}|{b.prev_hash}|{b.nonce}"
            )
            recomputed = _sha256(material)
            if recomputed != b.hash:
                return False, i, f"Hash mismatch at block {i}"
            if i > 0 and b.prev_hash != self._chain[i - 1].hash:
                return False, i, f"Broken link at block {i}"
        return True, None, "Ledger integrity verified"

    async def get_blocks(
        self,
        call_id: str | None = None,
        block_type: AuditBlockType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditBlock]:
        res = self._chain
        if call_id is not None:
            res = [b for b in res if b.call_id == call_id]
        if block_type is not None:
            res = [b for b in res if b.type == block_type]
        return res[offset : offset + limit]

    def tamper_block(self, index: int) -> None:
        """Mutate block content to verify tamper-evidence detection."""
        if 0 <= index < len(self._chain):
            old = self._chain[index]
            self._chain[index] = AuditBlock(
                index=old.index,
                timestamp=old.timestamp,
                type=old.type,
                payload_hash=_sha256("TAMPERED_CONTENT"),
                summary=old.summary + " ⚠ TAMPERED",
                actor=old.actor,
                prev_hash=old.prev_hash,
                hash=old.hash.replace("0", "f").replace("a", "0"),
                nonce=old.nonce,
                risk_score=old.risk_score,
            )
