// ============================================================================
// Isomorphic SHA-256 helpers (Web Crypto in browser, node:crypto on server).
// Used for privacy-preserving feature-vector hashing and the blockchain-anchored
// audit ledger. Raw audio / biometric templates are NEVER hashed or stored —
// only derived, irreversible digests, per DPDP-Act data-minimisation.
// ============================================================================

export async function sha256Hex(input: string): Promise<string> {
  // Browser / edge runtime
  if (typeof globalThis.crypto !== "undefined" && globalThis.crypto.subtle) {
    const data = new TextEncoder().encode(input);
    const digest = await globalThis.crypto.subtle.digest("SHA-256", data);
    return bufToHex(new Uint8Array(digest));
  }
  // Node fallback
  const { createHash } = await import("crypto");
  return createHash("sha256").update(input).digest("hex");
}

function bufToHex(bytes: Uint8Array): string {
  let out = "";
  for (let i = 0; i < bytes.length; i++) {
    out += bytes[i].toString(16).padStart(2, "0");
  }
  return out;
}

/** Short human-friendly digest for UI (first/last 8 hex chars). */
export function shortHash(hex: string): string {
  if (hex.length <= 20) return hex;
  return `${hex.slice(0, 10)}…${hex.slice(-8)}`;
}
