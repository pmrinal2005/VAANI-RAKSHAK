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

/** Autocorrelation-based pitch (F0) estimate + normalised periodicity strength.
 * strength ∈ [0,1] is the normalised autocorrelation peak — used both to gate
 * voicing (fixing the "real speech looks synthetic" bug) and to estimate HNR. */
function estimateF0Strength(frame: Float32Array, sr: number): { f0: number; strength: number } {
  const minLag = Math.floor(sr / 400); // 400 Hz
  const maxLag = Math.floor(sr / 70); // 70 Hz
  // energy at lag 0 (normaliser)
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

/** Mean normalised autocorrelation strength over voiced frames (for HNR). */
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

/** Spectral flatness computed only over voiced/energetic frames (stable). */
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
    // restrict to the speech band (<= codec-safe 3.8 kHz) so codec HF loss
    // does NOT inflate flatness for real recordings
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

  // ---- BUG-FIX: codec cutoff detection ----------------------------------
  // Real recordings from MediaRecorder (webm/opus) and phone codecs sharply
  // low-pass audio around 7-8 kHz. The ORIGINAL engine read that as a
  // "vocoder cutoff" and flagged genuine recordings as fake. Here we locate
  // the cutoff and decide whether it looks like a *codec* (broadband loss with
  // a clean shelf) vs a genuine synthesis artefact.
  // Build a smoothed energy-vs-frequency profile and find the highest freq that
  // still carries a meaningful fraction of the peak-band energy.
  const bandHz = 500;
  const nProfBands = Math.floor((TARGET_SR / 2) / bandHz);
  const prof = new Float32Array(nProfBands);
  for (let k = 0; k < mag.length; k++) {
    const bi = Math.min(nProfBands - 1, Math.floor(freqs[k] / bandHz));
    prof[bi] += mag[k];
  }
  let profPeak = 1e-9;
  for (let b = 0; b < nProfBands; b++) profPeak = Math.max(profPeak, prof[b]);
  // cutoff = highest band whose energy is >= 5% of the peak band
  let codecCutoffHz = TARGET_SR / 2;
  for (let b = nProfBands - 1; b >= 0; b--) {
    if (prof[b] >= 0.05 * profPeak) {
      codecCutoffHz = (b + 1) * bandHz;
      break;
    }
  }
  // A codec cutoff is a HARD shelf (steep drop) at a "round" telephony/opus
  // frequency (3.4k / 7k / 8k). Measure the drop steepness just below cutoff.
  const cutoffBand = Math.min(nProfBands - 1, Math.floor(codecCutoffHz / bandHz));
  const belowE = prof[Math.max(0, cutoffBand - 1)] + 1e-9;
  const aboveE = prof[Math.min(nProfBands - 1, cutoffBand + 1)] + 1e-9;
  const dropRatio = belowE / aboveE; // large => steep shelf (codec-like)
  const isLikelyCodec = codecCutoffHz <= 8200 && dropRatio > 6;

  // phase discontinuity proxy: 2nd difference of the signal (roughness)
  let d2 = 0;
  for (let i = 2; i < T; i++) d2 += Math.abs(wav[i] - 2 * wav[i - 1] + wav[i - 2]);
  const phaseDiscontinuity = d2 / T;

  // ---- frame-wise features: F0, jitter, shimmer (VOICED-ONLY) ----
  // BUG-FIX: the original computed jitter/shimmer over ALL frames incl. silence
  // & unvoiced noise, which made REAL speech look "too smooth" (fake). We now
  // gate on a per-frame voicing decision (energy + autocorrelation strength) so
  // jitter/shimmer reflect genuine glottal micro-variation, matching how
  // Praat/openSMILE compute them.
  const frameLen = 512;
  const hop = 256;
  const f0s: number[] = []; // voiced F0 track
  const voicedEnergies: number[] = []; // energies of voiced frames only
  const allEnergies: number[] = [];
  const envelope: number[] = []; // full amplitude envelope (for 4Hz modulation)
  let voicedFrames = 0;
  let totalFrames = 0;

  // global energy reference for voicing gate
  let gMax = 1e-9;
  for (let s = 0; s + frameLen < T; s += hop) {
    let e = 0;
    for (let i = 0; i < frameLen; i++) e += wav[s + i] * wav[s + i];
    gMax = Math.max(gMax, Math.sqrt(e / frameLen));
  }
  const voiceEnergyThr = 0.12 * gMax; // frame must carry real energy to be voiced

  for (let s = 0; s + frameLen < T; s += hop) {
    const fr = wav.subarray(s, s + frameLen);
    let e = 0;
    for (let i = 0; i < fr.length; i++) e += fr[i] * fr[i];
    const rmsFrame = Math.sqrt(e / fr.length);
    allEnergies.push(rmsFrame);
    envelope.push(rmsFrame);
    totalFrames++;

    if (rmsFrame < voiceEnergyThr) continue; // silence / very low energy -> unvoiced
    const { f0, strength } = estimateF0Strength(fr, sr);
    // voiced iff a clear periodicity exists in the human-speech F0 range
    if (f0 >= 70 && f0 <= 400 && strength > 0.35) {
      f0s.push(f0);
      voicedEnergies.push(rmsFrame);
      voicedFrames++;
    }
  }

  const mean = (a: number[]) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
  const std = (a: number[]) => {
    if (a.length < 2) return 0;
    const m = mean(a);
    return Math.sqrt(a.reduce((x, y) => x + (y - m) ** 2, 0) / a.length);
  };
  const percentile = (a: number[], p: number) => {
    if (!a.length) return 0;
    const sorted = [...a].sort((x, y) => x - y);
    const idx = Math.min(sorted.length - 1, Math.max(0, Math.round((p / 100) * (sorted.length - 1))));
    return sorted[idx];
  };

  const voicedRatio = totalFrames ? voicedFrames / totalFrames : 0;
  const f0MeanHz = mean(f0s);
  const f0Std = std(f0s);
  const f0RangeHz = f0s.length > 3 ? percentile(f0s, 95) - percentile(f0s, 5) : 0;

  // F0 delta dynamics (natural pitch contour moves; over-smooth TTS is flatter)
  const f0Deltas: number[] = [];
  for (let i = 1; i < f0s.length; i++) f0Deltas.push(f0s[i] - f0s[i - 1]);
  const f0DeltaVar = std(f0Deltas);

  // jitter: mean abs relative difference of consecutive VOICED F0 values
  let jitter = 0;
  if (f0s.length > 1) {
    let acc = 0;
    for (let i = 1; i < f0s.length; i++) acc += Math.abs(f0s[i] - f0s[i - 1]) / (f0s[i - 1] + 1e-9);
    jitter = acc / (f0s.length - 1);
  }
  // shimmer: mean abs relative difference of consecutive VOICED frame energies
  let shimmer = 0;
  if (voicedEnergies.length > 1) {
    let acc = 0;
    for (let i = 1; i < voicedEnergies.length; i++)
      acc += Math.abs(voicedEnergies[i] - voicedEnergies[i - 1]) / (voicedEnergies[i - 1] + 1e-9);
    shimmer = acc / (voicedEnergies.length - 1);
  }
  const speechRateVar = std(allEnergies);

  // ---- 4 Hz syllabic modulation depth --------------------------------------
  // Natural speech has strong ~4 Hz envelope modulation (syllable rate).
  // Compute normalised energy at 4 Hz of the frame-envelope signal.
  const envRate = sr / hop; // envelope sample rate (~62.5 Hz)
  let mod4 = 0;
  if (envelope.length > 8) {
    const envMean = mean(envelope);
    let re = 0;
    let im = 0;
    for (let n = 0; n < envelope.length; n++) {
      const ang = (-2 * Math.PI * 4 * n) / envRate;
      re += (envelope[n] - envMean) * Math.cos(ang);
      im += (envelope[n] - envMean) * Math.sin(ang);
    }
    const envStd = std(envelope) + 1e-9;
    mod4 = Math.sqrt(re * re + im * im) / (envelope.length * envStd);
  }
  const modulation4Hz = mod4;

  // ---- Harmonics-to-Noise Ratio (HNR, dB) ----------------------------------
  // From mean voiced autocorrelation strength: r/(1-r) in dB. Real voices sit
  // in a mid range; extreme values (very clean OR very noisy) are informative.
  const meanStrength = f0s.length ? voicedAutoStrength(wav, sr, hop, frameLen, voiceEnergyThr) : 0;
  const rHNR = Math.min(0.999, Math.max(0.001, meanStrength));
  const hnrDb = 10 * Math.log10(rHNR / (1 - rHNR));

  // ---- voiced-only spectral flatness (stable, noise-robust) ----------------
  const spectralFlatnessVoiced = voicedSpectralFlatness(wav, sr, hop, frameLen, voiceEnergyThr);

  // ---- input-quality gate --------------------------------------------------
  let qualityFlag: "ok" | "too_short" | "too_silent" | "low_snr" = "ok";
  if (dur < 0.6) qualityFlag = "too_short";
  else if (silenceRatio > 0.85 || voicedRatio < 0.06) qualityFlag = "too_silent";
  else if (rmsDb < -45) qualityFlag = "low_snr";

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
    f0RangeHz: round(f0RangeHz, 1),
    jitter: round(jitter, 4),
    shimmer: round(shimmer, 4),
    speechRateVar: round(speechRateVar, 4),
    mfcc: mfcc.map((v) => round(v, 3)),
    // codec-robust additions
    codecCutoffHz: round(codecCutoffHz, 0),
    isLikelyCodec,
    hnrDb: round(hnrDb, 2),
    voicedRatio: round(voicedRatio, 3),
    spectralFlatnessVoiced: round(spectralFlatnessVoiced, 4),
    modulation4Hz: round(modulation4Hz, 4),
    f0DeltaVar: round(f0DeltaVar, 3),
    qualityFlag,
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
    f.f0MeanHz, f.f0Std, f.f0RangeHz, f.jitter, f.shimmer, f.speechRateVar,
    f.codecCutoffHz, f.isLikelyCodec ? 1 : 0, f.hnrDb, f.voicedRatio,
    f.spectralFlatnessVoiced, f.modulation4Hz, f.f0DeltaVar, ...f.mfcc,
  ];
}
