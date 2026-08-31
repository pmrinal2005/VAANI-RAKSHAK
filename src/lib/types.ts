// ============================================================================
// VAANI-RAKSHAK — Core type definitions
// AI-Powered Real-Time Voice Cloning Detection Framework
// ============================================================================

/** Acoustic + behavioural features extracted from an audio chunk. */
export interface AudioFeatures {
  durationSec: number;
  sampleRate: number;
  rmsDb: number;
  silenceRatio: number;
  crestFactor: number;
  spectralCentroidHz: number;
  spectralSpreadHz: number;
  spectralFlatness: number;
  spectralRolloffHz: number;
  zeroCrossingRate: number;
  phaseDiscontinuity: number;
  hfEnergyRatio: number;
  cqccVar: number;
  lfccVar: number;
  f0MeanHz: number;
  f0Std: number;
  f0RangeHz: number;
  jitter: number;
  shimmer: number;
  speechRateVar: number;
  mfcc: number[];
  codecCutoffHz: number;
  isLikelyCodec: boolean;
  hnrDb: number;
  voicedRatio: number;
  spectralFlatnessVoiced: number;
  modulation4Hz: number;
  f0DeltaVar: number;
  qualityFlag: "ok" | "too_short" | "too_silent" | "low_snr";
}

export type TierId = 0 | 1 | 2;

export interface TierResult {
  tier: TierId;
  name: string;
  invoked: boolean;
  score: number;
  latencyMs: number;
  reason: string;
  earlyExit?: boolean;
}

export interface SignalVote {
  id: string;
  label: string;
  score: number;
  weight: number;
  detail: string;
}

export interface ShapContribution {
  feature: string;
  contribution: number;
  direction: "increases" | "decreases";
  detail: string;
}

export interface LanguageRouting {
  detected: string;
  code: string;
  confidence: number;
  distribution: { language: string; code: string; prob: number }[];
  adapter: string;
  codeSwitching: boolean;
  source: "onnx-lid" | "acoustic-heuristic" | "undetermined" | "user-selected";
  note: string;
}

export interface SpeakerCheck {
  enrolled: boolean;
  claimedSpeaker: string | null;
  cosineSimilarity: number | null;
  mismatch: boolean;
  note: string;
}

export interface CallContext {
  channel: string;
  aniReputation: number;
  knownContact: boolean;
  transactionType: string;
  transactionValueInr: number;
  timeOfDayRisk: number;
  claimedSpeaker: string | null;
}

export interface RiskAssessment {
  riskScore: number;
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
  featureHash: string;
  totalLatencyMs: number;
  timestamp: number;
}

export interface LedgerBlock {
  index: number;
  timestamp: number;
  type: "CONSENT" | "RISK_SCORE" | "ESCALATION" | "GENESIS";
  payloadHash: string;
  summary: string;
  riskScore?: number;
  actor: string;
  prevHash: string;
  hash: string;
  nonce: number;
}
