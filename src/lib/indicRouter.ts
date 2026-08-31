// ============================================================================
// VAANI-RAKSHAK — Indic Multilingual LID + LoRA Adapter Router
// Honest default is "undetermined" — DSP cannot identify a spoken language.
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

type OnnxLidFn = (f: AudioFeatures) => { code: string; prob: number }[] | null;
let onnxLid: OnnxLidFn | null = null;
export function setOnnxLid(fn: OnnxLidFn | null) {
  onnxLid = fn;
}

const UNDETERMINED_DIST = [{ language: "Undetermined", code: "und", prob: 1 }];

export function routeLanguage(
  f: AudioFeatures,
  manual?: string | null
): LanguageRouting {
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
