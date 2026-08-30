// ============================================================================
// Browser-side audio feature extraction (Web Audio API + pure DSP in JS).
// This is the EDGE-FIRST tier: all feature computation happens on-device in the
// caller's browser. Raw waveforms never leave the client — only a small numeric
// feature vector (and its SHA-256 hash) is used downstream. Mirrors the librosa/
// torchaudio Tier-0 DSP + prosody branch of the VAANI-RAKSHAK architecture.
// ============================================================================

import type { AudioFeatures } from "./types";

const TARGET_SR = 16000;

/** Decode an uploaded File / ArrayBuffer into a mono Float32 waveform @16kHz. */
export async function decodeToMono(
  input: ArrayBuffer
): Promise<{ samples: Float32Array; sampleRate: number }> {
  const AudioCtx: typeof AudioContext =
    (window as any).AudioContext || (window as any).webkitAudioContext;
  const ctx = new AudioCtx();
  const audioBuffer = await ctx.decodeAudioData(input.slice(0));
  const sr = audioBuffer.sampleRate;
  // downmix to mono
  const ch = audioBuffer.numberOfChannels;
  const len = audioBuffer.length;
  const mono = new Float32Array(len);
  for (let c = 0; c < ch; c++) {
    const data = audioBuffer.getChannelData(c);
    for (let i = 0; i < len; i++) mono[i] += data[i] / ch;
  }
  await ctx.close();
  return { samples: mono, sampleRate: sr };
}

/** Naive linear resample to 16 kHz. */
export function resample(samples: Float32Array, fromSr: number): Float32Array {
  if (fromSr === TARGET_SR) return samples;
  const ratio = TARGET_SR / fromSr;
  const outLen = Math.floor(samples.length * ratio);
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const srcPos = i / ratio;
    const i0 = Math.floor(srcPos);
    const i1 = Math.min(i0 + 1, samples.length - 1);
    const frac = srcPos - i0;
    out[i] = samples[i0] * (1 - frac) + samples[i1] * frac;
  }
  return out;
}

function normalize(x: Float32Array): Float32Array {
  let max = 1e-9;
  for (let i = 0; i < x.length; i++) max = Math.max(max, Math.abs(x[i]));
  const out = new Float32Array(x.length);
  for (let i = 0; i < x.length; i++) out[i] = x[i] / max;
  return out;
}

// ---- radix-agnostic DFT magnitude (small windows only) ----
function magnitudeSpectrum(frame: Float32Array): { mag: Float32Array; freqs: Float32Array } {
  const N = frame.length;
  const half = N >> 1;
  const mag = new Float32Array(half);
  const freqs = new Float32Array(half);
  for (let k = 0; k < half; k++) {
    let re = 0;
    let im = 0;
    for (let n = 0; n < N; n++) {
      const ang = (-2 * Math.PI * k * n) / N;
      re += frame[n] * Math.cos(ang);
      im += frame[n] * Math.sin(ang);
    }
    mag[k] = Math.sqrt(re * re + im * im);
    freqs[k] = (k * TARGET_SR) / N;
  }
  return { mag, freqs };
}

function hann(N: number): Float32Array {
  const w = new Float32Array(N);
  for (let n = 0; n < N; n++) w[n] = 0.5 - 0.5 * Math.cos((2 * Math.PI * n) / (N - 1));
  return w;
}

/** Autocorrelation-based pitch (F0) estimate for a frame. */
function estimateF0(frame: Float32Array, sr: number): number {
  const minLag = Math.floor(sr / 400); // 400 Hz
  const maxLag = Math.floor(sr / 70); // 70 Hz
  let bestLag = 0;
  let bestCorr = 0;
  for (let lag = minLag; lag <= maxLag && lag < frame.length; lag++) {
    let corr = 0;
    for (let i = 0; i < frame.length - lag; i++) corr += frame[i] * frame[i + lag];
    if (corr > bestCorr) {
      bestCorr = corr;
      bestLag = lag;
    }
  }
  return bestLag > 0 ? sr / bestLag : 0;
}

/** Compute the full feature vector used by the cascade tiers + fusion engine. */
export function extractFeatures(rawSamples: Float32Array, sampleRate: number): AudioFeatures {
  const resampled = resample(rawSamples, sampleRate);
  const wav = normalize(resampled);
  const sr = TARGET_SR;
  const T = wav.length;
  const dur = T / sr;

  // ---- energy / dynamics ----
  let sumSq = 0;
  let peak = 1e-9;
  for (let i = 0; i < T; i++) {
    sumSq += wav[i] * wav[i];
    peak = Math.max(peak, Math.abs(wav[i]));
  }
  const rms = Math.sqrt(sumSq / T + 1e-12);
  const rmsDb = 20 * Math.log10(rms + 1e-12);
  const crestFactor = peak / (rms + 1e-9);

  const silThr = Math.pow(10, -40 / 20);
  let silCount = 0;
  for (let i = 0; i < T; i++) if (Math.abs(wav[i]) < silThr) silCount++;
  const silenceRatio = silCount / T;

  // ---- zero-crossing rate ----
  let zc = 0;
  for (let i = 1; i < T; i++) if (wav[i] * wav[i - 1] < 0) zc++;
  const zeroCrossingRate = zc / T;

  // ---- global spectrum (down-sampled window) ----
  const N = 2048;
  const win = hann(N);
  const seg = new Float32Array(N);
  const start = Math.max(0, Math.floor((T - N) / 2));
  for (let i = 0; i < N; i++) seg[i] = (wav[start + i] || 0) * win[i];
  const { mag, freqs } = magnitudeSpectrum(seg);

  let magSum = 0;
  let logSum = 0;
  for (let k = 0; k < mag.length; k++) {
    magSum += mag[k] + 1e-9;
    logSum += Math.log(mag[k] + 1e-9);
  }
  const geoMean = Math.exp(logSum / mag.length);
  const arithMean = magSum / mag.length;
  const spectralFlatness = geoMean / (arithMean + 1e-9);

  let centroid = 0;
  for (let k = 0; k < mag.length; k++) centroid += freqs[k] * (mag[k] / magSum);
  let spread = 0;
  for (let k = 0; k < mag.length; k++)
    spread += (freqs[k] - centroid) ** 2 * (mag[k] / magSum);
  spread = Math.sqrt(spread);

  // rolloff (85% energy)
  let cum = 0;
  let rolloff = 0;
  const targetE = 0.85 * magSum;
  for (let k = 0; k < mag.length; k++) {
    cum += mag[k] + 1e-9;
    if (cum >= targetE) {
      rolloff = freqs[k];
      break;
    }
  }

  // HF energy ratio (>6kHz)
  let hf = 0;
  for (let k = 0; k < mag.length; k++) if (freqs[k] > 6000) hf += mag[k];
  const hfEnergyRatio = hf / magSum;

  // phase discontinuity proxy: 2nd difference of the signal (roughness)
  let d2 = 0;
  for (let i = 2; i < T; i++) d2 += Math.abs(wav[i] - 2 * wav[i - 1] + wav[i - 2]);
  const phaseDiscontinuity = d2 / T;

  // ---- frame-wise features: F0, jitter, shimmer, cepstral variance ----
  const frameLen = 512;
  const hop = 256;
  const f0s: number[] = [];
  const frameEnergies: number[] = [];
  const centroids: number[] = [];
  for (let s = 0; s + frameLen < T; s += hop) {
    const fr = wav.subarray(s, s + frameLen);
    const f0 = estimateF0(fr, sr);
    if (f0 > 0) f0s.push(f0);
    let e = 0;
    for (let i = 0; i < fr.length; i++) e += fr[i] * fr[i];
    frameEnergies.push(Math.sqrt(e / fr.length));
  }

  const mean = (a: number[]) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
  const std = (a: number[]) => {
    if (a.length < 2) return 0;
    const m = mean(a);
    return Math.sqrt(a.reduce((x, y) => x + (y - m) ** 2, 0) / a.length);
  };

  const f0MeanHz = mean(f0s);
  const f0Std = std(f0s);

  // jitter: mean abs relative difference of consecutive F0 periods
  let jitter = 0;
  if (f0s.length > 1) {
    let acc = 0;
    for (let i = 1; i < f0s.length; i++) acc += Math.abs(f0s[i] - f0s[i - 1]) / (f0s[i - 1] + 1e-9);
    jitter = acc / (f0s.length - 1);
  }
  // shimmer: mean abs relative difference of consecutive frame energies
  let shimmer = 0;
  if (frameEnergies.length > 1) {
    let acc = 0;
    for (let i = 1; i < frameEnergies.length; i++)
      acc += Math.abs(frameEnergies[i] - frameEnergies[i - 1]) / (frameEnergies[i - 1] + 1e-9);
    shimmer = acc / (frameEnergies.length - 1);
  }
  const speechRateVar = std(frameEnergies);

  // cepstral variance proxies (use log-spectrum roughness as CQCC/LFCC stand-in)
  const cqccVar = spread / 1000;
  const lfccVar = spectralFlatness * 10;

  // MFCC proxy: coarse log-mel of the global spectrum, DCT-lite
  const nBands = 13;
  const mfcc: number[] = [];
  const bandSize = Math.floor(mag.length / nBands);
  const logMel: number[] = [];
  for (let b = 0; b < nBands; b++) {
    let e = 0;
    for (let k = b * bandSize; k < (b + 1) * bandSize; k++) e += mag[k];
    logMel.push(Math.log(e + 1e-9));
  }
  for (let i = 0; i < nBands; i++) {
    let acc = 0;
    for (let b = 0; b < nBands; b++)
      acc += logMel[b] * Math.cos((Math.PI * i * (b + 0.5)) / nBands);
    mfcc.push(acc / nBands);
  }

  return {
    durationSec: round(dur, 3),
    sampleRate: sr,
    rmsDb: round(rmsDb, 2),
    silenceRatio: round(silenceRatio, 3),
    crestFactor: round(crestFactor, 3),
    spectralCentroidHz: round(centroid, 1),
    spectralSpreadHz: round(spread, 1),
    spectralFlatness: round(spectralFlatness, 4),
    spectralRolloffHz: round(rolloff, 1),
    zeroCrossingRate: round(zeroCrossingRate, 4),
    phaseDiscontinuity: round(phaseDiscontinuity, 5),
    hfEnergyRatio: round(hfEnergyRatio, 4),
    cqccVar: round(cqccVar, 4),
    lfccVar: round(lfccVar, 4),
    f0MeanHz: round(f0MeanHz, 1),
    f0Std: round(f0Std, 2),
    jitter: round(jitter, 4),
    shimmer: round(shimmer, 4),
    speechRateVar: round(speechRateVar, 4),
    mfcc: mfcc.map((v) => round(v, 3)),
  };
}

function round(v: number, d: number): number {
  const f = Math.pow(10, d);
  return Math.round(v * f) / f;
}

/** Feature vector as an ordered numeric array (for hashing / model input). */
export function featureVector(f: AudioFeatures): number[] {
  return [
    f.durationSec, f.rmsDb, f.silenceRatio, f.crestFactor,
    f.spectralCentroidHz, f.spectralSpreadHz, f.spectralFlatness, f.spectralRolloffHz,
    f.zeroCrossingRate, f.phaseDiscontinuity, f.hfEnergyRatio, f.cqccVar, f.lfccVar,
    f.f0MeanHz, f.f0Std, f.jitter, f.shimmer, f.speechRateVar, ...f.mfcc,
  ];
}
