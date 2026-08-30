"use client";

import type { ShapContribution } from "@/lib/types";

export function ShapBars({ shap }: { shap: ShapContribution[] }) {
  const max = Math.max(...shap.map((s) => Math.abs(s.contribution)), 1);
  return (
    <div className="space-y-2.5">
      {shap.map((s) => {
        const w = (Math.abs(s.contribution) / max) * 100;
        const pos = s.direction === "increases";
        return (
          <div key={s.feature} className="group">
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-white/80">{s.feature}</span>
              <span className={pos ? "text-danger" : "text-safe"}>
                {pos ? "+" : ""}
                {s.contribution}
              </span>
            </div>
            <div className="flex items-center">
              <div className="flex h-2 w-1/2 justify-end">
                {!pos && (
                  <div
                    className="h-2 rounded-l-full bg-safe/70"
                    style={{ width: `${w}%` }}
                  />
                )}
              </div>
              <div className="h-2 w-px bg-white/25" />
              <div className="flex h-2 w-1/2 justify-start">
                {pos && (
                  <div
                    className="h-2 rounded-r-full bg-danger/70"
                    style={{ width: `${w}%` }}
                  />
                )}
              </div>
            </div>
            <p className="mt-0.5 text-[10px] leading-tight text-white/40 opacity-0 transition-opacity group-hover:opacity-100">
              {s.detail}
            </p>
          </div>
        );
      })}
      <div className="flex justify-between pt-1 text-[10px] uppercase tracking-wide text-white/35">
        <span>← lowers risk (authentic)</span>
        <span>raises risk (clone) →</span>
      </div>
    </div>
  );
}
