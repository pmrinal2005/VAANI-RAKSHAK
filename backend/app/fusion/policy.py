# ==============================================================================
# VAANI-RAKSHAK — Enterprise Policy & Interceptor Engine
# Evaluates multi-modal risk scores, speaker status, and transaction stakes
# to determine banking interception actions: ALLOW, CHALLENGE, HOLD, BLOCK.
# ==============================================================================

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Decision, RiskBand
from app.schemas.context import CallContext
from app.schemas.detection import FusionOutput


class PolicyDecision(BaseModel):
    """The authoritative interceptor decision for a call session or transaction."""

    model_config = ConfigDict(extra="ignore")

    decision: Decision
    action_code: str
    requires_out_of_band: bool
    interceptor_rule: str
    rationale: str
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class EnterprisePolicyEngine:
    """
    Applies zero-trust banking interceptor policies to voice risk assessments.
    """

    def evaluate(
        self, fusion_output: FusionOutput, context: CallContext
    ) -> PolicyDecision:
        band = fusion_output.band
        score = fusion_output.risk_score
        speaker_mismatch = (
            fusion_output.speaker_check.mismatch
            if fusion_output.speaker_check
            else False
        )
        is_high_value = context.transaction_value_inr >= 200_000
        is_financial_transfer = bool(
            re.search(
                r"transfer|wire|recovery|approval|otp|kyc|beneficiary",
                context.transaction_type,
                re.I,
            )
        )

        # ----------------------------------------------------------------------
        # Rule 1: Speaker Mismatch Override (Zero-Trust Identity)
        # ----------------------------------------------------------------------
        if speaker_mismatch:
            if band == RiskBand.CRITICAL and (is_financial_transfer or is_high_value):
                return PolicyDecision(
                    decision=Decision.BLOCK,
                    action_code="INTERCEPT_BLOCK_SPEAKER_MISMATCH_CRITICAL",
                    requires_out_of_band=True,
                    interceptor_rule="RULE_SEC_01_SPEAKER_MISMATCH_CRITICAL",
                    rationale=(
                        "Immediate block: Claimed speaker voiceprint mismatch accompanied by "
                        "critical clone risk on sensitive transaction."
                    ),
                    metadata={"speaker_mismatch": True, "risk_score": score},
                )
            return PolicyDecision(
                decision=Decision.CHALLENGE,
                action_code="INTERCEPT_CHALLENGE_SPEAKER_MISMATCH",
                requires_out_of_band=True,
                interceptor_rule="RULE_SEC_02_SPEAKER_MISMATCH_STEPUP",
                rationale=(
                    "Step-up out-of-band challenge required: Spoken voiceprint does not match "
                    "enrolled customer biometric baseline."
                ),
                metadata={"speaker_mismatch": True, "risk_score": score},
            )

        # ----------------------------------------------------------------------
        # Rule 2: Critical Risk Band (Score >= 85)
        # ----------------------------------------------------------------------
        if band == RiskBand.CRITICAL or score >= 85:
            if is_financial_transfer or is_high_value:
                return PolicyDecision(
                    decision=Decision.BLOCK,
                    action_code="INTERCEPT_BLOCK_CRITICAL_FRAUD",
                    requires_out_of_band=True,
                    interceptor_rule="RULE_RISK_01_CRITICAL_FINANCIAL_BLOCK",
                    rationale=(
                        "Call intercepted and blocked: Synthetic clone detected "
                        "with high confidence during high-value or funds-transfer operation."
                    ),
                    metadata={"band": band.value, "risk_score": score},
                )
            return PolicyDecision(
                decision=Decision.HOLD,
                action_code="INTERCEPT_HOLD_CRITICAL_REVIEW",
                requires_out_of_band=True,
                interceptor_rule="RULE_RISK_02_CRITICAL_HOLD",
                rationale=(
                    "Call routed to fraud supervisor queue: Deepfake voice indicators detected. "
                    "Awaiting manual investigator verification."
                ),
                metadata={"band": band.value, "risk_score": score},
            )

        # ----------------------------------------------------------------------
        # Rule 3: High Risk Band (Score 65-84)
        # ----------------------------------------------------------------------
        if band == RiskBand.HIGH or score >= 65:
            return PolicyDecision(
                decision=Decision.HOLD,
                action_code="INTERCEPT_HOLD_SUPERVISOR",
                requires_out_of_band=True,
                interceptor_rule="RULE_RISK_03_HIGH_RISK_SUPERVISOR_HOLD",
                rationale=(
                    "Transaction placed on hold: Multiple acoustic and prosodic indicators suggest "
                    "voice synthesis or playback."
                ),
                metadata={"band": band.value, "risk_score": score},
            )

        # ----------------------------------------------------------------------
        # Rule 4: Elevated Risk Band (Score 40-64)
        # ----------------------------------------------------------------------
        if band == RiskBand.ELEVATED or score >= 40:
            if is_high_value or is_financial_transfer:
                return PolicyDecision(
                    decision=Decision.CHALLENGE,
                    action_code="INTERCEPT_CHALLENGE_STEPUP_OTP",
                    requires_out_of_band=True,
                    interceptor_rule="RULE_RISK_04_ELEVATED_STAKES_CHALLENGE",
                    rationale=(
                        "Step-up authentication required: Elevated synthetic voice risk detected "
                        "on financial transaction."
                    ),
                    metadata={"band": band.value, "risk_score": score},
                )
            return PolicyDecision(
                decision=Decision.ALLOW,
                action_code="INTERCEPT_ALLOW_MONITORED",
                requires_out_of_band=False,
                interceptor_rule="RULE_RISK_05_ELEVATED_LOW_STAKES_ALLOW",
                rationale=(
                    "Call allowed under enhanced telemetry monitoring: Moderate risk detected on "
                    "low-stakes inquiry."
                ),
                metadata={"band": band.value, "risk_score": score},
            )

        # ----------------------------------------------------------------------
        # Rule 5: Low Risk Band (Score < 40)
        # ----------------------------------------------------------------------
        if context.ani_reputation < 0.30 or not context.known_contact:
            return PolicyDecision(
                decision=Decision.ALLOW,
                action_code="INTERCEPT_ALLOW_UNVERIFIED_CALLER",
                requires_out_of_band=False,
                interceptor_rule="RULE_RISK_06_LOW_RISK_UNKNOWN_CALLER",
                rationale=(
                    "Authentic voice characteristics confirmed from unverified caller number."
                ),
                metadata={"band": band.value, "risk_score": score},
            )

        return PolicyDecision(
            decision=Decision.ALLOW,
            action_code="INTERCEPT_ALLOW_AUTHENTIC",
            requires_out_of_band=False,
            interceptor_rule="RULE_RISK_07_STANDARD_ALLOW",
            rationale="Authentic biological voice confirmed across all acoustic tiers.",
            metadata={"band": band.value, "risk_score": score},
        )
