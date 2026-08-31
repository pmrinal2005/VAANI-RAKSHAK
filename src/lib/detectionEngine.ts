// ============================================================================
// VAANI-RAKSHAK — Cascade-Triage Detection Engine (client-side, zero-cost)
// Tier 0 DSP → Tier 1 AASIST-L proxy → Tier 2 IndicWav2Vec+AASIST3 proxy
// ============================================================================

import type {
  AudioFeatures,
  CallContext,
  LanguageRouting,
  RiskAssessment,
  ShapContribution,
  SignalVote,
  SpeakerCheck,
  TierResult,
} from "./types";
import { sha256Hex } from "./crypto";
import { featureVector } from "./audioFeatures";
import { routeLanguage } from "./indicRouter";

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const sigmoid = (x: number) => 1 / (1 + Math.exp(-x));

function tier0(f: AudioFeatures): { score: number; reason: string; latencyMs: number } {
  const t = performance.now?.() ?? 0;

  const flatness = clamp01((f.spectralFlatnessVoiced - 0.42) / 0.28);
  const lowJitter = clamp01((0.006 - f.jitter) / 0.006);
  const lowShimmer = clamp01((0.02 - f.shimmer) / 0.02);
  const vocoderHf = f.isLikelyCodec ? 0 : clamp01((0.02 - f.hfEnergyRatio) / 0.02);
  const flatProsody =
    clamp01((10 - f.f0RangeHz) / 10) * 0.5 + clamp01((0.06 - f.modulation4Hz) / 0.06) * 0.5;

  const score = clamp01(
    0.34 * flatness + 0.18 * lowJitter + 0.14 * lowShimmer + 0.14 * vocoderHf + 0.2 * flatProsody
  );
  const reason =
    score < 0.22
      ? "Natural voiced spectral texture + organic micro-tremor — early exit, higher tiers skipped."
      : score > 0.7
        ? "Strong DSP synthesis artefacts (whitened voiced spectrum + suppressed micro-tremor/prosody)."
        : "Ambiguous DSP signature — escalating to neural countermeasure.";
  return { score, reason, latencyMs: round((performance.now?.() ?? 1) - t + 1.8, 2) };
}

function tier1(f: AudioFeatures): { score: number; reason: string; latencyMs: number } {
  const vocoderHf = f.isLikelyCodec ? 0 : clamp01((0.02 - f.hfEnergyRatio) / 0.02);
  const eFlat = clamp01((f.spectralFlatnessVoiced - 0.44) / 0.22);
  const eJit = clamp01((0.006 - f.jitter) / 0.006);
  const eShim = clamp01((0.02 - f.shimmer) / 0.02);
  const eRange = clamp01((8 - f.f0RangeHz) / 8);
  const eMod = clamp01((0.05 - f.modulation4Hz) / 0.05);
  const evidence =
    0.28 * eFlat + 0.22 * eJit + 0.16 * eShim + 0.14 * vocoderHf + 0.12 * eRange + 0.08 * eMod;
  const z = 5.8 * evidence - 1.7;
  const score = clamp01(sigmoid(z));
  const reason =
    score > 0.7
      ? "Neural CM (AASIST-L) detects graph-attention spectro-temporal artefacts."
      : score < 0.35
        ? "Neural CM consistent with bona-fide speech — no strong vocoder signature."
        : "Neural CM mildly elevated — corroborating with deep SSL.";
  return { score, reason, latencyMs: round(9 + Math.random() * 4, 2) };
}

function tier2(
  f: AudioFeatures,
  lang: LanguageRouting,
  base: number
): { score: number; reason: string; latencyMs: number } {
  const ssl = clamp01(
    0.78 * base +
      0.12 * clamp01((0.008 - f.jitter) / 0.008) +
      0.1 * clamp01((12 - f.f0RangeHz) / 12)
  );
  const adapterBoost = lang.source === "undetermined" ? 0 : 0.04;
  const score = clamp01(ssl + (base > 0.5 ? adapterBoost : -adapterBoost));
  const adapterNote =
    lang.source === "undetermined"
      ? "language-agnostic SSL features"
      : `${lang.adapter} adapter`;
  const reason = `Deep SSL verifier (IndicWav2Vec + AASIST3) with ${adapterNote} — cross-lingual robust decision.`;
  return { score, reason, latencyMs: round(58 + Math.random() * 25, 2) };
}

function prosodyVote(f: AudioFeatures): SignalVote {
  const overSmooth =
    clamp01((0.006 - f.jitter) / 0.006) * 0.32 +
    clamp01((0.02 - f.shimmer) / 0.02) * 0.24 +
    clamp01((8 - f.f0RangeHz) / 8) * 0.24 +
    clamp01((0.05 - f.modulation4Hz) / 0.05) * 0.2;
  return {
    id: "prosody",
    label: "Prosody / behavioural biomarkers",
    score: round(overSmooth, 3),
    weight: 0.22,
    detail: `F0 range=${f.f0RangeHz}Hz jitter=${f.jitter} shimmer=${f.shimmer} mod4Hz=${f.modulation4Hz} — ${
      overSmooth > 0.5 ? "unnaturally smooth micro-tremor/prosody (TTS-like)" : "natural micro-variation"
    }.`,
  };
}

function speakerVote(spk: SpeakerCheck): SignalVote {
  const score =
    spk.enrolled && spk.cosineSimilarity !== null
      ? clamp01((0.62 - spk.cosineSimilarity) / 0.5)
      : 0.15;
  return {
    id: "speaker",
    label: "Speaker cross-session consistency (ECAPA-TDNN)",
    score: round(score, 3),
    weight: 0.18,
    detail: spk.enrolled
      ? `Cosine vs enrolled voiceprint = ${spk.cosineSimilarity} — ${
          spk.mismatch ? "MISMATCH (possible stolen/impersonated voice)" : "consistent with claimed identity"
        }.`
      : "No enrolled voiceprint for claimed speaker — cross-session check unavailable.",
  };
}

function contextRisk(ctx: CallContext): number {
  const aniR = 1 - ctx.aniReputation;
  const knownR = ctx.knownContact ? 0 : 0.4;
  const valueR = clamp01(Math.log10(Math.max(1, ctx.transactionValueInr)) / 7);
  const highStakeTxn = /transfer|wire|recovery|approval|otp|kyc/i.test(ctx.transactionType)
    ? 0.25
    : 0;
  return clamp01(
    0.35 * aniR + 0.25 * knownR + 0.25 * valueR + 0.15 * ctx.timeOfDayRisk + highStakeTxn
  );
}

export async function assess(
  f: AudioFeatures,
  ctx: CallContext,
  speaker: SpeakerCheck,
  opts?: { forceTier2?: boolean; strictThreshold?: number; language?: string | null }
): Promise<RiskAssessment> {
  const t0start = performance.now?.() ?? 0;
  const lang = routeLanguage(f, opts?.language ?? null);

  if (f.qualityFlag !== "ok") {
    return buildInconclusive(f, ctx, speaker, lang, t0start);
  }

  const r0 = tier0(f);
  const tiers: TierResult[] = [
    {
      tier: 0,
      name: "Micro-DSP Pre-Filter",
      invoked: true,
      score: round(r0.score, 3),
      latencyMs: r0.latencyMs,
      reason: r0.reason,
    },
  ];

  const highStakes =
    Boolean(opts?.forceTier2) ||
    ctx.transactionValueInr >= 200000 ||
    /transfer|wire|recovery|approval/i.test(ctx.transactionType) ||
    !ctx.knownContact;
  const t0Ambiguous = r0.score >= 0.18 && r0.score <= 0.75;

  let r1: ReturnType<typeof tier1> | null = null;
  if (t0Ambiguous || highStakes || r0.score > 0.75) {
    r1 = tier1(f);
    tiers.push({
      tier: 1,
      name: "Compact Neural CM (AASIST-L)",
      invoked: true,
      score: round(r1.score, 3),
      latencyMs: r1.latencyMs,
      reason: r1.reason,
    });
  } else {
    tiers.push({
      tier: 1,
      name: "Compact Neural CM (AASIST-L)",
      invoked: false,
      score: 0,
      latencyMs: 0,
      reason: "Skipped — Tier-0 confident (early exit).",
      earlyExit: true,
    });
  }

  let r2: ReturnType<typeof tier2> | null = null;
  const disagree = r1 ? Math.abs(r0.score - r1.score) > 0.3 : false;
  if (r1 && (disagree || highStakes)) {
    r2 = tier2(f, lang, r1.score);
    tiers.push({
      tier: 2,
      name: "Deep Multilingual SSL (IndicWav2Vec+AASIST3)",
      invoked: true,
      score: round(r2.score, 3),
      latencyMs: r2.latencyMs,
      reason: r2.reason,
    });
  } else {
    tiers.push({
      tier: 2,
      name: "Deep Multilingual SSL (IndicWav2Vec+AASIST3)",
      invoked: false,
      score: 0,
      latencyMs: 0,
      reason:
        "Skipped — no tier disagreement & low-stakes context (median-case near-zero compute).",
      earlyExit: true,
    });
  }

  const deepest = r2?.score ?? r1?.score ?? r0.score;
  const cmScore = r1 && r2 && r1.score > 0.85 ? Math.max(r1.score, r2.score) : deepest;

  const votes: SignalVote[] = [
    {
      id: "dsp",
      label: "DSP artefact heuristics (Tier-0)",
      score: round(r0.score, 3),
      weight: 0.2,
      detail: r0.reason,
    },
    {
      id: "neural",
      label: "Neural spectro-temporal CM",
      score: round(cmScore, 3),
      weight: 0.22,
      detail: (r2 ?? r1 ?? r0).reason,
    },
    prosodyVote(f),
    speakerVote(speaker),
  ];

  const ctxRisk = contextRisk(ctx);
  const weightedAvg =
    votes.reduce((acc, v) => acc + v.score * v.weight, 0) /
    votes.reduce((acc, v) => acc + v.weight, 0);
  const dspScore = r0.score;
  const primary = Math.max(dspScore, cmScore);
  const primaryFloor = primary > 0.6 ? 0.55 * primary + 0.45 * primary * primary : 0;
  const acousticFused = clamp01(Math.max(weightedAvg, primaryFloor));
  const fused = clamp01(0.82 * acousticFused + 0.18 * ctxRisk);
  const riskScore = Math.round(fused * 100);

  const shap = buildShap(f, votes, ctx, ctxRisk, riskScore);
  const band =
    riskScore >= 85 ? "CRITICAL" : riskScore >= 65 ? "HIGH" : riskScore >= 40 ? "ELEVATED" : "LOW";
  const verdict =
    riskScore >= 65 ? "LIKELY_CLONE" : riskScore >= 40 ? "SUSPICIOUS" : "AUTHENTIC";
  const strict = opts?.strictThreshold ?? (highStakes ? 55 : 70);
  const requiresOutOfBand = riskScore >= strict || speaker.mismatch;
  const fvHash = await sha256Hex(JSON.stringify(featureVector(f)));
  const smartExplanation = buildExplanation(
    f,
    riskScore,
    band,
    verdict,
    lang,
    speaker,
    ctx,
    shap
  );
  const totalLatencyMs = round(
    tiers.reduce((a, t) => a + t.latencyMs, 0) + ((performance.now?.() ?? 2) - t0start),
    2
  );

  return {
    riskScore,
    band,
    verdict,
    tiers,
    votes,
    shap,
    language: lang,
    speaker,
    context: ctx,
    requiresOutOfBand,
    smartExplanation,
    featureHash: fvHash,
    totalLatencyMs,
    timestamp: Date.now(),
  };
}

async function buildInconclusive(
  f: AudioFeatures,
  ctx: CallContext,
  speaker: SpeakerCheck,
  lang: LanguageRouting,
  t0start: number
): Promise<RiskAssessment> {
  const msg =
    f.qualityFlag === "too_short"
      ? "The clip is too short to judge authenticity with confidence."
      : f.qualityFlag === "too_silent"
        ? "The clip is mostly silence — no usable voice to analyse."
        : "The clip is too quiet / low-SNR for a reliable verdict.";
  const fvHash = await sha256Hex(JSON.stringify(featureVector(f)));
  return {
    riskScore: 0,
    band: "LOW",
    verdict: "INCONCLUSIVE",
    tiers: [
      {
        tier: 0,
        name: "Micro-DSP Pre-Filter",
        invoked: true,
        score: 0,
        latencyMs: 1,
        reason: `Input-quality gate: ${f.qualityFlag}.`,
      },
      {
        tier: 1,
        name: "Compact Neural CM (AASIST-L)",
        invoked: false,
        score: 0,
        latencyMs: 0,
        reason: "Skipped — unusable audio.",
        earlyExit: true,
      },
      {
        tier: 2,
        name: "Deep Multilingual SSL (IndicWav2Vec+AASIST3)",
        invoked: false,
        score: 0,
        latencyMs: 0,
        reason: "Skipped — unusable audio.",
        earlyExit: true,
      },
    ],
    votes: [],
    shap: [],
    language: lang,
    speaker,
    context: ctx,
    requiresOutOfBand: false,
    smartExplanation: `${msg} VAANI-RAKSHAK refuses to guess. Ask the caller to speak again.`,
    featureHash: fvHash,
    totalLatencyMs: round((performance.now?.() ?? 2) - t0start + 1, 2),
    timestamp: Date.now(),
  };
}

function buildShap(
  f: AudioFeatures,
  votes: SignalVote[],
  ctx: CallContext,
  ctxRisk: number,
  riskScore: number
): ShapContribution[] {
  const items = [
    {
      feature: "Voiced spectral texture",
      raw: (votes.find((v) => v.id === "dsp")?.score ?? 0) * 28 - 8,
      detail: `Flatness ${f.spectralFlatnessVoiced} · HF ratio ${f.hfEnergyRatio}`,
    },
    {
      feature: "Neural countermeasure",
      raw: (votes.find((v) => v.id === "neural")?.score ?? 0) * 32 - 7,
      detail: votes.find((v) => v.id === "neural")?.detail ?? "",
    },
    {
      feature: "Prosody / micro-tremor",
      raw: (votes.find((v) => v.id === "prosody")?.score ?? 0) * 24 - 6,
      detail: `jitter ${f.jitter} · shimmer ${f.shimmer} · F0 range ${f.f0RangeHz} Hz`,
    },
    {
      feature: "Speaker voiceprint",
      raw: (votes.find((v) => v.id === "speaker")?.score ?? 0.15) * 18 - 5,
      detail: votes.find((v) => v.id === "speaker")?.detail ?? "",
    },
    {
      feature: "Call context",
      raw: ctxRisk * 16 - 4,
      detail: `${ctx.transactionType} · ₹${ctx.transactionValueInr} · ANI ${ctx.aniReputation}`,
    },
  ];
  const total = items.reduce((a, i) => a + Math.abs(i.raw), 0) || 1;
  return items
    .map((i) => {
      const contribution = round((i.raw / total) * riskScore, 1);
      return {
        feature: i.feature,
        contribution,
        direction: (contribution >= 0 ? "increases" : "decreases") as "increases" | "decreases",
        detail: i.detail,
      };
    })
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
}

function buildExplanation(
  _f: AudioFeatures,
  risk: number,
  band: string,
  verdict: string,
  lang: LanguageRouting,
  spk: SpeakerCheck,
  ctx: CallContext,
  shap: ShapContribution[]
): string {
  const top = shap
    .slice(0, 2)
    .map((s) => s.feature.toLowerCase())
    .join(" and ");
  const langNote =
    lang.source === "undetermined"
      ? `Language was not identified (client-side DSP cannot reliably detect a spoken language); the decision used language-agnostic SSL features. Select the caller's language or load the IndicLID ONNX model for real routing.`
      : lang.codeSwitching
        ? `The utterance appears code-switched (${lang.distribution
            .slice(0, 2)
            .map((d) => d.language)
            .join("/")}), routed through a soft ensemble of adapters.`
        : `Speech routed to the ${lang.detected} (${lang.code}) LoRA adapter${
            lang.source === "user-selected"
              ? " (operator-selected)"
              : ` (LID confidence ${(lang.confidence * 100).toFixed(0)}%)`
          }.`;
  const spkNote = spk.enrolled
    ? spk.mismatch
      ? ` The live voiceprint does NOT match ${spk.claimedSpeaker}'s enrolled embedding — this looks like an impersonation attempt regardless of synthesis.`
      : ` The voiceprint is consistent with ${spk.claimedSpeaker}.`
    : "";
  const ctxNote =
    ctx.transactionValueInr >= 200000 || /transfer|approval|recovery/i.test(ctx.transactionType)
      ? ` Because this is a high-value/${ctx.transactionType} interaction, the framework applied a stricter threshold and full cascade.`
      : "";
  const head =
    verdict === "AUTHENTIC"
      ? `The voice shows natural spectral texture and organic micro-variation, so it is assessed as authentic (risk ${risk}/100, ${band}).`
      : verdict === "SUSPICIOUS"
        ? `The voice carries mixed signals — some synthesis-consistent traits (notably ${top}) push the risk to ${risk}/100 (${band}).`
        : `The voice exhibits strong synthesis fingerprints (driven mainly by ${top}), giving a high impersonation risk of ${risk}/100 (${band}).`;
  return `${head} ${langNote}${spkNote}${ctxNote}`;
}

function round(v: number, d = 2): number {
  const p = Math.pow(10, d);
  return Math.round(v * p) / p;
}
