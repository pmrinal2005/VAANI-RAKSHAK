// ============================================================================
// VAANI-RAKSHAK — Blockchain-Anchored Audit & Consent Ledger
// Tamper-evident SHA-256 hash chain modelling a permissioned consortium ledger.
// ============================================================================

import type { LedgerBlock, RiskAssessment } from "./types";
import { sha256Hex } from "./crypto";

const STORAGE_KEY = "vaani_ledger_v1";
const DIFFICULTY = 3;

async function computeHash(b: Omit<LedgerBlock, "hash">): Promise<string> {
  const material = `${b.index}|${b.timestamp}|${b.type}|${b.payloadHash}|${b.summary}|${b.actor}|${b.prevHash}|${b.nonce}`;
  return sha256Hex(material);
}

async function mine(b: Omit<LedgerBlock, "hash" | "nonce">): Promise<LedgerBlock> {
  let nonce = 0;
  const prefix = "0".repeat(DIFFICULTY);
  for (; nonce < 250000; nonce++) {
    const candidate: Omit<LedgerBlock, "hash"> = { ...b, nonce };
    const hash = await computeHash(candidate);
    if (hash.startsWith(prefix)) return { ...candidate, hash };
  }
  const fallback: Omit<LedgerBlock, "hash"> = { ...b, nonce };
  return { ...fallback, hash: await computeHash(fallback) };
}

export function loadChain(): LedgerBlock[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as LedgerBlock[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveChain(chain: LedgerBlock[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(chain));
}

export async function ensureGenesis(): Promise<LedgerBlock[]> {
  let chain = loadChain();
  if (chain.length === 0) {
    const genesis = await mine({
      index: 0,
      timestamp: Date.now(),
      type: "GENESIS",
      payloadHash: await sha256Hex("VAANI-RAKSHAK-GENESIS"),
      summary: "Consortium genesis block (banks · telecom · regulator/CERT-In nodes).",
      actor: "consortium",
      prevHash: "0".repeat(64),
    });
    chain = [genesis];
    saveChain(chain);
  }
  return chain;
}

export async function appendBlock(
  type: LedgerBlock["type"],
  payloadPlaintext: string,
  summary: string,
  actor: string,
  riskScore?: number
): Promise<LedgerBlock[]> {
  const chain = await ensureGenesis();
  const prev = chain[chain.length - 1];
  const block = await mine({
    index: chain.length,
    timestamp: Date.now(),
    type,
    payloadHash: await sha256Hex(payloadPlaintext),
    summary,
    actor,
    prevHash: prev.hash,
    riskScore,
  });
  const next = [...chain, block];
  saveChain(next);
  return next;
}

export async function anchorRiskAssessment(a: RiskAssessment): Promise<LedgerBlock[]> {
  const payload = JSON.stringify({
    featureHash: a.featureHash,
    risk: a.riskScore,
    verdict: a.verdict,
    lang: a.language.code,
    explanation: a.smartExplanation,
    ts: a.timestamp,
  });
  return appendBlock(
    "RISK_SCORE",
    payload,
    `Risk packet anchored · ${a.verdict} · score ${a.riskScore}/100 · ${a.language.detected}`,
    "detection-node",
    a.riskScore
  );
}

export async function verifyChain(
  chain: LedgerBlock[]
): Promise<{ valid: boolean; brokenAt: number | null }> {
  for (let i = 0; i < chain.length; i++) {
    const b = chain[i];
    const recomputed = await computeHash({
      index: b.index,
      timestamp: b.timestamp,
      type: b.type,
      payloadHash: b.payloadHash,
      summary: b.summary,
      riskScore: b.riskScore,
      actor: b.actor,
      prevHash: b.prevHash,
      nonce: b.nonce,
    });
    if (recomputed !== b.hash) return { valid: false, brokenAt: i };
    if (i > 0 && b.prevHash !== chain[i - 1].hash) return { valid: false, brokenAt: i };
  }
  return { valid: true, brokenAt: null };
}

export function resetChain() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

/** Mutate a non-genesis block so verification fails — demo of tamper evidence. */
export function tamperChain(): LedgerBlock[] {
  const chain = loadChain();
  if (chain.length < 2) return chain;
  const idx = Math.max(1, chain.length - 1);
  chain[idx] = {
    ...chain[idx],
    summary: chain[idx].summary + " ⚠ TAMPERED",
    hash: chain[idx].hash.replace(/0/g, "f").replace(/a/g, "0"),
  };
  saveChain(chain);
  return chain;
}
