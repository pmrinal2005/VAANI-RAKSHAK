// ============================================================================
// Browser-side audio feature extraction (Web Audio API + pure DSP in JS).
// EDGE-FIRST: raw waveforms never leave the client.
// ============================================================================

import type { AudioFeatures } from "./types";

const TARGET_SR = 16000;

export async function decodeToMono(
  input: ArrayBuffer
): Promise<{ samples: Float32Array; sampleRate: number }> {
  const AudioCtx: typeof AudioContext =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new AudioCtx();
  const audioBuffer = await ctx.decodeAudioData(input.slice(0));
  const sr = audioBuffer.sampleRate;
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

function estimateF0Strength(frame: Float32Array, sr: number): { f0: number; strength: number } {
  const minLag = Math.floor(sr / 400);
  const maxLag = Math.floor(sr / 70);
  let r0 = 0;
  for (let i = 0; i < frame.length; i++) r0 += frame[i] * frame[i];
  r0 = r0 || 1e-9;
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
  const strength = Math.max(0, Math.min(1, bestCorr / r0));
  return { f0: bestLag > 0 ? sr / bestLag : 0, strength };
}

function voicedAutoStrength(
  wav: Float32Array,
  sr: number,
  hop: number,
  frameLen: number,
  energyThr: number
): number {
  const vals: number[] = [];
  for (let s = 0; s + frameLen < wav.length; s += hop) {
    const fr = wav.subarray(s, s + frameLen);
    let e = 0;
    for (let i = 0; i < fr.length; i++) e += fr[i] * fr[i];
    if (Math.sqrt(e / fr.length) < energyThr) continue;
    const { f0, strength } = estimateF0Strength(fr, sr);
    if (f0 >= 70 && f0 <= 400) vals.push(strength);
  }
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
}

function voicedSpectralFlatness(
  wav: Float32Array,
  sr: number,
  hop: number,
  frameLen: number,
  energyThr: number
): number {
  const N = 512;
  const w = hann(N);
  const flatnesses: number[] = [];
  for (let s = 0; s + frameLen < wav.length; s += hop) {
    let e = 0;
    for (let i = 0; i < frameLen; i++) e += wav[s + i] * wav[s + i];
    if (Math.sqrt(e / frameLen) < energyThr) continue;
    const seg = new Float32Array(N);
    for (let i = 0; i < N; i++) seg[i] = (wav[s + i] || 0) * w[i];
    const { mag } = magnitudeSpectrum(seg);
    let logSum = 0;
    let arith = 0;
    let cnt = 0;
    const kMax = Math.min(mag.length, Math.floor((3800 * N) / sr));
    for (let k = 1; k < kMax; k++) {
      const m = mag[k] + 1e-9;
      logSum += Math.log(m);
      arith += m;
      cnt++;
    }
    if (!cnt) continue;
    const geo = Math.exp(logSum / cnt);
    flatnesses.push(geo / (arith / cnt + 1e-9));
  }
  if (!flatnesses.length) return 0;
  return flatnesses.reduce((a, b) => a + b, 0) / flatnesses.length;
}

function meanMfcc(wav: Float32Array, nCoeff = 13): number[] {
  const N = 512;
  const w = hann(N);
  const hop = 256;
  const acc = new Array(nCoeff).fill(0);
  let frames = 0;
  for (let s = 0; s + N < wav.length; s += hop) {
    const seg = new Float32Array(N);
    for (let i = 0; i < N; i++) seg[i] = wav[s + i] * w[i];
    const { mag } = magnitudeSpectrum(seg);
    const nMels = 26;
    const mels = new Float32Array(nMels);
    for (let m = 0; m < nMels; m++) {
      const lo = Math.floor((m / nMels) * mag.length);
      const hi = Math.floor(((m + 1) / nMels) * mag.length);
      let sum = 0;
      for (let k = lo; k < hi; k++) sum += mag[k];
      mels[m] = Math.log(sum / Math.max(1, hi - lo) + 1e-9);
    }
    for (let c = 0; c < nCoeff; c++) {
      let dct = 0;
      for (let m = 0; m < nMels; m++) {
        dct += mels[m] * Math.cos((Math.PI * c * (m + 0.5)) / nMels);
      }
      acc[c] += dct;
    }
    frames++;
  }
  return acc.map((v) => (frames ? v / frames : 0));
}

export function extractFeatures(rawSamples: Float32Array, sampleRate: number): AudioFeatures {
  const resampled = resample(rawSamples, sampleRate);
  const wav = normalize(resampled);
  const sr = TARGET_SR;
  const T = wav.length;
  const dur = T / sr;

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

  let zc = 0;
  for (let i = 1; i < T; i++) if (wav[i] * wav[i - 1] < 0) zc++;
  const zeroCrossingRate = zc / T;

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
  for (let k = 0; k < mag.length; k++) spread += (freqs[k] - centroid) ** 2 * (mag[k] / magSum);
  spread = Math.sqrt(spread);

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

  let hf = 0;
  for (let k = 0; k < mag.length; k++) if (freqs[k] >= 6000) hf += mag[k];
  const hfEnergyRatio = hf / (magSum + 1e-9);

  let cum2 = 0;
  let codecCutoffHz = freqs[freqs.length - 1] || 8000;
  const target95 = 0.95 * magSum;
  for (let k = 0; k < mag.length; k++) {
    cum2 += mag[k] + 1e-9;
    if (cum2 >= target95) {
      codecCutoffHz = freqs[k];
      break;
    }
  }
  const isLikelyCodec = codecCutoffHz < 8500 && codecCutoffHz > 5500 && hfEnergyRatio < 0.08;

  let phaseDisc = 0;
  const hopP = 256;
  const flP = 512;
  let prevPhase = 0;
  let pCount = 0;
  for (let s = 0; s + flP < T; s += hopP) {
    const fr = wav.subarray(s, s + flP);
    let re = 0;
    let im = 0;
    for (let n = 0; n < 64; n++) {
      const ang = (-2 * Math.PI * 8 * n) / 64;
      re += fr[n] * Math.cos(ang);
      im += fr[n] * Math.sin(ang);
    }
    const ph = Math.atan2(im, re);
    if (pCount > 0) phaseDisc += Math.abs(ph - prevPhase);
    prevPhase = ph;
    pCount++;
  }
  const phaseDiscontinuity = pCount > 1 ? phaseDisc / (pCount - 1) : 0;

  const hop = 256;
  const frameLen = 512;
  const energyThr = 0.02;
  const f0s: number[] = [];
  const amps: number[] = [];
  let voiced = 0;
  let frames = 0;
  for (let s = 0; s + frameLen < T; s += hop) {
    const fr = wav.subarray(s, s + frameLen);
    let e = 0;
    for (let i = 0; i < fr.length; i++) e += fr[i] * fr[i];
    const rmsF = Math.sqrt(e / fr.length);
    frames++;
    if (rmsF < energyThr) continue;
    const { f0, strength } = estimateF0Strength(fr, sr);
    if (f0 >= 70 && f0 <= 400 && strength > 0.25) {
      f0s.push(f0);
      amps.push(rmsF);
      voiced++;
    }
  }
  const voicedRatio = frames ? voiced / frames : 0;
  const f0MeanHz = f0s.length ? f0s.reduce((a, b) => a + b, 0) / f0s.length : 0;
  let f0Var = 0;
  for (const v of f0s) f0Var += (v - f0MeanHz) ** 2;
  const f0Std = f0s.length > 1 ? Math.sqrt(f0Var / f0s.length) : 0;
  const sorted = [...f0s].sort((a, b) => a - b);
  const p5 = sorted[Math.floor(sorted.length * 0.05)] ?? f0MeanHz;
  const p95 = sorted[Math.floor(sorted.length * 0.95)] ?? f0MeanHz;
  const f0RangeHz = Math.max(0, p95 - p5);

  let jitter = 0;
  if (f0s.length > 2) {
    let d = 0;
    for (let i = 1; i < f0s.length; i++) d += Math.abs(f0s[i] - f0s[i - 1]);
    jitter = d / ((f0s.length - 1) * (f0MeanHz + 1e-9));
  }
  let shimmer = 0;
  if (amps.length > 2) {
    let d = 0;
    const meanA = amps.reduce((a, b) => a + b, 0) / amps.length;
    for (let i = 1; i < amps.length; i++) d += Math.abs(amps[i] - amps[i - 1]);
    shimmer = d / ((amps.length - 1) * (meanA + 1e-9));
  }

  let f0DeltaVar = 0;
  if (f0s.length > 2) {
    const deltas: number[] = [];
    for (let i = 1; i < f0s.length; i++) deltas.push(f0s[i] - f0s[i - 1]);
    const md = deltas.reduce((a, b) => a + b, 0) / deltas.length;
    for (const d of deltas) f0DeltaVar += (d - md) ** 2;
    f0DeltaVar /= deltas.length;
  }

  // 4 Hz syllabic envelope modulation
  const envHop = Math.floor(sr / 50);
  const env: number[] = [];
  for (let s = 0; s + envHop < T; s += envHop) {
    let e = 0;
    for (let i = 0; i < envHop; i++) e += wav[s + i] * wav[s + i];
    env.push(Math.sqrt(e / envHop));
  }
  let modulation4Hz = 0;
  if (env.length > 8) {
    const envSr = 50;
    let re = 0;
    let im = 0;
    for (let n = 0; n < env.length; n++) {
      const ang = (-2 * Math.PI * 4 * n) / envSr;
      re += env[n] * Math.cos(ang);
      im += env[n] * Math.sin(ang);
    }
    const meanEnv = env.reduce((a, b) => a + b, 0) / env.length;
    modulation4Hz = Math.sqrt(re * re + im * im) / (env.length * (meanEnv + 1e-9));
  }

  const autoStr = voicedAutoStrength(wav, sr, hop, frameLen, energyThr);
  const hnrDb = 10 * Math.log10(autoStr / (1 - autoStr + 1e-9) + 1e-9);
  const spectralFlatnessVoiced = voicedSpectralFlatness(wav, sr, hop, frameLen, energyThr);

  const mfcc = meanMfcc(wav, 13);
  const cqccVar = variance(mfcc.slice(1, 8));
  const lfccVar = variance(mfcc.slice(0, 6));

  let speechRateVar = 0;
  if (env.length > 4) {
    const meanE = env.reduce((a, b) => a + b, 0) / env.length;
    for (const e of env) speechRateVar += (e - meanE) ** 2;
    speechRateVar /= env.length;
  }

  let qualityFlag: AudioFeatures["qualityFlag"] = "ok";
  if (dur < 0.55) qualityFlag = "too_short";
  else if (silenceRatio > 0.92) qualityFlag = "too_silent";
  else if (rmsDb < -48) qualityFlag = "low_snr";

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
    phaseDiscontinuity: round(phaseDiscontinuity, 4),
    hfEnergyRatio: round(hfEnergyRatio, 4),
    cqccVar: round(cqccVar, 4),
    lfccVar: round(lfccVar, 4),
    f0MeanHz: round(f0MeanHz, 1),
    f0Std: round(f0Std, 2),
    f0RangeHz: round(f0RangeHz, 1),
    jitter: round(jitter, 4),
    shimmer: round(shimmer, 4),
    speechRateVar: round(speechRateVar, 5),
    mfcc: mfcc.map((v) => round(v, 4)),
    codecCutoffHz: round(codecCutoffHz, 1),
    isLikelyCodec,
    hnrDb: round(hnrDb, 2),
    voicedRatio: round(voicedRatio, 3),
    spectralFlatnessVoiced: round(spectralFlatnessVoiced, 4),
    modulation4Hz: round(modulation4Hz, 4),
    f0DeltaVar: round(f0DeltaVar, 3),
    qualityFlag,
  };
}

export function featureVector(f: AudioFeatures): number[] {
  return [
    f.rmsDb,
    f.silenceRatio,
    f.crestFactor,
    f.spectralCentroidHz,
    f.spectralSpreadHz,
    f.spectralFlatness,
    f.spectralRolloffHz,
    f.zeroCrossingRate,
    f.phaseDiscontinuity,
    f.hfEnergyRatio,
    f.cqccVar,
    f.lfccVar,
    f.f0MeanHz,
    f.f0Std,
    f.f0RangeHz,
    f.jitter,
    f.shimmer,
    f.speechRateVar,
    f.hnrDb,
    f.voicedRatio,
    f.spectralFlatnessVoiced,
    f.modulation4Hz,
    f.f0DeltaVar,
    f.codecCutoffHz,
    ...f.mfcc,
  ];
}

function variance(xs: number[]): number {
  if (!xs.length) return 0;
  const m = xs.reduce((a, b) => a + b, 0) / xs.length;
  return xs.reduce((a, b) => a + (b - m) ** 2, 0) / xs.length;
}

function round(v: number, d = 2): number {
  const p = Math.pow(10, d);
  return Math.round(v * p) / p;
}
