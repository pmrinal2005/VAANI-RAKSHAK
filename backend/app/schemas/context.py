# ==============================================================================
# VAANI-RAKSHAK — Call Context Schema
# Telephony, transaction, and operational risk signals.
# Business policy logic is intentionally kept separate from this pure schema.
# ==============================================================================

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CallContext(BaseModel):
    """
    Metadata surrounding an inbound or ongoing voice interaction.
    Compatible with frontend CallContext while adding enterprise extensions.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    channel: str = Field(
        default="Upload / Softphone", description="Source channel (SIP, WebRTC, Upload, IVR)"
    )
    ani_reputation: float = Field(
        default=0.6,
        alias="aniReputation",
        ge=0.0,
        le=1.0,
        description="Reputation score of the calling number (0.0=known scammer, 1.0=trusted)",
    )
    known_contact: bool = Field(
        default=True,
        alias="knownContact",
        description="Whether the caller phone number matches customer records",
    )
    transaction_type: str = Field(
        default="customer-service",
        alias="transactionType",
        description="Type of operation requested (e.g. kyc, otp, wire-transfer, recovery)",
    )
    transaction_value_inr: float = Field(
        default=0.0,
        alias="transactionValueInr",
        ge=0.0,
        description="Monetary transaction amount in Indian Rupees (INR)",
    )
    time_of_day_risk: float = Field(
        default=0.2,
        alias="timeOfDayRisk",
        ge=0.0,
        le=1.0,
        description="Temporal anomaly score based on account usage patterns",
    )
    claimed_speaker: str | None = Field(
        default=None,
        alias="claimedSpeaker",
        description="Account holder or speaker identity claimed by the caller",
    )
    historical_flags: list[str] = Field(
        default_factory=list,
        alias="historicalFlags",
        description="Prior risk flags (e.g. SIM_SWAP, HIGH_VELOCITY)",
    )
    workflow_type: str = Field(
        default="financial",
        alias="workflowType",
        description="High-level workflow category: financial | telecommunications | government",
    )
    language: str | None = Field(
        default=None,
        alias="language",
        description="Explicit language code if known or operator-selected (e.g. hi, en-IN)",
    )
    code_switching: bool = Field(
        default=False,
        alias="codeSwitching",
        description="Flag indicating code-switching observed in call stream",
    )
