"use client";

import { useCallback, useEffect, useState } from "react";
import {
  appendBlock,
  ensureGenesis,
  loadChain,
  resetChain,
  verifyChain,
} from "@/lib/ledger";
import type { LedgerBlock } from "@/lib/types";
import { shortHash } from "@/lib/crypto";

const TYPE_META: Record<string, { icon: string; color: string }> = {
  GENESIS: { icon: "🌱", color: "#94a3b8" },
  CONSENT: { icon: "✍️", color: "#22c55e" },
  RISK_SCORE: { icon: "📊", color: "#f59e0b" },
  ESCALATION: { icon: "🚨", color: "#ef4444" },
};

export function LedgerClient() {
  const [chain, setChain] = useState<LedgerBlock[]>([]);
  const [verify, setVerify] = useState<{ valid: boolean; brokenAt: number | null } | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const c = await ensureGenesis();
    setChain(c);
    setVerify(await verifyChain(c));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const add = useCallback(
    async (type: LedgerBlock["type"], summary: string, payload: string, actor: string, risk?: number) => {
      setBusy(true);
      const c = await appendBlock(type, payload, summary, actor, risk);
      setChain(c);
      setVerify(await verifyChain(c));
      setBusy(false);
    },
    []
  );

  const tamper = useCallback(async () => {
    if (chain.length < 2) return;
    // mutate a middle block's summary WITHOUT recomputing hash → chain breaks
    const idx = Math.floor(chain.length / 2);
    const mutated = chain.map((b, i) =>
      i === idx ? { ...b, summary: b.summary + " [ILLEGALLY EDITED]", riskScore: 1 } : b
    );
    window.localStorage.setItem("vaani_ledger_v1", JSON.stringify(mutated));
    setChain(mutated);
    setVerify(await verifyChain(mutated));
  }, [chain]);

  const reset = useCallback(async () => {
    resetChain();
    await refresh();
  }, [refresh]);

  return (
    <div className="space-y-6">
      {/* controls */}
      <div className="card p-5">
        <div className="flex flex-wrap items-center gap-2">
          <button
            className="btn-ghost !text-xs"
            disabled={busy}
            onClick={() =>
              add(
                "CONSENT",
                "Voiceprint enrollment consent recorded for VIP speaker",
                JSON.stringify({ consentId: crypto.randomUUID(), scope: "voiceprint-enroll", ts: Date.now() }),
                "customer-node"
              )
            }
          >
            ✍️ Record consent
          </button>
          <button
            className="btn-ghost !text-xs"
            disabled={busy}
            onClick={() =>
              add(
                "RISK_SCORE",
                `Risk packet anchored · score ${40 + Math.floor(Math.random() * 55)}/100`,
                JSON.stringify({ featureHash: crypto.randomUUID(), ts: Date.now() }),
                "detection-node",
                40 + Math.floor(Math.random() * 55)
              )
            }
          >
            📊 Anchor risk score
          </button>
          <button
            className="btn-ghost !text-xs"
            disabled={busy}
            onClick={() =>
              add(
                "ESCALATION",
                "Out-of-band confirmation completed · fund-transfer authorised by 2 channels",
                JSON.stringify({ action: "OOB-2FA", approver: "branch-mgr", ts: Date.now() }),
                "workflow-contract"
              )
            }
          >
            🚨 Log escalation
          </button>
          <div className="mx-2 h-6 w-px bg-white/15" />
          <button className="btn !text-xs bg-danger text-white" onClick={tamper}>
            ⚠ Tamper with a block
          </button>
          <button className="btn-ghost !text-xs" onClick={reset}>
            ↺ Reset chain
          </button>
        </div>

        {/* verification banner */}
        {verify && (
          <div
            className={`mt-4 flex items-center gap-3 rounded-xl border p-3 text-sm ${
              verify.valid
                ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-200"
                : "border-danger/50 bg-danger/10 text-red-200"
            }`}
          >
            {verify.valid ? (
              <>
                <span className="text-lg">🔒</span>
                <span>
                  <b>Chain valid.</b> All {chain.length} blocks verified — every hash
                  re-derived and every prev-link intact. Tamper-evident integrity holds.
                </span>
              </>
            ) : (
              <>
                <span className="text-lg">💥</span>
                <span>
                  <b>Tamper detected at block #{verify.brokenAt}.</b> The recomputed hash
                  no longer matches — every subsequent block is invalidated. This is the
                  exact guarantee a Fabric consortium ledger gives regulators/courts.
                </span>
              </>
            )}
          </div>
        )}
      </div>

      {/* chain */}
      <div className="space-y-3">
        {chain.map((b, i) => {
          const meta = TYPE_META[b.type] ?? TYPE_META.RISK_SCORE;
          const broken = verify && !verify.valid && verify.brokenAt !== null && i >= verify.brokenAt;
          return (
            <div
              key={b.index}
              className={`card p-5 ${broken ? "border-danger/50 bg-danger/5" : ""}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <span
                    className="flex h-10 w-10 items-center justify-center rounded-xl text-lg"
                    style={{ background: `${meta.color}22` }}
                  >
                    {meta.icon}
                  </span>
                  <div>
                    <span className="mono text-xs text-white/40">block #{b.index}</span>
                    <p className="text-sm font-semibold" style={{ color: meta.color }}>
                      {b.type}
                    </p>
                  </div>
                </div>
                <div className="text-right text-xs text-white/40">
                  <p className="mono">{new Date(b.timestamp).toLocaleString()}</p>
                  <p>actor: {b.actor}</p>
                </div>
              </div>

              <p className="mt-3 text-sm text-white/75">{b.summary}</p>
              {typeof b.riskScore === "number" && (
                <span className="pill mt-2 bg-white/10 text-xs text-white/60">
                  risk {b.riskScore}/100
                </span>
              )}

              <div className="mono mt-3 grid gap-1 text-[11px] text-white/40 sm:grid-cols-2">
                <div>payload-hash: {shortHash(b.payloadHash)}</div>
                <div>nonce: {b.nonce}</div>
                <div>prev: {shortHash(b.prevHash)}</div>
                <div className={broken ? "text-danger" : "text-emerald-400/80"}>
                  hash: {shortHash(b.hash)}
                </div>
              </div>

              {i < chain.length - 1 && (
                <div className="mt-2 flex justify-center text-white/20">↓ links to next</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
