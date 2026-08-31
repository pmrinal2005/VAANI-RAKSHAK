import { LedgerClient } from "@/components/LedgerClient";

export function LedgerPage() {
  return (
    <div className="space-y-6">
      <header>
        <p className="mb-2 text-[10px] uppercase tracking-[0.28em] text-white/35">Audit Ledger</p>
        <h1 className="font-heading text-4xl italic text-white md:text-5xl">
          A trail no attacker can rewrite.
        </h1>
        <p className="mt-3 max-w-3xl font-body text-sm font-light leading-relaxed text-white/55 md:text-base">
          A tamper-evident SHA-256 hash chain modelling the permissioned consortium ledger. Only
          irreversible hashes of consent, risk packets and escalations are anchored — never raw
          audio. Hit <b className="text-danger">Tamper</b> and watch verification fail.
        </p>
      </header>
      <LedgerClient />
    </div>
  );
}
