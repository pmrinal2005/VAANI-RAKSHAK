const COMPONENTS = [
  {
    id: "A",
    title: "Multi-Layer Voice Authenticity",
    color: "border-saffron/40",
    items: [
      [
        "Acoustic / spectral layer",
        "A first-pass ear that hears synthesis artefacts, then a neural ear that confirms them — so the clone never hides in the texture of the voice.",
      ],
      [
        "Prosody / behavioural layer",
        "Pitch, tremor, breath, pause. Over-smooth TTS gives itself away. This vote is independent of the spectral one.",
      ],
      [
        "Cross-session consistency",
        "A voiceprint check against the enrolled customer. Catches stolen-but-genuine voice that AI-only detectors miss.",
      ],
    ],
  },
  {
    id: "B",
    title: "Real-Time Risk Scoring",
    color: "border-amber-400/40",
    items: [
      [
        "Explainable fusion",
        "Four independent signals plus call context become a 0–100 impersonation risk — updating as the conversation unfolds.",
      ],
      [
        "A reason, not a number",
        "Every score carries a human-readable why. Frontline staff can act without waiting for a data-science team.",
      ],
      [
        "Per-workflow thresholds",
        "A ₹8 lakh wire is not a balance enquiry. Stricter gates for high-stakes work — layered defence, never a single switch.",
      ],
    ],
  },
  {
    id: "C",
    title: "Alerting & Out-of-Band Hold",
    color: "border-blue-400/40",
    items: [
      [
        "Agent desktop first",
        "The hold lands where the agent already works. No new console. No extra click between ‘suspicious’ and ‘stopped’.",
      ],
      [
        "Mandatory second channel",
        "When risk crosses the line, a signed email, chat reply or pre-agreed codeword is required before money moves.",
      ],
    ],
  },
  {
    id: "D",
    title: "Privacy & Compliance",
    color: "border-emerald-400/40",
    items: [
      [
        "Edge-first inference",
        "The cheap tiers run on-device. Raw audio never leaves the perimeter. DPDP is the architecture, not a policy PDF.",
      ],
      [
        "Feature-only logging",
        "Only the fused score, the why, and an irreversible hash persist. No biometric templates. No voice archive.",
      ],
    ],
  },
  {
    id: "E",
    title: "Blockchain-Anchored Audit",
    color: "border-purple-400/40",
    items: [
      [
        "Permissioned consortium",
        "Banks, telecom, regulator. Hashes only, on-chain. No gas fees. Sub-second finality.",
      ],
      [
        "Policy as code",
        "If risk is high and value is high — two independent confirms. The contract does not blink.",
      ],
    ],
  },
  {
    id: "F",
    title: "Platform & Integration",
    color: "border-cyan-400/40",
    items: [
      [
        "Open protocols",
        "REST and gRPC for banks. SIP/RTP ingest for telecom. No proprietary middleware between the call and the guardian.",
      ],
      [
        "Commodity hardware",
        "Designed for on-prem CPUs. The median call never wakes the expensive model.",
      ],
    ],
  },
];

const STACK = [
  ["Backbone", "IndicWav2Vec · XLS-R · wav2vec 2.0"],
  ["Countermeasures", "AASIST · AASIST-L · AASIST3"],
  ["Speaker", "ECAPA-TDNN"],
  ["Fusion / XAI", "LightGBM + SHAP"],
  ["Edge runtime", "ONNX · TFLite"],
  ["Blockchain", "Hyperledger Fabric-style hash chain"],
  ["Frontend", "React (this app) · fully client-side"],
  ["Datasets", "IndicSynth · IndicVoices-R · InDeepFake · ASVspoof"],
];

export function ArchitecturePage() {
  return (
    <div className="space-y-12">
      <header>
        <p className="mb-2 text-[10px] uppercase tracking-[0.28em] text-white/35">Blueprint</p>
        <h1 className="font-heading text-4xl italic text-white md:text-5xl">
          Sophisticated where it matters. Invisible everywhere else.
        </h1>
        <p className="mt-3 max-w-3xl font-body text-sm font-light text-white/55 md:text-base">
          Cascade-triage detection, four independent signal families, explainable fusion, edge-first
          privacy, blockchain audit, and an Indic multilingual strategy — without 22 heavy models.
        </p>
      </header>

      <section className="card overflow-x-auto p-6">
        <h2 className="mb-6 text-xl font-bold">Cascade-triage data flow</h2>
        <div className="flex min-w-[720px] items-stretch gap-3 text-sm">
          <FlowBox title="SIP / RTP ingest" sub="FreeSWITCH · Kamailio" />
          <Arrow />
          <FlowBox title="Kafka stream" sub="chunked audio" />
          <Arrow />
          <FlowBox title="Tier 0 · DSP" sub="<5ms · every chunk" />
          <Arrow label="ambiguous" />
          <FlowBox title="Tier 1 · AASIST-L" sub="~10ms · on-device" />
          <Arrow label="disagree" />
          <FlowBox title="Tier 2 · SSL" sub="~60ms · flagged only" />
          <Arrow />
          <FlowBox title="SHAP fusion" sub="risk 0–100" />
          <Arrow />
          <FlowBox title="Alert + Ledger" sub="OOB + hash" />
        </div>
        <p className="mt-4 text-xs text-white/40">
          80–95% of live audio exits at Tier 0/1 → expensive multilingual inference runs on a small
          fraction of segments → telecom-grade real-time on commodity CPUs.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold">Key components</h2>
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

      <section className="card p-6">
        <h2 className="text-xl font-bold">🇮🇳 Indian multilingual strategy</h2>
        <p className="mt-2 max-w-3xl text-white/55">
          High accuracy on Indic voice <i>without</i> 22 heavy models — a shared backbone + language
          adapters:
        </p>
        <ol className="mt-4 space-y-3 text-sm text-white/70">
          <li>
            <b>Shared backbone.</b> One IndicWav2Vec model covers all 22 scheduled languages.
          </li>
          <li>
            <b>LID → adapter routing.</b> A few-MB LoRA adapter per language — not a whole new model.
          </li>
          <li>
            <b>Code-switch handling.</b> Split confidence triggers a soft ensemble of the top-2 adapters.
          </li>
          <li>
            <b>Cheap dialect growth.</b> A new dialect is a few megabytes, not a full retrain.
          </li>
        </ol>
      </section>

      <section className="card p-6">
        <h2 className="mb-4 text-xl font-bold">Zero-cost stack</h2>
        <div className="grid gap-2 sm:grid-cols-2">
          {STACK.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 rounded-xl bg-white/5 px-4 py-3 text-sm">
              <span className="text-white/45">{k}</span>
              <span className="text-right text-white/80">{v}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function FlowBox({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="flex min-w-[110px] flex-1 flex-col justify-center rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-center">
      <p className="font-semibold leading-tight">{title}</p>
      <p className="mt-1 text-[10px] text-white/40">{sub}</p>
    </div>
  );
}

function Arrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center text-white/30">
      <span>→</span>
      {label && <span className="max-w-[70px] text-center text-[9px] leading-tight">{label}</span>}
    </div>
  );
}
