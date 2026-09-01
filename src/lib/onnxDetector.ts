// ============================================================================
// Real trained-model inference in the browser (onnxruntime-web, WASM).
//
//   Tier-1  aasist_lite.onnx   : 64x200 log-mel  -> spoof logit
//   Fusion  fusion_lgbm.onnx   : 23 DSP+prosody feats + cm_score -> P(fake)
//
// This runs the ACTUAL models trained in kaggle_training/train.py — not the
// heuristic proxy in detectionEngine.ts. All feature extraction is librosa-
// compatible (see melFeatures.ts) and validated to ~1e-6 against librosa.
// ============================================================================

import * as ort from "onnxruntime-web";
import {
  extractDspFeatures,
  featureVectorForFusion,
  melSpectrogramForCnn,
  prepareSignal,
  resampleTo16k,
  N_MELS_CNN,
  TARGET_FRAMES,
  type DspFeatures,
} from "./melFeatures";

export interface OnnxCalibration {
  fusion_threshold: number;
  threshold_is_calibrated?: boolean;
  eer_percent?: number;
  feature_order: string[];
  n_features: number;
}

export interface OnnxDetection {
  available: true;
  cmScore: number; // Tier-1 AASIST-Lite sigmoid(logit)
  cmLogit: number;
  probFake: number; // fusion P(spoof)
  probReal: number;
  label: number; // fusion argmax (0=real, 1=fake)
  threshold: number;
  thresholdCalibrated: boolean;
  isFake: boolean;
  riskScore: number; // 0..100, = probFake*100
  features: DspFeatures;
  featureVector: number[]; // 23 values in calibration order
  featureOrder: string[];
  latencyMs: number;
  cmLatencyMs: number; // Tier-1 mel-CNN inference time
  fusionLatencyMs: number; // fusion LightGBM inference time
}

export interface OnnxUnavailable {
  available: false;
  error: string;
}

export type OnnxResult = OnnxDetection | OnnxUnavailable;

const MODELS_BASE = "/models";

let sessionsPromise: Promise<{
  cm: ort.InferenceSession;
  fusion: ort.InferenceSession;
  calib: OnnxCalibration;
}> | null = null;

function configureOrtOnce() {
  // Single-threaded WASM: no SharedArrayBuffer / cross-origin isolation needed.
  ort.env.wasm.numThreads = 1;
  ort.env.wasm.proxy = false;
  // Serve the .wasm/.mjs from /public/ort (copied from the onnxruntime-web dist).
  ort.env.wasm.wasmPaths = "/ort/";
}

async function loadSessions() {
  if (!sessionsPromise) {
    sessionsPromise = (async () => {
      configureOrtOnce();
      const [cmModel, fusionModel, calib] = await Promise.all([
        fetchBuffer(`${MODELS_BASE}/aasist_lite.onnx`),
        fetchBuffer(`${MODELS_BASE}/fusion_lgbm.onnx`),
        fetchJson<OnnxCalibration>(`${MODELS_BASE}/calibration.json`),
      ]);
      // aasist_lite.onnx is self-contained (weights embedded) — no external
      // .onnx.data sidecar to load.
      const cm = await ort.InferenceSession.create(new Uint8Array(cmModel), {
        executionProviders: ["wasm"],
      });
      const fusion = await ort.InferenceSession.create(new Uint8Array(fusionModel), {
        executionProviders: ["wasm"],
      });
      return { cm, fusion, calib };
    })().catch((e) => {
      sessionsPromise = null; // allow retry on next call
      throw e;
    });
  }
  return sessionsPromise;
}

async function fetchBuffer(url: string): Promise<ArrayBuffer> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`fetch ${url} -> ${r.status}`);
  return r.arrayBuffer();
}
async function fetchJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`fetch ${url} -> ${r.status}`);
  return r.json() as Promise<T>;
}

const now = () => (typeof performance !== "undefined" ? performance.now() : 0);

/**
 * Run the real trained cascade on a mono waveform.
 * @param samples raw mono PCM (any sample rate)
 * @param sampleRate source sample rate of `samples`
 */
export async function runOnnxDetection(
  samples: Float32Array,
  sampleRate: number
): Promise<OnnxResult> {
  const t0 = now();
  let sessions;
  try {
    sessions = await loadSessions();
  } catch (e) {
    return { available: false, error: e instanceof Error ? e.message : String(e) };
  }
  try {
    const { cm, fusion, calib } = sessions;

    // Match training: resample to 16 kHz, truncate to 3.5 s, peak-normalize.
    const y = prepareSignal(resampleTo16k(samples, sampleRate));

    // --- Tier 1: AASIST-Lite mel-CNN ---
    const tCm = now();
    const mel = melSpectrogramForCnn(y);
    const cmOut = await cm.run({
      [cm.inputNames[0]]: new ort.Tensor("float32", mel, [1, 1, N_MELS_CNN, TARGET_FRAMES]),
    });
    const cmLogit = Number(cmOut[cm.outputNames[0]].data[0]);
    const cmScore = 1 / (1 + Math.exp(-cmLogit));
    const cmLatencyMs = Math.round((now() - tCm) * 100) / 100;

    // --- Fusion: LightGBM over DSP+prosody feats + cm_score ---
    const tFusion = now();
    const features = extractDspFeatures(y);
    const featureVector = featureVectorForFusion(features, cmScore);
    if (featureVector.length !== calib.n_features) {
      return {
        available: false,
        error: `feature count ${featureVector.length} != calibration n_features ${calib.n_features}`,
      };
    }
    const fusionOut = await fusion.run({
      [fusion.inputNames[0]]: new ort.Tensor(
        "float32",
        Float32Array.from(featureVector),
        [1, featureVector.length]
      ),
    });
    const label = Number(fusionOut["label"]?.data[0] ?? 0);
    const probData = fusionOut["probabilities"]?.data as
      | Float32Array
      | undefined;
    // probabilities tensor is [P(real), P(fake)] (class order 0,1).
    const probReal = probData ? Number(probData[0]) : label === 1 ? 0 : 1;
    const probFake = probData ? Number(probData[1]) : label === 1 ? 1 : 0;

    const fusionLatencyMs = Math.round((now() - tFusion) * 100) / 100;
    const threshold = calib.fusion_threshold ?? 0.5;
    const isFake = probFake >= threshold;

    return {
      available: true,
      cmScore,
      cmLogit,
      probFake,
      probReal,
      label,
      threshold,
      thresholdCalibrated: calib.threshold_is_calibrated ?? true,
      isFake,
      riskScore: Math.round(probFake * 100),
      features,
      featureVector,
      featureOrder: calib.feature_order,
      latencyMs: Math.round((now() - t0) * 100) / 100,
      cmLatencyMs,
      fusionLatencyMs,
    };
  } catch (e) {
    return { available: false, error: e instanceof Error ? e.message : String(e) };
  }
}
