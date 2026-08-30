// ============================================================================
// VAANI-RAKSHAK — Indic Multilingual LID + LoRA Adapter Router
//
// ── BUG-FIX (wrong language every time) ─────────────────────────────────────
// The previous version "detected" a language from a Math.sin() hash of spectral
// features. That is NOT language identification — spoken-language ID requires a
// trained acoustic/phonotactic model (e.g. AI4Bharat IndicLID). The old hash
// produced a different, essentially random label per clip (biased to Hindi),
// which is exactly the reported bug.
//
// The honest, correct behaviour for a pure client-side DSP demo:
//   1. DEFAULT → `undetermined`: we do NOT fabricate a language. The UI shows a
//      clear note that real LID requires the ONNX model exported from Colab.
//   2. USER-SELECTED → if the operator picks the caller's (registered) language,
//      we route to that language's LoRA adapter with confidence 1.0. This is
//      realistic: banks/telecoms usually know the customer's registered
//      language, and it removes the gu! from the demo.
//   3. ONNX-LID → if a real IndicLID ONNX session is wired in (see
//      `setOnnxLid`), its probability distribution is used directly.
// This keeps the framework's cross-lingual adapter story intact while never
// showing a confidently-wrong language.
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

export type IndicCode = (typeof INDIC_LANGUAGES)[number]["code"];

/** Optional real LID hook. When a trained IndicLID ONNX model is loaded, set a
 *  callback here (from the client) that maps features/waveform → distribution. */
type OnnxLidFn = (
  f: AudioFeatures
) => { code: string; prob: number }[] | null;
let onnxLid: OnnxLidFn | null = null;
export function setOnnxLid(fn: OnnxLidFn | null) {
  onnxLid = fn;
}

const UNDETERMINED_DIST = [
  { language: "Undetermined", code: "und", prob: 1 },
];

/**
 * Route an utterance to a language adapter.
 * @param f       extracted audio features
 * @param manual  optional operator-selected language code (from the UI)
 */
export function routeLanguage(f: AudioFeatures, manual?: string | null): LanguageRouting {
  // 1) Operator-selected language (honest, realistic for KYC-verified callers)
  if (manual && manual !== "auto" && manual !== "und") {
    const chosen = INDIC_LANGUAGES.find((l) => l.code === manual);
    if (chosen) {
      return {
        detected: chosen.language,
        code: chosen.code,
        confidence: 1,
        distribution: [{ language: chosen.language, code: chosen.code, prob: 1 }],
        adapter: chosen.adapter,
        codeSwitching: false,
        source: "user-selected",
        note: `Operator-selected language → routed to ${chosen.adapter}. (Registered-language routing; no acoustic guessing.)`,
      };
    }
  }

  // 2) Real ONNX IndicLID model, if wired in
  if (onnxLid) {
    const dist = onnxLid(f);
    if (dist && dist.length) {
      const enriched = dist
        .map((d) => {
          const meta = INDIC_LANGUAGES.find((l) => l.code === d.code);
          return { language: meta?.language ?? d.code, code: d.code, prob: d.prob };
        })
        .sort((a, b) => b.prob - a.prob);
      const top = enriched[0];
      const second = enriched[1] ?? { prob: 0, code: "", language: "" };
      const codeSwitching = top.prob - second.prob < 0.1;
      const chosen = INDIC_LANGUAGES.find((l) => l.code === top.code);
      const adapter = chosen
        ? codeSwitching && second.code
          ? `${chosen.adapter} ⊕ ${INDIC_LANGUAGES.find((l) => l.code === second.code)?.adapter ?? ""}`
          : chosen.adapter
        : "lora-generic";
      return {
        detected: top.language,
        code: top.code,
        confidence: round(top.prob, 3),
        distribution: enriched.slice(0, 5).map((d) => ({ ...d, prob: round(d.prob, 3) })),
        adapter,
        codeSwitching,
        source: "onnx-lid",
        note: "Language identified by the trained IndicLID ONNX model (real LID).",
      };
    }
  }

  // 3) Honest default — DO NOT fabricate a language from DSP alone.
  return {
    detected: "Undetermined",
    code: "und",
    confidence: 0,
    distribution: UNDETERMINED_DIST,
    adapter: "language-agnostic",
    codeSwitching: false,
    source: "undetermined",
    note:
      "Language not determined. Client-side DSP cannot identify a spoken language reliably — " +
      "select the caller's language, or load the trained IndicLID ONNX model (from the Colab notebook) for real LID. " +
      "Detection uses language-agnostic SSL features in the meantime.",
  };
}

function round(v: number, d: number): number {
  const p = Math.pow(10, d);
  return Math.round(v * p) / p;
}
