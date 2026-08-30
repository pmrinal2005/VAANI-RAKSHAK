import { LedgerClient } from "@/components/LedgerClient";

export const metadata = { title: "Audit Ledger · VAANI-RAKSHAK" };

export default function LedgerPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-black">Blockchain-Anchored Audit Ledger</h1>
        <p className="mt-2 max-w-3xl text-white/55">
          A tamper-evident SHA-256 hash chain modelling the permissioned Hyperledger
          Fabric consortium ledger. Only irreversible hashes of consent records,
          risk-score packets and escalation actions are anchored — never raw audio or
          biometric templates. Try the <b className="text-danger">Tamper</b> button to
          watch chain verification fail.
        </p>
      </header>
      <LedgerClient />
    </div>
  );
}
