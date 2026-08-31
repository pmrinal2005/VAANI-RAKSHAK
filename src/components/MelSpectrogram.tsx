import { useEffect, useRef } from "react";

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
      const mag = new Array(nMels).fill(0);
      for (let m = 0; m < nMels; m++) {
        const lo = Math.floor((m / nMels) * (frameLen / 2));
        const hi = Math.floor(((m + 1) / nMels) * (frameLen / 2));
        let sum = 0;
        for (let k = lo; k < hi; k++) {
          const re = samples[s + k] ?? 0;
          sum += re * re;
        }
        mag[m] = Math.log(sum / Math.max(1, hi - lo) + 1e-9);
      }
      frames.push(mag);
    }
    if (!frames.length) return;

    let min = Infinity;
    let max = -Infinity;
    for (const fr of frames) {
      for (const v of fr) {
        if (v < min) min = v;
        if (v > max) max = v;
      }
    }
    const W = (canvas.width = canvas.clientWidth * 2);
    const H = (canvas.height = canvas.clientHeight * 2);
    const img = ctx.createImageData(W, H);
    for (let x = 0; x < W; x++) {
      const fi = Math.min(frames.length - 1, Math.floor((x / W) * frames.length));
      const fr = frames[fi];
      for (let y = 0; y < H; y++) {
        const mi = Math.min(nMels - 1, Math.floor(((H - 1 - y) / H) * nMels));
        const t = (fr[mi] - min) / (max - min + 1e-9);
        const [r, g, b] = magma(t);
        const i = (y * W + x) * 4;
        img.data[i] = r;
        img.data[i + 1] = g;
        img.data[i + 2] = b;
        img.data[i + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
  }, [samples]);

  return (
    <canvas
      ref={ref}
      className="h-28 w-full rounded-xl bg-black/40"
      style={{ width: "100%", height: "112px" }}
    />
  );
}

function magma(t: number): [number, number, number] {
  t = Math.max(0, Math.min(1, t));
  const r = Math.min(255, Math.floor(255 * Math.pow(t, 0.7)));
  const g = Math.floor(255 * Math.pow(Math.max(0, t - 0.25) / 0.75, 1.4));
  const b = Math.floor(
    255 * (t < 0.5 ? t * 1.6 : Math.max(0, 1 - (t - 0.5) * 1.3)) + 25 * (1 - t)
  );
  return [r, g, Math.min(255, b)];
}
