export function RiskGauge({ score, band }: { score: number; band: string }) {
  const radius = 84;
  const circ = Math.PI * radius;
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const dash = circ * pct;
  const color =
    score >= 85 ? "#ef4444" : score >= 65 ? "#f97316" : score >= 40 ? "#f59e0b" : "#22c55e";

  return (
    <div className="flex flex-col items-center">
      <svg width="220" height="130" viewBox="0 0 220 130">
        <path
          d="M26 118 A84 84 0 0 1 194 118"
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d="M26 118 A84 84 0 0 1 194 118"
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
        />
        <text
          x="110"
          y="92"
          textAnchor="middle"
          fill="#fff"
          fontSize="36"
          fontFamily="Instrument Serif, serif"
          fontStyle="italic"
        >
          {score}
        </text>
        <text x="110" y="112" textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="11">
          / 100
        </text>
      </svg>
      <div
        className="mt-1 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]"
        style={{ color, background: `${color}22` }}
      >
        ● {band} RISK
      </div>
    </div>
  );
}
