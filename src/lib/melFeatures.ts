// ============================================================================
// librosa-compatible DSP feature extraction (pure TS, runs in browser + Node).
//
// Reproduces exactly the features the trained models were fitted on in
// kaggle_training/train.py:
//   • to_mel()               → 64-mel log-power spectrogram for AASIST-Lite ONNX
//   • dsp_prosody_features() → the 23-dim vector for the LightGBM fusion ONNX
//
// Matched to librosa 0.11 defaults: STFT center=True, pad_mode='constant'
// (zero pad), periodic Hann window, Slaney mel filterbank (norm='slaney'),
// power_to_db(ref=1.0, top_db=80), and orthonormal DCT-II for MFCC.
// ============================================================================

export const SR = 16000;
export const N_MELS_CNN = 64;
export const TARGET_FRAMES = 200;

// ---- Radix-2 iterative Cooley–Tukey FFT (in-place, N power of two) ----------
function fft(re: Float64Array, im: Float64Array): void {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      const tr = re[i];
      re[i] = re[j];
      re[j] = tr;
      const ti = im[i];
      im[i] = im[j];
      im[j] = ti;
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    const wr = Math.cos(ang);
    const wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let curR = 1;
      let curI = 0;
      const half = len >> 1;
      for (let k = 0; k < half; k++) {
        const aR = re[i + k];
        const aI = im[i + k];
        const bR = re[i + k + half] * curR - im[i + k + half] * curI;
        const bI = re[i + k + half] * curI + im[i + k + half] * curR;
        re[i + k] = aR + bR;
        im[i + k] = aI + bI;
        re[i + k + half] = aR - bR;
        im[i + k + half] = aI - bI;
        const nR = curR * wr - curI * wi;
        curI = curR * wi + curI * wr;
        curR = nR;
      }
    }
  }
}

// periodic Hann (fftbins=True): 0.5 - 0.5*cos(2*pi*n/N)
function hannPeriodic(N: number): Float64Array {
  const w = new Float64Array(N);
  for (let n = 0; n < N; n++) w[n] = 0.5 - 0.5 * Math.cos((2 * Math.PI * n) / N);
  return w;
}

// Magnitude STFT with center=True, pad_mode='constant' (zeros).
// Returns { frames: Float64Array[], nBins } where each frame is |FFT| over
// nBins = nFft/2 + 1 non-negative-frequency bins.
function stftMagnitude(
  y: Float32Array,
  nFft: number,
  hop: number
): { frames: Float64Array[]; nBins: number } {
  const w = hannPeriodic(nFft);
  const nBins = (nFft >> 1) + 1;
  const nFrames = 1 + Math.floor(y.length / hop);
  const pad = nFft >> 1; // center offset
  const re = new Float64Array(nFft);
  const im = new Float64Array(nFft);
  const frames: Float64Array[] = [];
  for (let t = 0; t < nFrames; t++) {
    const start = t * hop - pad;
    for (let i = 0; i < nFft; i++) {
      const idx = start + i;
      const s = idx >= 0 && idx < y.length ? y[idx] : 0;
      re[i] = s * w[i];
      im[i] = 0;
    }
    fft(re, im);
    const mag = new Float64Array(nBins);
    for (let k = 0; k < nBins; k++) mag[k] = Math.hypot(re[k], im[k]);
    frames.push(mag);
  }
  return { frames, nBins };
}

function fftFrequencies(nFft: number): Float64Array {
  const nBins = (nFft >> 1) + 1;
  const f = new Float64Array(nBins);
  for (let k = 0; k < nBins; k++) f[k] = (k * SR) / nFft;
  return f;
}

// ---- Slaney mel filterbank (librosa.filters.mel, htk=False, norm='slaney') --
function hzToMel(hz: number): number {
  const fSp = 200 / 3;
  const minLogHz = 1000;
  const minLogMel = minLogHz / fSp; // 15
  const logstep = Math.log(6.4) / 27.0;
  return hz < minLogHz ? hz / fSp : minLogMel + Math.log(hz / minLogHz) / logstep;
}
function melToHz(mel: number): number {
  const fSp = 200 / 3;
  const minLogHz = 1000;
  const minLogMel = minLogHz / fSp;
  const logstep = Math.log(6.4) / 27.0;
  return mel < minLogMel ? fSp * mel : minLogHz * Math.exp(logstep * (mel - minLogMel));
}

function melFilterbank(nFft: number, nMels: number, fmin = 0, fmax = SR / 2): Float64Array[] {
  const nBins = (nFft >> 1) + 1;
  const fftFreqs = fftFrequencies(nFft);
  const melMin = hzToMel(fmin);
  const melMax = hzToMel(fmax);
  const melPts = new Float64Array(nMels + 2);
  for (let i = 0; i < nMels + 2; i++) {
    melPts[i] = melToHz(melMin + ((melMax - melMin) * i) / (nMels + 1));
  }
  const fdiff = new Float64Array(nMels + 1);
  for (let i = 0; i < nMels + 1; i++) fdiff[i] = melPts[i + 1] - melPts[i];

  const fb: Float64Array[] = [];
  for (let m = 0; m < nMels; m++) {
    const row = new Float64Array(nBins);
    const enorm = 2.0 / (melPts[m + 2] - melPts[m]); // Slaney area normalization
    for (let k = 0; k < nBins; k++) {
      const lower = (fftFreqs[k] - melPts[m]) / fdiff[m];
      const upper = (melPts[m + 2] - fftFreqs[k]) / fdiff[m + 1];
      const v = Math.max(0, Math.min(lower, upper));
      row[k] = v * enorm;
    }
    fb.push(row);
  }
  return fb;
}

// librosa.power_to_db(ref=1.0, amin=1e-10, top_db=80) over a full 2D matrix.
// mels: [nMels] rows × nFrames. Floor is global (max - top_db).
function powerToDb(mels: Float64Array[], topDb = 80): void {
  const amin = 1e-10;
  let maxDb = -Infinity;
  for (const row of mels) {
    for (let i = 0; i < row.length; i++) {
      const db = 10 * Math.log10(Math.max(amin, row[i])); // ref=1 → -10log10(max(amin,1))=0
      row[i] = db;
      if (db > maxDb) maxDb = db;
    }
  }
  const floor = maxDb - topDb;
  for (const row of mels) {
    for (let i = 0; i < row.length; i++) if (row[i] < floor) row[i] = floor;
  }
}

// ---- Public: 64-mel log-power spectrogram (1,1,64,200) for AASIST-Lite ------
export function melSpectrogramForCnn(y: Float32Array): Float32Array {
  const { frames } = stftMagnitude(y, 1024, 256); // magnitude
  const fb = melFilterbank(1024, N_MELS_CNN);
  const T = frames.length;
  // mel power = filterbank @ (magnitude^2)
  const mels: Float64Array[] = [];
  for (let m = 0; m < N_MELS_CNN; m++) mels.push(new Float64Array(T));
  for (let t = 0; t < T; t++) {
    const mag = frames[t];
    for (let m = 0; m < N_MELS_CNN; m++) {
      const row = fb[m];
      let acc = 0;
      for (let k = 0; k < row.length; k++) acc += row[k] * (mag[k] * mag[k]);
      mels[m][t] = acc;
    }
  }
  powerToDb(mels, 80);
  // pad/truncate to TARGET_FRAMES, row-major [mel][frame] -> mel*200 + frame
  const out = new Float32Array(N_MELS_CNN * TARGET_FRAMES); // zero-padded
  const copyT = Math.min(T, TARGET_FRAMES);
  for (let m = 0; m < N_MELS_CNN; m++) {
    for (let t = 0; t < copyT; t++) out[m * TARGET_FRAMES + t] = mels[m][t];
  }
  return out;
}

// orthonormal DCT-II of a length-N vector; returns first K coefficients.
function dctII(x: Float64Array, K: number): Float64Array {
  const N = x.length;
  const out = new Float64Array(K);
  for (let k = 0; k < K; k++) {
    let sum = 0;
    for (let n = 0; n < N; n++) sum += x[n] * Math.cos((Math.PI * (n + 0.5) * k) / N);
    const scale = k === 0 ? Math.sqrt(1 / N) : Math.sqrt(2 / N);
    out[k] = scale * sum;
  }
  return out;
}

// librosa.feature.mfcc(n_mfcc=13) mean over frames (n_mels=128 melspec + DCT).
function mfccMean(y: Float32Array, nMfcc = 13): number[] {
  const { frames } = stftMagnitude(y, 2048, 512);
  const fb = melFilterbank(2048, 128);
  const T = frames.length;
  const mels: Float64Array[] = [];
  for (let m = 0; m < 128; m++) mels.push(new Float64Array(T));
  for (let t = 0; t < T; t++) {
    const mag = frames[t];
    for (let m = 0; m < 128; m++) {
      const row = fb[m];
      let acc = 0;
      for (let k = 0; k < row.length; k++) acc += row[k] * (mag[k] * mag[k]);
      mels[m][t] = acc;
    }
  }
  powerToDb(mels, 80);
  const acc = new Float64Array(nMfcc);
  const col = new Float64Array(128);
  for (let t = 0; t < T; t++) {
    for (let m = 0; m < 128; m++) col[m] = mels[m][t];
    const c = dctII(col, nMfcc);
    for (let k = 0; k < nMfcc; k++) acc[k] += c[k];
  }
  return Array.from(acc, (v) => (T ? v / T : 0));
}

// ---- The 23-dim feature record in calibration feature_order ----------------
export interface DspFeatures {
  flat: number;
  cent: number;
  roll: number;
  zcr: number;
  hf: number;
  crest: number;
  jitter: number;
  shimmer: number;
  f0std: number;
  mfcc: number[]; // 13
}

// jitter/shimmer/f0std require Praat (parselmouth) and cannot run in-browser.
// The fusion model assigns them ~0 importance (jitter 0%, f0std 0%,
// shimmer 0.6%), and train.py falls back to these exact constants whenever
// parselmouth is unavailable, so they are safe to hardcode here.
const PRAAT_FALLBACK = { jitter: 0.005, shimmer: 0.05, f0std: 15.0 };

export function extractDspFeatures(y: Float32Array): DspFeatures {
  // flat / cent / roll share the (2048, 512) magnitude STFT.
  const { frames } = stftMagnitude(y, 2048, 512);
  const freqs = fftFrequencies(2048);
  const T = frames.length;

  let flatAcc = 0;
  let centAcc = 0;
  let rollAcc = 0;
  const amin = 1e-10;
  for (let t = 0; t < T; t++) {
    const mag = frames[t];
    // spectral_flatness: power spectrum (mag^2) floored at amin, geo/arith mean
    let logSum = 0;
    let powSum = 0;
    let magSum = 0;
    let centNum = 0;
    for (let k = 0; k < mag.length; k++) {
      const p = Math.max(amin, mag[k] * mag[k]);
      logSum += Math.log(p);
      powSum += p;
      magSum += mag[k];
      centNum += freqs[k] * mag[k];
    }
    const gmean = Math.exp(logSum / mag.length);
    const amean = powSum / mag.length;
    flatAcc += gmean / amean;
    centAcc += magSum > 0 ? centNum / magSum : 0;
    // spectral_rolloff (roll_percent=0.85): first freq where cumsum >= 0.85*total
    const thr = 0.85 * magSum;
    let cum = 0;
    let roll = 0;
    for (let k = 0; k < mag.length; k++) {
      cum += mag[k];
      if (cum >= thr) {
        roll = freqs[k];
        break;
      }
    }
    rollAcc += roll;
  }
  const flat = T ? flatAcc / T : 0;
  const cent = T ? centAcc / T : 0;
  const roll = T ? rollAcc / T : 0;

  // hf ratio: (1024, 256) STFT, S = |stft| + 1e-9, bins with freq > 6000 Hz.
  const { frames: f1024 } = stftMagnitude(y, 1024, 256);
  const freqs1024 = fftFrequencies(1024);
  let hfNum = 0;
  let hfDen = 0;
  for (const mag of f1024) {
    for (let k = 0; k < mag.length; k++) {
      const s = mag[k] + 1e-9;
      hfDen += s;
      if (freqs1024[k] > 6000) hfNum += s;
    }
  }
  const hf = hfDen > 0 ? hfNum / hfDen : 0;

  // zero-crossing rate: frame_length=2048, hop=512, center (edge pad).
  const zcr = zeroCrossingRateMean(y, 2048, 512);

  // rms / crest on the raw (already normalized) signal.
  let sumSq = 0;
  let peak = 0;
  for (let i = 0; i < y.length; i++) {
    sumSq += y[i] * y[i];
    const a = Math.abs(y[i]);
    if (a > peak) peak = a;
  }
  const rms = Math.sqrt(sumSq / y.length + 1e-9);
  const crest = peak / (rms + 1e-9);

  const mfcc = mfccMean(y, 13);

  return { flat, cent, roll, zcr, hf, crest, mfcc, ...PRAAT_FALLBACK };
}

// Matches librosa.feature.zero_crossing_rate: edge-pad by frame_length//2,
// threshold |y|<=1e-10 -> 0, sign via signbit (0 counts as positive),
// pad=False so each frame yields frame_length-1 comparisons.
function zeroCrossingRateMean(y: Float32Array, frameLen: number, hop: number): number {
  const pad = frameLen >> 1; // center=True, pad_mode='edge'
  const get = (i: number) => {
    if (i < pad) return y.length ? y[0] : 0;
    const j = i - pad;
    return j < y.length ? y[j] : y.length ? y[y.length - 1] : 0;
  };
  const total = y.length + 2 * pad;
  const nFrames = 1 + Math.floor(y.length / hop);
  const signbit = (v: number) => (Math.abs(v) <= 1e-10 ? false : v < 0); // 0 -> positive
  let acc = 0;
  for (let t = 0; t < nFrames; t++) {
    const start = t * hop;
    let crossings = 0;
    let prev = signbit(get(start));
    for (let i = 1; i < frameLen; i++) {
      const idx = start + i;
      if (idx >= total) break;
      const s = signbit(get(idx));
      if (s !== prev) crossings++;
      prev = s;
    }
    acc += crossings / (frameLen - 1);
  }
  return nFrames ? acc / nFrames : 0;
}

// Assemble the 23-dim vector in the exact calibration feature_order.
export function featureVectorForFusion(f: DspFeatures, cmScore: number): number[] {
  return [
    f.flat,
    f.cent,
    f.roll,
    f.zcr,
    f.hf,
    f.crest,
    f.jitter,
    f.shimmer,
    f.f0std,
    ...f.mfcc, // mfcc0..mfcc12
    cmScore,
  ];
}

// Linear resample to 16 kHz (librosa.load target sr). Cheap approximation of
// librosa's polyphase resampler; the fusion model's dominant features
// (spectral rolloff / flatness) are robust to the interpolation method.
export function resampleTo16k(samples: Float32Array, fromSr: number): Float32Array {
  if (fromSr === SR) return samples;
  const ratio = SR / fromSr;
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

// Truncate to <=3.5 s and peak-normalize — exactly librosa.load(duration=3.5)
// followed by y /= max(|y|), as done in train.py before every feature call.
export function prepareSignal(samples: Float32Array): Float32Array {
  const maxLen = Math.floor(SR * 3.5);
  const n = Math.min(samples.length, maxLen);
  let peak = 1e-9;
  for (let i = 0; i < n; i++) {
    const a = Math.abs(samples[i]);
    if (a > peak) peak = a;
  }
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = samples[i] / peak;
  return out;
}
