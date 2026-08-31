// ============================================================================
// Demo audio synthesiser — generates illustrative "authentic" vs "cloned" voice
// clips entirely in-browser so the framework can be exercised with $0 assets.
// ============================================================================

const SR = 16000;

export type DemoKind = "authentic" | "cloned" | "borderline";

function noise() {
  return Math.random() * 2 - 1;
}

/** Build a formant-based vowel-ish tone with optional natural micro-variation. */
export function synthDemo(kind: DemoKind, seconds = 2.2): Float32Array {
  const N = Math.floor(SR * seconds);
  const out = new Float32Array(N);

  const baseF0 = 120 + Math.random() * 40;
  const formants = [700, 1220, 2600];

  const jitterAmt = kind === "authentic" ? 0.03 : kind === "borderline" ? 0.011 : 0.002;
  const shimmerAmt = kind === "authentic" ? 0.18 : kind === "borderline" ? 0.07 : 0.02;
  const hfHiss = kind === "authentic" ? 0.05 : kind === "borderline" ? 0.02 : 0.004;
  const silenceProb = kind === "authentic" ? 0.16 : kind === "borderline" ? 0.09 : 0.03;
  const pitchDriftHz = kind === "authentic" ? 24 : kind === "borderline" ? 9 : 2;

  let phase = 0;
  let f0 = baseF0;
  let ampEnv = 1;
  let silenceUntil = 0;

  for (let i = 0; i < N; i++) {
    const tSec = i / SR;
    if (i > silenceUntil && Math.random() < silenceProb / SR) {
      silenceUntil = i + Math.floor(SR * (0.05 + Math.random() * 0.15));
    }
    if (i < silenceUntil) {
      out[i] = hfHiss * 0.2 * noise();
      continue;
    }

    const drift = (pitchDriftHz / 2) * Math.sin(2 * Math.PI * 0.4 * tSec + 0.9);
    f0 =
      (baseF0 + drift) *
      (1 + jitterAmt * Math.sin(2 * Math.PI * 5 * tSec) + jitterAmt * 0.5 * noise());
    ampEnv =
      (0.6 + 0.4 * Math.sin(2 * Math.PI * 0.7 * tSec)) *
      (1 + shimmerAmt * Math.sin(2 * Math.PI * 8 * tSec) + shimmerAmt * 0.4 * noise());

    phase += (2 * Math.PI * f0) / SR;
    let s = 0;
    for (let h = 1; h <= 12; h++) {
      const fh = f0 * h;
      let gain = 1 / h;
      for (const F of formants) {
        gain *= 1 + 0.9 / (1 + ((fh - F) / 120) ** 2);
      }
      if (kind === "cloned" && fh > 6000) gain *= 0.15;
      if (kind === "borderline" && fh > 7000) gain *= 0.4;
      s += gain * Math.sin(phase * h);
    }
    s = s / 6;
    s += hfHiss * noise();
    out[i] = ampEnv * s * 0.5;
  }

  let max = 1e-9;
  for (let i = 0; i < N; i++) max = Math.max(max, Math.abs(out[i]));
  for (let i = 0; i < N; i++) out[i] /= max;
  return out;
}

/** Encode a Float32 mono waveform to a 16-bit PCM WAV Blob (for playback). */
export function encodeWav(samples: Float32Array, sr = SR): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeStr = (off: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
  };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sr, true);
  view.setUint32(28, sr * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, samples.length * 2, true);
  let off = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    off += 2;
  }
  return new Blob([view], { type: "audio/wav" });
}
