export const metadata = { title: "Architecture · VAANI-RAKSHAK" };

const COMPONENTS = [
  {
    id: "A",
    title: "Multi-Layer Voice Authenticity Analysis",
    color: "border-saffron/40",
    items: [
      ["Acoustic / spectral layer", "Tier-0 DSP (CQCC/LFCC, flatness, phase, HF-cutoff) + Tier-1/2 neural CM (AASIST-L → IndicWav2Vec+AASIST3) targeting synthesis artefacts, phase inconsistency, unnatural formant transitions."],
      ["Prosody / behavioural layer", "Praat/Parselmouth + openSMILE proxy: F0 contour, jitter, shimmer, pause stats, speech-rate micro-variation. Cheap CPU biomarkers catching over-smooth TTS prosody — an independent second vote."],
      ["Cross-session consistency", "ECAPA-TDNN (SpeechBrain) voiceprint vs an enrolled, encrypted, locally-stored embedding. Catches stolen-but-genuine voice that AI-only detectors miss."],
    ],
  },
  {
    id: "B",
    title: "Real-Time Risk Scoring Engine",
    color: "border-amber-400/40",
    items: [
      ["LightGBM fusion", "Sub-ms gradient-boosted ensemble fuses 4 independent signal streams + call metadata into a continuously-updating 0–100 impersonation risk score."],
      ["SHAP explanations", "Every score carries a human-readable 'why' — giving frontline staff a reason, not just a number."],
      ["Per-workflow thresholds", "Stricter thresholds for wire-transfer / recovery vs general service — layered-defence, never a single gate."],
    ],
  },
  {
    id: "C",
    title: "Alerting & User Interaction Layer",
    color: "border-blue-400/40",
    items: [
      ["Multi-channel push", "WebSocket/SSE to agent desktop (React/Next.js), SMTP email, self-hosted SMS (Kannel/SMPP)."],
      ["Mandatory out-of-band", "Whenever risk crosses threshold, a second non-voice channel (signed email, chat reply, pre-agreed codeword) confirmation is enforced."],
    ],
  },
  {
    id: "D",
    title: "Privacy & Compliance Module",
    color: "border-emerald-400/40",
    items: [
      ["Edge-first inference", "Tier-0/1 run on-device/on-prem (branch server, telecom edge, softphone). Raw audio & most features never leave the perimeter."],
      ["Feature-only logging", "Only fused score, SHAP, and irreversible feature-vector hashes persist centrally — DPDP-Act data-minimisation."],
      ["Federated learning + DP", "Flower framework contributes encrypted gradient updates (never raw voice); Opacus adds differential-privacy guarantees."],
    ],
  },
  {
    id: "E",
    title: "Blockchain-Anchored Audit & Consent",
    color: "border-purple-400/40",
    items: [
      ["Permissioned Hyperledger Fabric", "Consortium of banks, enterprises, telecom operators & regulator/CERT-In. No gas fees, sub-second finality (~284 ms, 3000+ TPS)."],
      ["Hashes only, on-chain", "SHA-256 of consent records, risk-score+explanation packets, and every escalation/override — never raw audio or templates."],
      ["Smart-contract workflow", "'if risk > 85 AND value > ₹X → require two independent out-of-band confirmations before authorised' — policy as enforceable code."],
    ],
  },
  {
    id: "F",
    title: "Platform & Integration APIs",
    color: "border-cyan-400/40",
    items: [
      ["Open protocols", "gRPC + REST via FastAPI for bank/enterprise integration."],
      ["Telecom-native ingest", "FreeSWITCH / Kamailio + RTPengine tap & stream call audio without proprietary middleware."],
      ["Streaming backbone", "Apache Kafka between ingestion → tiers → scoring → alerting; Docker + K3s orchestration on modest on-prem hardware."],
    ],
  },
];

const STACK = [
  ["Backbone / SSL", "IndicWav2Vec (AI4Bharat), XLS-R, wav2vec 2.0"],
  ["Countermeasures", "AASIST, AASIST-L, AASIST3 (KAN), RawNet2"],
  ["Speaker", "ECAPA-TDNN via SpeechBrain"],
  ["Fusion / XAI", "LightGBM + SHAP"],
  ["Prosody", "librosa, Parselmouth (Praat), openSMILE"],
  ["Edge runtime", "ONNX Runtime, TensorFlow Lite (INT8, delegates)"],
  ["Privacy", "Flower (federated), Opacus (DP)"],
  ["Blockchain", "Hyperledger Fabric (permissioned)"],
  ["Telecom", "FreeSWITCH, Kamailio, RTPengine"],
  ["Infra", "Kafka, Docker, K3s, Prometheus, Grafana"],
  ["Frontend", "React / Next.js (this app)"],
  ["Datasets", "IndicSynth, IndicVoices(-R), InDeepFake, ASVspoof"],
];

export default function ArchitecturePage() {
  return (
    <div className="space-y-12">
      <header>
        <h1 className="text-3xl font-black">Architecture Blueprint</h1>
        <p className="mt-2 max-w-3xl text-white/55">
          The full VAANI-RAKSHAK zero-cost framework: cascade-triage detection, four
          independent signal families, explainable fusion, edge-first privacy,
          blockchain audit, and an Indic multilingual shared-backbone + LoRA-adapter
          strategy.
        </p>
      </header>

      {/* cascade diagram */}
      <section className="card overflow-x-auto p-6">
        <h2 className="mb-6 text-xl font-bold">Cascade-triage data flow</h2>
        <div className="flex min-w-[720px] items-stretch gap-3 text-sm">
          <FlowBox title="SIP / RTP ingest" sub="FreeSWITCH · Kamailio" tone="cyan" />
          <Arrow />
          <FlowBox title="Kafka stream" sub="chunked audio" tone="slate" />
          <Arrow />
          <FlowBox title="Tier 0 · DSP" sub="<5ms · every chunk" tone="emerald" />
          <Arrow label="ambiguous" />
          <FlowBox title="Tier 1 · AASIST-L" sub="~10ms · quantised" tone="amber" />
          <Arrow label="disagree / high-stakes" />
          <FlowBox title="Tier 2 · SSL+adapter" sub="~60ms · flagged only" tone="orange" />
          <Arrow />
          <FlowBox title="LightGBM + SHAP" sub="risk 0–100" tone="saffron" />
          <Arrow />
          <FlowBox title="Alert + Ledger" sub="OOB + Fabric hash" tone="purple" />
        </div>
        <p className="mt-4 text-xs text-white/40">
          80–95% of live audio exits at Tier 0/1 → expensive multilingual inference runs
          on a small fraction of segments → telecom-grade real-time on commodity CPUs.
        </p>
      </section>

      {/* components A–F */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold">Key components (mapped to the brief)</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {COMPONENTS.map((c) => (
            <div key={c.id} className={`card border-l-4 ${c.color} p-6`}>
              <h3 className="text-lg font-bold">
                <span className="mono mr-2 text-white/40">{c.id}.</span>
                {c.title}
              </h3>
              <ul className="mt-3 space-y-3">
                {c.items.map(([t, d]) => (
                  <li key={t}>
                    <p className="text-sm font-semibold text-white/85">{t}</p>
                    <p className="text-xs leading-relaxed text-white/55">{d}</p>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* indic strategy */}
      <section className="card p-6">
        <h2 className="text-xl font-bold">🇮🇳 Indian multilingual strategy</h2>
        <p className="mt-2 max-w-3xl text-white/55">
          High accuracy on Indic benchmarks <i>without</i> 22 heavy models — a shared
          backbone + language adapters:
        </p>
        <ol className="mt-4 space-y-3 text-sm text-white/70">
          {[
            ["Shared SSL backbone", "One IndicWav2Vec backbone (all 22 scheduled languages) is the universal Tier-2 feature extractor."],
            ["LID → adapter routing", "IndicLID routes each utterance to the correct few-MB LoRA adapter — not a whole new model."],
            ["Indic spoof fine-tuning", "Adapters validated on IndicSynth (12 langs, 4000+h synthetic), IndicVoices-R (1704h bona-fide), InDeepFake (7 langs, 7 generators)."],
            ["Code-switch handling", "LID outputs a distribution; split confidence triggers a soft ensemble of the top-2 adapters — cheap mixed-language support."],
            ["Cheap dialect growth", "New dialect = a few-MB adapter, not a full multi-hundred-million-parameter retrain."],
          ].map(([t, d], i) => (
            <li key={t} className="flex gap-3">
              <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-saffron/20 text-xs font-bold text-saffron">
                {i + 1}
              </span>
              <span>
                <b className="text-white/90">{t}.</b> {d}
              </span>
            </li>
          ))}
        </ol>
      </section>

      {/* stack table */}
      <section>
        <h2 className="mb-4 text-xl font-bold">100% free/open-source stack</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {STACK.map(([k, v]) => (
            <div key={k} className="card p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-saffron">{k}</p>
              <p className="mt-1 text-sm text-white/70">{v}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function FlowBox({ title, sub, tone }: { title: string; sub: string; tone: string }) {
  const tones: Record<string, string> = {
    cyan: "border-cyan-400/40 bg-cyan-400/5",
    slate: "border-white/15 bg-white/5",
    emerald: "border-emerald-400/40 bg-emerald-400/5",
    amber: "border-amber-400/40 bg-amber-400/5",
    orange: "border-orange-400/40 bg-orange-400/5",
    saffron: "border-saffron/50 bg-saffron/10",
    purple: "border-purple-400/40 bg-purple-400/5",
  };
  return (
    <div className={`flex min-w-[120px] flex-1 flex-col justify-center rounded-xl border p-3 text-center ${tones[tone]}`}>
      <span className="text-xs font-bold text-white/90">{title}</span>
      <span className="mono mt-1 text-[10px] text-white/45">{sub}</span>
    </div>
  );
}

function Arrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center">
      <span className="text-white/30">→</span>
      {label && <span className="mt-0.5 text-[9px] text-white/35">{label}</span>}
    </div>
  );
}
