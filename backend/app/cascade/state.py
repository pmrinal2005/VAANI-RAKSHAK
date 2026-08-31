# ==============================================================================
# VAANI-RAKSHAK — Cascade Execution State & Telemetry Models
# Captures per-segment tier transitions, latency breakdown, and degradation flags.
# ==============================================================================

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CascadeExecutionSummary(BaseModel):
    """Telemetry summary of the cascade decision path for a single audio segment."""

    model_config = ConfigDict(extra="ignore")

    call_id: str
    segment_id: str
    tier0_invoked: bool = True
    tier0_early_exit: bool = False
    tier1_invoked: bool = False
    tier1_early_exit: bool = False
    tier2_invoked: bool = False
    tier_disagreement: bool = False
    disagreement_delta: float = 0.0
    total_latency_ms: float = 0.0
    degraded: bool = False
    degradation_reasons: list[str] = Field(default_factory=list)
