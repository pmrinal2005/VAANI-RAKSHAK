"use client";

export function RiskGauge({ score, band }: { score: number; band: string }) {
  const radius = 84;
  const circ = Math.PI * radius; // semicircle
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const dash = circ * pct;
  const color =
    score >= 85 ? "#ef4444" : score >= 65 ? "#f97316" : score >= 40 ? "#f59e0b" : "#22c55e";

  return (
    <div className="flex flex-col items-center">
      <svg width="220" height="130" viewBox="0 0 220 130">
        <path
          d="M 20 120 A 90 90 0 0 1 200 120"
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="16"
          strokeLinecap="round"
        />
        <path
          d="M 20 120 A 90 90 0 0 1 200 120"
          fill="none"
          stroke={color}
          strokeWidth="16"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: "stroke-dasharray 0.8s ease, stroke 0.4s" }}
        />
        <text x="110" y="98" textAnchor="middle" className="fill-white" fontSize="40" fontWeight="800">
          {score}
        </text>
        <text x="110" y="118" textAnchor="middle" fill="rgba(255,255,255,0.45)" fontSize="12">
          / 100
        </text>
      </svg>
      <span
        className="pill mt-1"
        style={{ background: `${color}22`, color, border: `1px solid ${color}55` }}
      >
        ● {band} RISK
      </span>
    </div>
  );
}
