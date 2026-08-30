// ============================================================================
// VAANI-RAKSHAK — Core type definitions
// AI-Powered Real-Time Voice Cloning Detection Framework
// ============================================================================

/** Acoustic + behavioural features extracted from an audio chunk. */
export interface AudioFeatures {
  durationSec: number;
  sampleRate: number;
  // Energy / dynamics
  rmsDb: number;
  silenceRatio: number;
  crestFactor: number; // peak / rms  (naturalness of dynamics)
  // Spectral (Tier-0 DSP)
  spectralCentroidHz: number;
  spectralSpreadHz: number;
  spectralFlatness: number; // synthetic voices tend to be flatter/whiter
  spectralRolloffHz: number;
  zeroCrossingRate: number;
  // Phase / vocoder artefacts
  phaseDiscontinuity: number; // proxy for neural-vocoder phase artefacts
  hfEnergyRatio: number; // energy above 6 kHz (codec/vocoder cutoff clue)
  // Cepstral (CQCC/LFCC-like proxy)
  cqccVar: number;
  lfccVar: number;
  // Prosody / behavioural biomarkers (Praat/openSMILE-style proxy)
  f0MeanHz: number;
  f0Std: number; // over-smooth TTS -> low pitch variability
  f0RangeHz: number; // voiced-frame p95-p5 pitch range (natural prosody span)
  jitter: number; // micro-tremor of pitch periods (voiced-only)
  shimmer: number; // micro-tremor of amplitude (voiced-only)
  speechRateVar: number;
  mfcc: number[]; // 13 mean MFCCs (for embedding proxy)

  // ---- BUG-FIX ADDITIONS: codec-robust + relative discriminators ----
  // These features fix the "real recorded voice flagged as fake" bug by
  // separating *codec* artefacts (which hit REAL recordings too) from genuine
  // *neural-vocoder / synthesis* artefacts.
  codecCutoffHz: number; // frequency where spectral energy collapses (opus/webm ~7-8k)
  isLikelyCodec: boolean; // true when the HF loss is a codec, not a vocoder, signature
  hnrDb: number; // harmonics-to-noise ratio (dB) — TTS is often *too* clean OR too noisy
  voicedRatio: number; // fraction of frames that are voiced (0..1)
  spectralFlatnessVoiced: number; // flatness on voiced/energetic frames only (stable)
  modulation4Hz: number; // 4 Hz syllabic envelope modulation depth (natural speech ~high)
  f0DeltaVar: number; // variance of frame-to-frame F0 delta (natural contour dynamics)
  qualityFlag: "ok" | "too_short" | "too_silent" | "low_snr"; // input-quality gate
}

export type TierId = 0 | 1 | 2;

export interface TierResult {
  tier: TierId;
  name: string;
  invoked: boolean;
  score: number; // 0..1  (probability the audio is synthetic)
  latencyMs: number;
  reason: string;
  earlyExit?: boolean;
}

export interface SignalVote {
  id: string;
  label: string;
  score: number; // 0..1 fraud/synthetic likelihood
  weight: number;
  detail: string;
}

/** SHAP-style contribution used to explain the fused risk score. */
export interface ShapContribution {
  feature: string;
  contribution: number; // signed points on 0..100 scale
  direction: "increases" | "decreases";
  detail: string;
}

export interface LanguageRouting {
  detected: string;
  code: string;
  confidence: number;
  distribution: { language: string; code: string; prob: number }[];
  adapter: string; // LoRA adapter selected
  codeSwitching: boolean;
  /** Where the language decision came from. The pure-DSP web demo CANNOT truly
   * identify a spoken language from acoustics alone, so by default this is
   * "undetermined" (honest) rather than a confidently-wrong guess. A real
   * IndicLID ONNX model (loaded via the Colab export) sets this to "onnx-lid". */
  source: "onnx-lid" | "acoustic-heuristic" | "undetermined" | "user-selected";
  /** Human-readable note explaining the routing decision / limitation. */
  note: string;
}

export interface SpeakerCheck {
  enrolled: boolean;
  claimedSpeaker: string | null;
  cosineSimilarity: number | null; // vs enrolled voiceprint
  mismatch: boolean;
  note: string;
}

export interface CallContext {
  channel: string; // e.g. "SIP / FreeSWITCH", "Softphone", "Upload"
  aniReputation: number; // 0..1 (1 = trusted known contact)
  knownContact: boolean;
  transactionType: string;
  transactionValueInr: number;
  timeOfDayRisk: number; // 0..1
  claimedSpeaker: string | null;
}

export interface RiskAssessment {
  riskScore: number; // 0..100
  band: "LOW" | "ELEVATED" | "HIGH" | "CRITICAL";
  verdict: "AUTHENTIC" | "SUSPICIOUS" | "LIKELY_CLONE" | "INCONCLUSIVE";
  tiers: TierResult[];
  votes: SignalVote[];
  shap: ShapContribution[];
  language: LanguageRouting;
  speaker: SpeakerCheck;
  context: CallContext;
  requiresOutOfBand: boolean;
  smartExplanation: string;
  featureHash: string; // SHA-256 of feature vector (privacy-preserving)
  totalLatencyMs: number;
  timestamp: number;
}

export interface LedgerBlock {
  index: number;
  timestamp: number;
  type: "CONSENT" | "RISK_SCORE" | "ESCALATION" | "GENESIS";
  payloadHash: string; // SHA-256 of the (off-chain) payload — no raw audio
  summary: string;
  riskScore?: number;
  actor: string;
  prevHash: string;
  hash: string;
  nonce: number;
}
