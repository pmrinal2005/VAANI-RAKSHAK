import { Link } from "react-router-dom";

export function ResearchPage() {
  return (
    <div className="space-y-10">
      <header>
        <p className="mb-2 text-[10px] uppercase tracking-[0.28em] text-white/35">
          Deep Research
        </p>
        <h1 className="font-heading text-4xl italic text-white md:text-5xl">
          The clone is already on the line.
        </h1>
        <p className="mt-3 max-w-3xl font-body text-sm font-light text-white/55 md:text-base">
          Voice-cloning fraud is not a future risk. It is a present one — and Indian banks and
          telecoms are the richest hunting ground. This is the landscape, the gap, and the
          architecture that closes it.
        </p>
      </header>

      <article className="card space-y-4 p-6">
        <h2 className="text-xl font-bold">Part 1 · The landscape</h2>
        <p className="text-sm leading-relaxed text-white/65">
          A cloned voice can pass a human ear, a call-centre script, and often a speaker-ID check
          that was never designed for generative audio. Vishing that once needed an actor now needs
          a thirty-second sample from a WhatsApp forward. The victim hears their relationship
          manager. The money leaves in a wire.
        </p>
        <p className="text-sm leading-relaxed text-white/65">
          Commercial detectors exist — and they are expensive, English-first, cloud-hosted, and
          silent on <i>why</i>. Indian languages, code-switching, and DPDP data-localisation are
          treated as afterthoughts. That is the gap VAANI-RAKSHAK was built to occupy.
        </p>
      </article>

      <article className="card space-y-4 p-6">
        <h2 className="text-xl font-bold">Part 2 · The gap</h2>
        <ul className="list-disc space-y-2 pl-5 text-sm text-white/65">
          <li>Cloud-only inference ships raw voice off-device — a DPDP non-starter.</li>
          <li>English-centric models collapse across Indic languages (~42% EER in published multilingual stress tests).</li>
          <li>Black-box scores cannot be defended to an auditor, a court, or a frontline agent.</li>
          <li>Paid SaaS (Pindrop, Reality Defender, Resemble Detect) breaks the $0 mandate for public-sector and rural banks.</li>
        </ul>
      </article>

      <article className="card space-y-4 p-6">
        <h2 className="text-xl font-bold">Part 3 · The architecture</h2>
        <p className="text-sm leading-relaxed text-white/65">
          Cascade-triage, not brute force. Cheap DSP on every chunk. A compact neural
          countermeasure when the cheap check is unsure. A deep multilingual verifier only when the
          call is high-stakes or the cheaper ears disagree. Four independent votes, fused with a
          reason. Out-of-band hold. A hash-chain ledger.
        </p>
        <p className="text-sm leading-relaxed text-white/65">
          One IndicWav2Vec backbone. Per-language LoRA adapters of a few megabytes. Code-switch
          handled as a distribution, not a guess.{" "}
          <Link to="/architecture" className="text-saffron hover:underline">
            Full blueprint →
          </Link>
        </p>
      </article>

      <article className="card space-y-4 p-6">
        <h2 className="text-xl font-bold">Part 4 · Outcomes we hold ourselves to</h2>
        <ul className="list-disc space-y-2 pl-5 text-sm text-white/65">
          <li>Authentic voices stay authentic — no false alarm on a real customer.</li>
          <li>Cloned voices are decisive, not “maybe” — especially on high-value wires.</li>
          <li>Language is never fabricated. If we cannot know, we say so.</li>
          <li>Unusable audio is INCONCLUSIVE, never a confident wrong call.</li>
          <li>The public demo runs at $0, fully client-side. The Colab notebook trains the real models.</li>
        </ul>
      </article>

      <article className="card border-indiagreen/30 bg-indiagreen/5 p-6">
        <h2 className="text-lg font-bold">Core philosophy</h2>
        <p className="mt-2 text-sm leading-relaxed text-white/65">
          Rather than running one giant multilingual model on every millisecond, a three-tier
          cascade invokes heavy compute only when cheap checks are ambiguous — 80–95% of live audio
          exits at Tier 0/1. The system is simultaneously sophisticated (deep models on demand) and
          lightweight (median-case compute near-zero, telecom-grade on commodity CPUs).
        </p>
      </article>
    </div>
  );
}
