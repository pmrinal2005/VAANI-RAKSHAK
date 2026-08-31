"use client";

import { useEffect, useState } from "react";
import type { LedgerBlock } from "@/lib/types";
import {
  appendBlock,
  ensureGenesis,
  loadChain,
  resetChain,
  tamperChain,
  verifyChain,
} from "@/lib/ledger";
import { shortHash } from "@/lib/crypto";

const TYPE_META: Record<
  LedgerBlock["type"],
  { icon: string; tint: string }
> = {
  GENESIS: { icon: "🌱", tint: "from-indiagreen/20 to-transparent" },
  CONSENT: { icon: "✍️", tint: "from-chakra/25 to-transparent" },
  RISK_SCORE: { icon: "🎯", tint: "from-saffron/20 to-transparent" },
  ESCALATION: { icon: "🚨", tint: "from-danger/25 to-transparent" },
};

export function LedgerClient() {
  const [chain, setChain] = useState<LedgerBlock[]>([]);
  const [busy, setBusy] = useState(false);
  const [verify, setVerify] = useState<{ valid: boolean; brokenAt: number | null } | null>(
    null
  );

  useEffect(() => {
    ensureGenesis().then(setChain);
  }, []);

  const run = async (fn: () => Promise<LedgerBlock[]> | LedgerBlock[]) => {
    setBusy(true);
    setVerify(null);
    try {
      const next = await fn();
      setChain(next);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="card flex flex-wrap items-center gap-3 p-4">
        <button
          className="btn-primary"
          disabled={busy}
          onClick={() =>
            run(() =>
              appendBlock(
                "CONSENT",
                `consent-${Date.now()}`,
                "Caller consent captured — feature-hash only, no raw audio stored.",
                "kyc-desk"
              )
            )
          }
        >
          + Consent block
        </button>
        <button
          className="btn-ghost"
          disabled={busy}
          onClick={() =>
            run(() =>
              appendBlock(
                "ESCALATION",
                `esc-${Date.now()}`,
                "Out-of-band hold fired — wire-transfer blocked pending second-channel confirm.",
                "policy-engine",
                91
              )
            )
          }
        >
          + Escalation block
        </button>
        <button
          className="btn-ghost"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            const v = await verifyChain(chain.length ? chain : loadChain());
            setVerify(v);
            setBusy(false);
          }}
        >
          Verify chain
        </button>
        <button
          className="btn-ghost text-danger"
          disabled={busy}
          onClick={() => {
            setVerify(null);
            setChain(tamperChain());
          }}
        >
          Tamper
        </button>
        <button
          className="btn-ghost"
          disabled={busy}
          onClick={() => {
            resetChain();
            setVerify(null);
            ensureGenesis().then(setChain);
          }}
        >
          Reset
        </button>
        <span className="ml-auto text-xs text-white/40">
          {chain.length} block{chain.length === 1 ? "" : "s"} · SHA-256 · PoW-lite
        </span>
      </div>

      {verify && (
        <div
          className={`card flex items-start gap-3 p-5 ${
            verify.valid ? "border-safe/30" : "border-danger/40"
          }`}
        >
          {verify.valid ? (
            <>
              <span className="text-2xl">🔒</span>
              <p className="text-sm text-white/70">
                Chain valid. All {chain.length} blocks verified — every hash re-derived and every
                prev-link intact. Tamper-evident integrity holds.
              </p>
            </>
          ) : (
            <>
              <span className="text-2xl">💥</span>
              <p className="text-sm text-white/70">
                Tamper detected at block #{verify.brokenAt}. The recomputed hash no longer matches
                — every subsequent block is invalidated. This is the exact guarantee a Fabric
                consortium ledger gives regulators/courts.
              </p>
            </>
          )}
        </div>
      )}

      <div className="space-y-4">
        {chain.map((b, i) => {
          const meta = TYPE_META[b.type] ?? TYPE_META.RISK_SCORE;
          const broken =
            verify && !verify.valid && verify.brokenAt !== null && i >= verify.brokenAt;
          return (
            <div
              key={`${b.index}-${b.hash}`}
              className={`card relative overflow-hidden p-5 ${broken ? "border-danger/50" : ""}`}
            >
              <div
                className={`pointer-events-none absolute inset-0 bg-gradient-to-r ${meta.tint}`}
              />
              <div className="relative">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-lg">
                      {meta.icon}
                    </span>
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-white/40">
                        block #{b.index}
                      </p>
                      <p className="font-semibold">{b.type}</p>
                    </div>
                  </div>
                  <div className="text-right text-xs text-white/40">
                    <p>{new Date(b.timestamp).toLocaleString()}</p>
                    <p>actor: {b.actor}</p>
                  </div>
                </div>

                <p className="mt-3 text-sm text-white/70">{b.summary}</p>
                {typeof b.riskScore === "number" && (
                  <p className="mt-2 text-xs font-semibold text-saffron">
                    risk {b.riskScore}/100
                  </p>
                )}

                <div className="mt-4 grid gap-1 font-mono text-[11px] text-white/40">
                  <span>payload-hash: {shortHash(b.payloadHash)}</span>
                  <span>nonce: {b.nonce}</span>
                  <span>prev: {shortHash(b.prevHash)}</span>
                  <span>hash: {shortHash(b.hash)}</span>
                </div>

                {i < chain.length - 1 && (
                  <p className="mt-3 text-center text-xs text-white/25">↓ links to next</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
