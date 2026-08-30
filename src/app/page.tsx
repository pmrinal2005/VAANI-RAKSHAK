import Link from "next/link";

const STATS = [
  { v: "$1.1B", l: "US corporate funds drained by deepfake fraud (2025)" },
  { v: "1,633%", l: "surge in deepfake vishing (Q4’24 → Q1’25)" },
  { v: "62%", l: "of orgs hit by a deepfake attack in 12 months" },
  { v: "42.6%", l: "EER of best open baseline on multilingual audio" },
];

const TIERS = [
  {
    tier: "Tier 0",
    name: "Micro-DSP Pre-Filter",
    lat: "<5 ms · CPU-only",
    desc: "CQCC/LFCC, spectral flatness, phase & HF-cutoff heuristics on every chunk. Discards obvious clean/flagged audio — heavy compute stays near-zero in the median case.",
    color: "from-emerald-500/20 to-emerald-500/5",
  },
  {
    tier: "Tier 1",
    name: "Compact Neural CM",
    lat: "~10 ms · quantised INT8",
    desc: "Distilled AASIST-L graph-attention countermeasure fused with a compact multilingual SSL front-end — near-SOTA spectro-temporal artefact detection on-device (ONNX / TFLite).",
    color: "from-amber-500/20 to-amber-500/5",
  },
  {
    tier: "Tier 2",
    name: "Deep Multilingual SSL",
    lat: "~60 ms · flagged only",
    desc: "Full IndicWav2Vec / XLS-R + AASIST3 with per-language LoRA adapters. Invoked only when lower tiers disagree or the call is high-stakes.",
    color: "from-orange-500/20 to-orange-500/5",
  },
];

const LAYERS = [
  ["🔬", "Multi-Layer Voice Authenticity", "Acoustic + prosody + speaker-embedding — 4 independent votes an attacker must beat simultaneously."],
  ["📊", "Real-Time Risk Scoring", "LightGBM-style fusion → explainable 0–100 impersonation risk with SHAP 'why'."],
  ["🔔", "Alerting & Out-of-Band", "WebSocket/SSE agent alerts + mandatory second-channel confirmation enforced by smart contracts."],
  ["🛡️", "Privacy & Compliance", "Edge-first inference, feature-only logging, federated learning — DPDP/RBI aligned."],
  ["⛓️", "Blockchain Audit", "Hyperledger-Fabric-style tamper-evident ledger of consent, scores & escalations (hashes only)."],
  ["🇮🇳", "Indic Multilingual", "IndicWav2Vec backbone + LoRA adapters for 22 languages, code-switch aware."],
];

export default function Home() {
  return (
    <div className="space-y-16">
      {/* HERO */}
      <section className="relative overflow-hidden rounded-3xl border border-white/10 grid-bg">
        <div className="relative z-10 px-6 py-16 sm:px-12 sm:py-20">
          <span className="pill bg-saffron/15 text-saffron">
            वाणी-रक्षक · Guardian of Voice
          </span>
          <h1 className="mt-5 max-w-3xl text-4xl font-black leading-[1.1] tracking-tight sm:text-6xl">
            Real-time{" "}
            <span className="bg-gradient-to-r from-saffron via-white to-indiagreen bg-clip-text text-transparent">
              voice-cloning
            </span>{" "}
            detection for India — at zero cost.
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-white/60">
            A sophisticated-yet-lightweight <b className="text-white/90">cascade-triage</b>{" "}
            framework that flags AI-cloned voices mid-call, explains{" "}
            <i>why</i>, enforces out-of-band verification, and anchors every decision
            to a tamper-evident consortium ledger — 100% free/open-source, edge-first,
            multilingual.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/detect" className="btn-primary">
              ▶ Launch Live Detector
            </Link>
            <Link href="/architecture" className="btn-ghost">
              Explore the Architecture
            </Link>
            <Link href="/colab" className="btn-ghost">
              Train real models (Colab)
            </Link>
          </div>
        </div>
      </section>

      {/* STATS */}
      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {STATS.map((s) => (
          <div key={s.l} className="card card-hover p-5">
            <div className="text-3xl font-black text-saffron">{s.v}</div>
            <div className="mt-1.5 text-xs leading-snug text-white/50">{s.l}</div>
          </div>
        ))}
      </section>

      {/* CASCADE */}
      <section>
        <h2 className="text-2xl font-bold">The cascade-triage core</h2>
        <p className="mt-2 max-w-2xl text-white/55">
          Not one giant model on every millisecond — a three-tier cascade so expensive
          compute is invoked only when cheap checks are ambiguous. Simultaneously
          high-accuracy and telecom-scale cheap.
        </p>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {TIERS.map((t) => (
            <div
              key={t.tier}
              className={`card card-hover bg-gradient-to-b ${t.color} p-6`}
            >
              <div className="flex items-baseline justify-between">
                <span className="text-xs font-bold uppercase tracking-widest text-white/50">
                  {t.tier}
                </span>
                <span className="mono text-[10px] text-white/40">{t.lat}</span>
              </div>
              <h3 className="mt-2 text-lg font-bold">{t.name}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/60">{t.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* LAYERS */}
      <section>
        <h2 className="text-2xl font-bold">Every required key component, mapped</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {LAYERS.map(([icon, title, desc]) => (
            <div key={title} className="card card-hover p-5">
              <div className="text-2xl">{icon}</div>
              <h3 className="mt-2 font-semibold">{title}</h3>
              <p className="mt-1.5 text-sm text-white/55">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="card overflow-hidden">
        <div className="grid items-center gap-6 p-8 md:grid-cols-[1.4fr_1fr]">
          <div>
            <h2 className="text-2xl font-bold">
              Built on the VCFAD research lineage — extended to production-grade defence.
            </h2>
            <p className="mt-3 text-white/60">
              Inspired by the open Voice-Cloning &amp; Fake-Audio-Detection (mel-spectrogram
              CNN) project, VAANI-RAKSHAK re-architects that single classifier into a
              resilient, multilingual, privacy-preserving, blockchain-audited framework
              addressing the nine persisting gaps in today’s commercial &amp; academic
              solutions.
            </p>
            <Link href="/research" className="btn-ghost mt-5">
              Read the gap analysis →
            </Link>
          </div>
          <ul className="space-y-2 text-sm text-white/70">
            {[
              "IndicWav2Vec + AASIST3 + ECAPA-TDNN",
              "LightGBM fusion + SHAP explanations",
              "Hyperledger-Fabric-style audit chain",
              "Flower federated learning + Opacus DP",
              "FreeSWITCH/Kamailio SIP-native ingest",
              "Vercel-deployed · $0 tech stack",
            ].map((x) => (
              <li key={x} className="flex items-center gap-2">
                <span className="text-indiagreen">✓</span> {x}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
