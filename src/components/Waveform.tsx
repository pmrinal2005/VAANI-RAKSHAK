"use client";

import { useEffect, useRef } from "react";

export function Waveform({ samples }: { samples: Float32Array | null }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !samples) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const W = (canvas.width = canvas.clientWidth * 2);
    const H = (canvas.height = canvas.clientHeight * 2);
    ctx.clearRect(0, 0, W, H);

    const step = Math.max(1, Math.floor(samples.length / W));
    const mid = H / 2;
    const grad = ctx.createLinearGradient(0, 0, W, 0);
    grad.addColorStop(0, "#ff9933");
    grad.addColorStop(1, "#138808");
    ctx.strokeStyle = grad;
    ctx.fillStyle = "rgba(255,153,51,0.12)";
    ctx.lineWidth = 1.5;

    ctx.beginPath();
    ctx.moveTo(0, mid);
    for (let x = 0; x < W; x++) {
      let min = 1;
      let max = -1;
      for (let j = 0; j < step; j++) {
        const v = samples[x * step + j] ?? 0;
        if (v < min) min = v;
        if (v > max) max = v;
      }
      ctx.lineTo(x, mid + max * mid * 0.9);
    }
    for (let x = W - 1; x >= 0; x--) {
      let min = 1;
      for (let j = 0; j < step; j++) {
        const v = samples[x * step + j] ?? 0;
        if (v < min) min = v;
      }
      ctx.lineTo(x, mid + min * mid * 0.9);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }, [samples]);

  return (
    <canvas
      ref={ref}
      className="h-24 w-full rounded-xl border border-white/10 bg-ink-900/60"
    />
  );
}
