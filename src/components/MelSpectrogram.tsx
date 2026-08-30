"use client";

import { useEffect, useRef } from "react";

/** Compute a coarse log-mel spectrogram from a waveform and render as heatmap. */
export function MelSpectrogram({ samples }: { samples: Float32Array | null }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !samples) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const nMels = 48;
    const frameLen = 512;
    const hop = 256;
    const frames: number[][] = [];
    for (let s = 0; s + frameLen < samples.length; s += hop) {
      const spec = new Array(frameLen / 2).fill(0);
      // cheap magnitude via Goertzel-ish sampled bins
      for (let k = 0; k < frameLen / 2; k += 1) {
        let re = 0;
        let im = 0;
        const kk = k;
        for (let n = 0; n < frameLen; n += 2) {
          const ang = (-2 * Math.PI * kk * n) / frameLen;
          const v = samples[s + n];
          re += v * Math.cos(ang);
          im += v * Math.sin(ang);
        }
        spec[k] = Math.sqrt(re * re + im * im);
      }
      // fold into mel bands (log)
      const band: number[] = [];
      const per = Math.floor(spec.length / nMels);
      for (let m = 0; m < nMels; m++) {
        let e = 0;
        for (let j = m * per; j < (m + 1) * per; j++) e += spec[j];
        band.push(Math.log(e + 1e-6));
      }
      frames.push(band);
    }
    if (frames.length === 0) return;

    let mn = Infinity;
    let mx = -Infinity;
    for (const fr of frames)
      for (const v of fr) {
        mn = Math.min(mn, v);
        mx = Math.max(mx, v);
      }

    const W = (canvas.width = frames.length);
    const H = (canvas.height = nMels);
    const img = ctx.createImageData(W, H);
    for (let x = 0; x < W; x++) {
      for (let y = 0; y < H; y++) {
        const v = (frames[x][nMels - 1 - y] - mn) / (mx - mn + 1e-9);
        const [r, g, b] = magma(v);
        const idx = (y * W + x) * 4;
        img.data[idx] = r;
        img.data[idx + 1] = g;
        img.data[idx + 2] = b;
        img.data[idx + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
  }, [samples]);

  return (
    <canvas
      ref={ref}
      className="h-40 w-full rounded-xl border border-white/10 bg-ink-900/60"
      style={{ imageRendering: "pixelated" }}
    />
  );
}

// Magma-ish colormap
function magma(t: number): [number, number, number] {
  t = Math.max(0, Math.min(1, t));
  const r = Math.min(255, Math.floor(255 * Math.pow(t, 0.7)));
  const g = Math.floor(255 * Math.pow(Math.max(0, t - 0.25) / 0.75, 1.4));
  const b = Math.floor(
    255 * (t < 0.5 ? t * 1.6 : Math.max(0, 1 - (t - 0.5) * 1.3)) + 25 * (1 - t)
  );
  return [r, g, Math.min(255, b)];
}
