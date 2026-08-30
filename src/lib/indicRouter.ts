// ============================================================================
// VAANI-RAKSHAK — Indic Multilingual LID + LoRA Adapter Router
//
// Simulates the AI4Bharat IndicLID front-end that routes each utterance to the
// correct language/dialect LoRA adapter stacked on a single shared IndicWav2Vec
// backbone. Instead of 22 heavy models, only a few-MB adapter is swapped in.
// Code-switching (Hindi-English etc.) yields a *distribution*, triggering a soft
// ensemble of the top-2 adapters. The deterministic pseudo-LID here is a
// deployable stand-in; the Colab notebook wires the real IndicLID + adapters.
// ============================================================================

import type { AudioFeatures, LanguageRouting } from "./types";

export const INDIC_LANGUAGES = [
  { language: "Hindi", code: "hi", adapter: "lora-hi-v2" },
  { language: "Bengali", code: "bn", adapter: "lora-bn-v1" },
  { language: "Telugu", code: "te", adapter: "lora-te-v1" },
  { language: "Marathi", code: "mr", adapter: "lora-mr-v1" },
  { language: "Tamil", code: "ta", adapter: "lora-ta-v2" },
  { language: "Gujarati", code: "gu", adapter: "lora-gu-v1" },
  { language: "Kannada", code: "kn", adapter: "lora-kn-v1" },
  { language: "Malayalam", code: "ml", adapter: "lora-ml-v1" },
  { language: "Punjabi", code: "pa", adapter: "lora-pa-v1" },
  { language: "Odia", code: "or", adapter: "lora-or-v1" },
  { language: "Urdu", code: "ur", adapter: "lora-ur-v1" },
  { language: "English (Indian)", code: "en-IN", adapter: "lora-enIN-v2" },
] as const;

/** Deterministic pseudo-LID driven by spectral/prosodic features + MFCC hash. */
export function routeLanguage(f: AudioFeatures): LanguageRouting {
  // Derive a stable seed from acoustic descriptors so the same clip -> same LID.
  const seed =
    Math.abs(
      Math.sin(
        f.spectralCentroidHz * 0.0007 +
          f.f0MeanHz * 0.013 +
          (f.mfcc[1] ?? 0) * 1.7 +
          (f.mfcc[3] ?? 0) * 0.9 +
          f.zeroCrossingRate * 31.0
      )
    ) % 1;

  // Build a softmax-ish distribution over a rotating subset (weighted to Hindi/en-IN).
  const priors = INDIC_LANGUAGES.map((l, i) => {
    const bump = l.code === "hi" ? 1.5 : l.code === "en-IN" ? 1.3 : 1.0;
    const s = Math.abs(Math.sin(seed * 12.9898 + i * 4.1)) * bump;
    return { ...l, raw: s };
  });
  const sum = priors.reduce((a, p) => a + p.raw, 0);
  const dist = priors
    .map((p) => ({ language: p.language, code: p.code, prob: p.raw / sum }))
    .sort((a, b) => b.prob - a.prob);

  const top = dist[0];
  const second = dist[1];
  const confidence = top.prob;
  const codeSwitching = top.prob - second.prob < 0.10; // ambiguous -> soft ensemble

  const chosen = INDIC_LANGUAGES.find((l) => l.code === top.code)!;
  const adapter = codeSwitching
    ? `${chosen.adapter} ⊕ ${INDIC_LANGUAGES.find((l) => l.code === second.code)!.adapter}`
    : chosen.adapter;

  return {
    detected: top.language,
    code: top.code,
    confidence: round(confidence, 3),
    distribution: dist.slice(0, 5).map((d) => ({ ...d, prob: round(d.prob, 3) })),
    adapter,
    codeSwitching,
  };
}

function round(v: number, d: number): number {
  const p = Math.pow(10, d);
  return Math.round(v * p) / p;
}
