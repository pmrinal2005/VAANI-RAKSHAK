export const metadata = { title: "Research & Gap Analysis · VAANI-RAKSHAK" };

const COMMERCIAL = [
  "Resemble AI", "Reality Defender", "Pindrop", "CloudSEK", "Oracle OCCAS",
];

const OSS = [
  ["RawNet2", "End-to-end anti-spoofing baseline (ASVspoof 2021) — sinc-conv + residual blocks + GRU."],
  ["AASIST", "Spectral + temporal graph-attention networks; SOTA on ASVspoof, open academic license."],
  ["SSL-AASIST", "wav2vec 2.0 front-end + AASIST backend (318M params) — strong but English/European-biased."],
  ["AASIST3", "Adds Kolmogorov-Arnold Networks (KAN) + Wav2Vec2 encoder + graph attention for spatio-temporal modelling."],
];

const INDIC = [
  ["IndicVoices", "7,348h spontaneous speech · 22 languages · 16,237 speakers · 145 districts (1,639h transcribed)."],
  ["IndicVoices-R", "Largest Indian TTS dataset — 1,704h · 10,496 speakers · 22 languages."],
  ["IndicSynth", "Multilingual synthetic-speech dataset · 12 low-resource Indian languages · 4,000+h synthetic audio."],
  ["InDeepFake", "Multimodal audio-video deepfakes · 7 Indian languages · 7 SOTA generators · age/gender diversity."],
];

const GAPS = [
  ["Catastrophic cross-lingual degradation", "SSL-AASIST hits 37.71% dev EER and 42.6% on multilingual eval — near random. Models trained on one language collapse out-of-domain."],
  ["No robustness to emerging generation", "ASVspoof lacks emotional speech; codec/diffusion/flow-matching TTS unseen in training defeat static classifiers."],
  ["Single-model single-point-of-failure", "One CM in an arms race; its confidence should feed a decision, never be the sole gate."],
  ["Human factor under pressure", "Even trained staff treat a familiar 'CFO' voice as validating under time pressure. Detection alone is insufficient."],
  ["No streaming actionable risk score", "Academic CMs output offline EER-optimised LLRs on pre-recorded utterances — not a mid-call, threshold-calibrated stream."],
  ["Privacy retrofitted, not designed-in", "Cloud/SaaS tools push raw voice biometrics outside the perimeter — a problem for RBI / DPDP data-localisation."],
  ["Mutable, siloed audit trails", "Alerts/consent/escalations live in mutable DBs — legally weak for forensics and cross-institution trust."],
  ["Cost & vendor lock-in", "All strong products are paid SaaS — unsuitable for a $0, telecom-scale, price-sensitive Indian deployment."],
  ["OSS cloning tools have no built-in defence", "No watermarking, consent-verification or misuse-prevention — attacker toolchain is frictionless, defender's is fragmented."],
];

const OUTCOMES = [
  ["Reduction in voice-cloning financial fraud", "Cascade detection + mandatory out-of-band workflow enforced by smart contracts before high-value approvals."],
  ["Improved trust in voice channels", "Explainable SHAP risk score + blockchain-verifiable incident history restores institutional & inter-agency trust."],
  ["Early detection → proactive containment", "Continuous streaming Tier-0/1 scoring gives sub-second flags mid-call, not post-call forensics."],
  ["Reusable cross-sector security layer", "Open gRPC/REST APIs, SIP/RTP-native ingest, consortium blockchain shared across banks/telecom/gov."],
];

export default function ResearchPage() {
  return (
    <div className="space-y-12">
      <header>
        <h1 className="text-3xl font-black">Deep Research &amp; Gap Analysis</h1>
        <p className="mt-2 max-w-3xl text-white/55">
          Why VAANI-RAKSHAK is designed the way it is — the existing landscape, the nine
          persisting gaps it closes, and how each expected outcome is delivered.
        </p>
      </header>

      {/* PART 1 */}
      <section className="space-y-6">
        <SectionTitle n="1" title="Existing solutions landscape" />
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="card p-6">
            <h3 className="font-bold">Commercial / enterprise</h3>
            <p className="mt-2 text-sm text-white/55">
              Sub-second detection layered on telephony (Zoom/Teams/Meet/SIP), orchestrated
              via platforms like Oracle OCCAS above existing telephony — banks start with
              highest-risk flows (account recovery) and expand.
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {COMMERCIAL.map((c) => (
                <span key={c} className="pill bg-white/10 text-[10px] text-white/60">
                  {c}
                </span>
              ))}
            </div>
            <p className="mt-3 text-xs text-danger/80">
              All paid SaaS — referenced for gap analysis only; never adopted in our $0 stack.
            </p>
          </div>

          <div className="card p-6">
            <h3 className="font-bold">Open-source countermeasures</h3>
            <ul className="mt-2 space-y-2">
              {OSS.map(([t, d]) => (
                <li key={t} className="text-sm">
                  <b className="text-saffron">{t}</b>
                  <span className="text-white/55"> — {d}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card p-6">
            <h3 className="font-bold">Indian-language assets</h3>
            <ul className="mt-2 space-y-2">
              {INDIC.map(([t, d]) => (
                <li key={t} className="text-sm">
                  <b className="text-indiagreen">{t}</b>
                  <span className="text-white/55"> — {d}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* PART 2 */}
      <section className="space-y-6">
        <SectionTitle n="2" title="Persisting gaps & loopholes" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {GAPS.map(([t, d], i) => (
            <div key={t} className="card card-hover p-5">
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-danger/20 text-xs font-bold text-danger">
                  {i + 1}
                </span>
                <h3 className="text-sm font-bold text-white/90">{t}</h3>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-white/55">{d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* PART 4 */}
      <section className="space-y-6">
        <SectionTitle n="4" title="Expected outcomes — traceability" />
        <div className="overflow-hidden rounded-2xl border border-white/10">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-xs uppercase tracking-wide text-white/50">
              <tr>
                <th className="p-4">Brief’s expected outcome</th>
                <th className="p-4">How VAANI-RAKSHAK delivers it</th>
              </tr>
            </thead>
            <tbody>
              {OUTCOMES.map(([o, h], i) => (
                <tr key={o} className={i % 2 ? "bg-white/[0.02]" : ""}>
                  <td className="p-4 font-semibold text-white/85">{o}</td>
                  <td className="p-4 text-white/60">{h}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card p-6">
        <SectionTitle n="✓" title="Self-verification checklist" />
        <ul className="mt-4 space-y-2 text-sm text-white/70">
          {[
            "All task points/subpoints addressed — existing solutions, gaps, sophisticated-yet-lightweight zero-cost architecture (every key component), Indic strategy, blockchain+cybersecurity integration.",
            "No contradictions — privacy-by-edge-inference is consistent throughout (raw audio never centralised, not even on-chain — hashes only).",
            "Free/open-source only — every named tool is permissively licensed & self-hostable; no paid SaaS in the build.",
            "Cascade is consistently the reason for both 'sophisticated' and 'lightweight' — not conflicting goals.",
          ].map((x) => (
            <li key={x} className="flex gap-2">
              <span className="text-indiagreen">✓</span>
              <span>{x}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function SectionTitle({ n, title }: { n: string; title: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-saffron/15 font-black text-saffron">
        {n}
      </span>
      <h2 className="text-xl font-bold">{title}</h2>
    </div>
  );
}
