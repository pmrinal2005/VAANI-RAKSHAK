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
  jitter: number; // micro-tremor of pitch periods
  shimmer: number; // micro-tremor of amplitude
  speechRateVar: number;
  mfcc: number[]; // 13 mean MFCCs (for embedding proxy)
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
  verdict: "AUTHENTIC" | "SUSPICIOUS" | "LIKELY_CLONE";
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
