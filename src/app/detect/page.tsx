import { DetectorClient } from "@/components/DetectorClient";

export const metadata = { title: "Live Detector · VAANI-RAKSHAK" };

export default function DetectPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-black">Live Voice-Cloning Detector</h1>
        <p className="mt-2 max-w-3xl text-white/55">
          Upload a clip, record from your mic, or load a demo profile. The full
          cascade — DSP → neural CM → deep SSL — runs <b>entirely in your browser</b>.
          Raw audio never leaves your device; only the fused risk score, SHAP
          explanation and an irreversible feature-hash are produced.
        </p>
      </header>
      <DetectorClient />
    </div>
  );
}
