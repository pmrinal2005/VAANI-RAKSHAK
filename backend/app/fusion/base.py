# ==============================================================================
# VAANI-RAKSHAK — Multi-Modal Fusion & Explainability Protocol Interfaces
# Combines independent acoustic tiers, prosodic biomarkers, speaker verification,
# and contextual risk into an actionable risk assessment and plain-language explanation.
# ==============================================================================

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.detection import FusionInput, FusionOutput, ShapContribution, SignalVote


@runtime_checkable
class FusionEngine(Protocol):
    """
    Interface for fusing multiple detection tier outputs, behavioural biomarkers,
    speaker verification consistency, and contextual risk into a unified risk assessment.
    """

    async def fuse(self, fusion_input: FusionInput) -> FusionOutput:
        """Execute multi-modal evidence fusion and return the final risk decision."""
        ...


@runtime_checkable
class ExplanationEngine(Protocol):
    """
    Interface for generating SHAP-style feature attribution breakdowns.
    Provides plain-language diagnostic explanations without obfuscating model uncertainty.
    """

    async def explain(
        self,
        fusion_input: FusionInput,
        risk_score: int,
        votes: list[SignalVote],
    ) -> list[ShapContribution]:
        """Compute feature contributions and diagnostic attribution details."""
        ...
