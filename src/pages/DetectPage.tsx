import { DetectorClient } from "@/components/DetectorClient";

export function DetectPage() {
  return (
    <div className="space-y-6">
      <header>
        <p className="mb-2 text-[10px] uppercase tracking-[0.28em] text-white/35">Live Detector</p>
        <h1 className="font-heading text-4xl italic text-white md:text-5xl">
          Catch the clone. Mid-call.
        </h1>
        <p className="mt-3 max-w-3xl font-body text-sm font-light leading-relaxed text-white/55 md:text-base">
          Upload a clip, record from your mic, or load a demo profile. The full cascade runs
          entirely in your browser. Raw audio never leaves your device — only a fused risk score, a
          plain-language why, and an irreversible feature-hash are produced.
        </p>
      </header>
      <DetectorClient />
    </div>
  );
}
