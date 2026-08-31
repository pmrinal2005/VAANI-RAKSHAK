# ==============================================================================
# VAANI-RAKSHAK — Indic Multilingual Language Router Mock Adapter
# Routes incoming audio to language-specific LoRA adapters across 12 Indic languages.
# Clearly marked as MOCK implementation.
# ==============================================================================

from __future__ import annotations

from app.domain.enums import LanguageRoutingSource, MockScenario
from app.schemas.detection import (
    DetectionRequest,
    LanguageDistributionItem,
    LanguageRoutingResult,
)

INDIC_LANGUAGES = [
    {"language": "Hindi", "code": "hi", "adapter": "lora-hi-v2"},
    {"language": "Bengali", "code": "bn", "adapter": "lora-bn-v1"},
    {"language": "Telugu", "code": "te", "adapter": "lora-te-v1"},
    {"language": "Marathi", "code": "mr", "adapter": "lora-mr-v1"},
    {"language": "Tamil", "code": "ta", "adapter": "lora-ta-v2"},
    {"language": "Gujarati", "code": "gu", "adapter": "lora-gu-v1"},
    {"language": "Kannada", "code": "kn", "adapter": "lora-kn-v1"},
    {"language": "Malayalam", "code": "ml", "adapter": "lora-ml-v1"},
    {"language": "Punjabi", "code": "pa", "adapter": "lora-pa-v1"},
    {"language": "Odia", "code": "or", "adapter": "lora-or-v1"},
    {"language": "Urdu", "code": "ur", "adapter": "lora-ur-v1"},
    {"language": "English (Indian)", "code": "en-IN", "adapter": "lora-enIN-v2"},
]


class MockLanguageRouter:
    """
    Mock implementation of LanguageRouter protocol.
    Provides honest routing defaults and Indic LoRA adapter allocation.
    """

    def __init__(self, default_scenario: MockScenario = MockScenario.LOW_RISK) -> None:
        self.default_scenario = default_scenario

    async def route(self, request: DetectionRequest) -> LanguageRoutingResult:
        code_requested = request.language_override or request.context.language

        # User / operator explicit selection
        if code_requested and code_requested not in ("auto", "und"):
            meta = next((item for item in INDIC_LANGUAGES if item["code"] == code_requested), None)
            if meta:
                return LanguageRoutingResult(
                    detected=meta["language"],
                    code=meta["code"],
                    confidence=1.0,
                    distribution=[
                        LanguageDistributionItem(
                            language=meta["language"], code=meta["code"], prob=1.0
                        )
                    ],
                    adapter=meta["adapter"],
                    code_switching=False,
                    source=LanguageRoutingSource.USER_SELECTED,
                    note=(
                        f"Operator-selected language ({meta['language']}) -> "
                        f"routed to {meta['adapter']}."
                    ),
                )

        # Code-switching simulation
        if request.context.code_switching:
            return LanguageRoutingResult(
                detected="Hindi / English (Indian)",
                code="hi+en-IN",
                confidence=0.88,
                distribution=[
                    LanguageDistributionItem(language="Hindi", code="hi", prob=0.55),
                    LanguageDistributionItem(language="English (Indian)", code="en-IN", prob=0.35),
                    LanguageDistributionItem(language="Marathi", code="mr", prob=0.10),
                ],
                adapter="lora-hi-v2 ⊕ lora-enIN-v2",
                code_switching=True,
                source=LanguageRoutingSource.ONNX_LID,
                note=(
                    "Code-switching detected (Hindi / English-IN) — "
                    "soft ensemble of dual LoRA adapters engaged."
                ),
            )

        # Honest fallback: DSP cannot reliably guess language without neural IndicLID
        return LanguageRoutingResult(
            detected="Undetermined",
            code="und",
            confidence=0.0,
            distribution=[LanguageDistributionItem(language="Undetermined", code="und", prob=1.0)],
            adapter="language-agnostic",
            code_switching=False,
            source=LanguageRoutingSource.UNDETERMINED,
            note=(
                "Language undetermined. Client-side DSP cannot identify spoken language without "
                "neural IndicLID. Using language-agnostic SSL representation."
            ),
        )
