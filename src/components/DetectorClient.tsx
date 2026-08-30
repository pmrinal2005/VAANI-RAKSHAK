"use client";

import { useCallback, useRef, useState } from "react";
import { assess } from "@/lib/detectionEngine";
import { decodeToMono, extractFeatures } from "@/lib/audioFeatures";
import { synthDemo, encodeWav, type DemoKind } from "@/lib/demoSynth";
import { anchorRiskAssessment } from "@/lib/ledger";
import { INDIC_LANGUAGES } from "@/lib/indicRouter";
import type { AudioFeatures, CallContext, RiskAssessment, SpeakerCheck } from "@/lib/types";
import { RiskGauge } from "./RiskGauge";
import { Waveform } from "./Waveform";
import { MelSpectrogram } from "./MelSpectrogram";
import { ShapBars } from "./ShapBars";
import { shortHash } from "@/lib/crypto";

type Enrolled = { name: string; mfcc: number[] };

function cosine(a: number[], b: number[]): number {
  let dot = 0;
  let na = 0;
  let nb = 0;
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  return dot / (Math.sqrt(na) * Math.sqrt(nb) + 1e-9);
}

export function DetectorClient() {
  const [samples, setSamples] = useState<Float32Array | null>(null);
  const [features, setFeatures] = useState<AudioFeatures | null>(null);
  const [result, setResult] = useState<RiskAssessment | null>(null);
  const [busy, setBusy] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [anchored, setAnchored] = useState(false);

  // context controls
  const [ctx, setCtx] = useState<CallContext>({
    channel: "Upload / Softphone",
    aniReputation: 0.6,
    knownContact: true,
    transactionType: "customer-service",
    transactionValueInr: 0,
    timeOfDayRisk: 0.2,
    claimedSpeaker: null,
  });
  const [forceTier2, setForceTier2] = useState(false);
  // operator-selected caller language ("auto" = do not guess / undetermined)
  const [language, setLanguage] = useState<string>("auto");

  // speaker enrollment
  const [enrolled, setEnrolled] = useState<Enrolled | null>(null);

  const mediaRec = useRef<MediaRecorder | null>(null);
  const [recording, setRecording] = useState(false);

  const runFromSamples = useCallback(
    async (wav: Float32Array, sr: number, label?: string) => {
      setBusy(true);
      setError(null);
      setAnchored(false);
      try {
        const feats = extractFeatures(wav, sr);
        setFeatures(feats);

        const speaker: SpeakerCheck = enrolled
          ? (() => {
              const sim = cosine(enrolled.mfcc, feats.mfcc);
              const mismatch = sim < 0.55;
              return {
                enrolled: true,
                claimedSpeaker: enrolled.name,
                cosineSimilarity: Math.round(sim * 1000) / 1000,
                mismatch,
                note: mismatch ? "Voiceprint mismatch" : "Voiceprint consistent",
              };
            })()
          : {
              enrolled: false,
              claimedSpeaker: ctx.claimedSpeaker,
              cosineSimilarity: null,
              mismatch: false,
              note: "No enrolled voiceprint",
            };

        const r = await assess(feats, { ...ctx, claimedSpeaker: enrolled?.name ?? ctx.claimedSpeaker }, speaker, {
          forceTier2,
          language,
        });
        setResult(r);
      } catch (e: any) {
        setError(e?.message ?? String(e));
      } finally {
        setBusy(false);
      }
    },
    [ctx, enrolled, forceTier2, language]
  );

  const handleFile = useCallback(
    async (file: File) => {
      setBusy(true);
      setError(null);
      try {
        const buf = await file.arrayBuffer();
        const { samples: s, sampleRate } = await decodeToMono(buf);
        setSamples(s);
        setAudioUrl(URL.createObjectURL(file));
        await runFromSamples(s, sampleRate, file.name);
      } catch (e: any) {
        setError("Could not decode audio: " + (e?.message ?? e));
        setBusy(false);
      }
    },
    [runFromSamples]
  );

  const loadDemo = useCallback(
    async (kind: DemoKind) => {
      const wav = synthDemo(kind);
      setSamples(wav);
      const blob = encodeWav(wav);
      setAudioUrl(URL.createObjectURL(blob));
      // preset context to make the demo instructive
      if (kind === "cloned") {
        setCtx((c) => ({
          ...c,
          knownContact: false,
          aniReputation: 0.2,
          transactionType: "wire-transfer",
          transactionValueInr: 850000,
          timeOfDayRisk: 0.7,
        }));
      }
      await runFromSamples(wav, 16000, `demo-${kind}`);
    },
    [runFromSamples]
  );

  const startRec = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: BlobPart[] = [];
      const rec = new MediaRecorder(stream);
      rec.ondataavailable = (e) => chunks.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: "audio/webm" });
        setAudioUrl(URL.createObjectURL(blob));
        const buf = await blob.arrayBuffer();
        const { samples: s, sampleRate } = await decodeToMono(buf);
        setSamples(s);
        await runFromSamples(s, sampleRate, "mic-recording");
      };
      mediaRec.current = rec;
      rec.start();
      setRecording(true);
    } catch (e: any) {
      setError("Mic access denied or unavailable: " + (e?.message ?? e));
    }
  }, [runFromSamples]);

  const stopRec = useCallback(() => {
    mediaRec.current?.stop();
    setRecording(false);
  }, []);

  const enrollCurrent = useCallback(() => {
    if (!features) return;
    const name = ctx.claimedSpeaker || "VIP-Speaker";
    setEnrolled({ name, mfcc: features.mfcc });
  }, [features, ctx.claimedSpeaker]);

  const anchor = useCallback(async () => {
    if (!result) return;
    await anchorRiskAssessment(result);
    setAnchored(true);
  }, [result]);

  return (
    <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
      {/* ---------- LEFT: inputs & context ---------- */}
      <aside className="space-y-5">
        <div className="card p-5">
          <h3 className="text-sm font-bold uppercase tracking-wide text-white/50">
            1 · Audio input
          </h3>
          <label className="btn-primary mt-3 w-full cursor-pointer">
            ⬆ Upload audio
            <input
              type="file"
              accept="audio/*"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
          </label>
          <div className="mt-2 flex gap-2">
            {!recording ? (
              <button className="btn-ghost flex-1" onClick={startRec}>
                🎙 Record
              </button>
            ) : (
              <button className="btn flex-1 bg-danger text-white" onClick={stopRec}>
                ■ Stop &amp; analyse
              </button>
            )}
          </div>
          <div className="mt-3">
            <p className="mb-1.5 text-xs text-white/40">Or load a demo profile:</p>
            <div className="grid grid-cols-3 gap-2">
              <button className="btn-ghost !px-2 !text-xs" onClick={() => loadDemo("authentic")}>
                Authentic
              </button>
              <button className="btn-ghost !px-2 !text-xs" onClick={() => loadDemo("borderline")}>
                Borderline
              </button>
              <button className="btn-ghost !px-2 !text-xs" onClick={() => loadDemo("cloned")}>
                Cloned
              </button>
            </div>
          </div>
          {audioUrl && (
            <audio controls src={audioUrl} className="mt-3 w-full" />
          )}
        </div>

        <div className="card p-5">
          <h3 className="text-sm font-bold uppercase tracking-wide text-white/50">
            2 · Call context
          </h3>
          <div className="mt-3 space-y-3 text-sm">
            <Field label="Claimed speaker">
              <input
                className="input"
                placeholder="e.g. CFO / customer"
                value={ctx.claimedSpeaker ?? ""}
                onChange={(e) => setCtx({ ...ctx, claimedSpeaker: e.target.value || null })}
              />
            </Field>
            <Field label="Caller language (LID routing)">
              <select
                className="input"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                <option value="auto">Auto / undetermined (no guessing)</option>
                {INDIC_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.language} ({l.code})
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Transaction type">
              <select
                className="input"
                value={ctx.transactionType}
                onChange={(e) => setCtx({ ...ctx, transactionType: e.target.value })}
              >
                {["customer-service", "wire-transfer", "account-recovery", "kyc-approval", "otp-share", "general"].map(
                  (t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  )
                )}
              </select>
            </Field>
            <Field label={`Transaction value: ₹${ctx.transactionValueInr.toLocaleString("en-IN")}`}>
              <input
                type="range"
                min={0}
                max={5000000}
                step={50000}
                value={ctx.transactionValueInr}
                onChange={(e) => setCtx({ ...ctx, transactionValueInr: +e.target.value })}
                className="w-full"
              />
            </Field>
            <Field label={`ANI/caller reputation: ${(ctx.aniReputation * 100).toFixed(0)}%`}>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={ctx.aniReputation}
                onChange={(e) => setCtx({ ...ctx, aniReputation: +e.target.value })}
                className="w-full"
              />
            </Field>
            <label className="flex items-center gap-2 text-white/70">
              <input
                type="checkbox"
                checked={ctx.knownContact}
                onChange={(e) => setCtx({ ...ctx, knownContact: e.target.checked })}
              />
              Known/registered contact
            </label>
            <label className="flex items-center gap-2 text-white/70">
              <input
                type="checkbox"
                checked={forceTier2}
                onChange={(e) => setForceTier2(e.target.checked)}
              />
              Force deep Tier-2 verification
            </label>
          </div>
        </div>

        <div className="card p-5">
          <h3 className="text-sm font-bold uppercase tracking-wide text-white/50">
            3 · Voiceprint enrollment
          </h3>
          <p className="mt-2 text-xs text-white/45">
            Enroll the current clip as the claimed speaker’s reference embedding
            (ECAPA-TDNN proxy). Only the embedding is stored, never audio.
          </p>
          <button
            className="btn-ghost mt-3 w-full"
            disabled={!features}
            onClick={enrollCurrent}
          >
            ⭐ Enroll current voice
          </button>
          {enrolled && (
            <p className="mt-2 text-xs text-indiagreen">
              ✓ Enrolled: {enrolled.name} ({enrolled.mfcc.length}-d embedding)
            </p>
          )}
        </div>
      </aside>

      {/* ---------- RIGHT: results ---------- */}
      <section className="space-y-5">
        {error && (
          <div className="card border-danger/40 bg-danger/10 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {busy && (
          <div className="card p-8 text-center text-white/60">
            <div className="animate-pulseline text-lg">Running cascade…</div>
          </div>
        )}

        {!result && !busy && (
          <div className="card grid-bg flex min-h-[300px] flex-col items-center justify-center p-8 text-center">
            <div className="text-5xl">🎙️</div>
            <p className="mt-3 max-w-sm text-white/50">
              Load a demo profile or upload a clip to run the full detection cascade.
              Try <b className="text-saffron">Cloned</b> to see a CRITICAL escalation.
            </p>
          </div>
        )}

        {result && !busy && (
          <>
            {/* verdict header */}
            <div className="card p-6">
              <div className="grid items-center gap-6 sm:grid-cols-[220px_1fr]">
                <RiskGauge score={result.riskScore} band={result.band} />
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className="pill text-sm"
                      style={{
                        background:
                          result.verdict === "AUTHENTIC"
                            ? "#22c55e22"
                            : result.verdict === "SUSPICIOUS"
                            ? "#f59e0b22"
                            : result.verdict === "INCONCLUSIVE"
                            ? "#64748b33"
                            : "#ef444422",
                        color:
                          result.verdict === "AUTHENTIC"
                            ? "#22c55e"
                            : result.verdict === "SUSPICIOUS"
                            ? "#f59e0b"
                            : result.verdict === "INCONCLUSIVE"
                            ? "#94a3b8"
                            : "#ef4444",
                      }}
                    >
                      {result.verdict.replace("_", " ")}
                    </span>
                    <span
                      className="pill bg-white/10 text-white/70"
                      title={result.language.note}
                    >
                      🌐 {result.language.detected} · {result.language.adapter}
                      {result.language.source === "undetermined" && " (?)"}
                    </span>
                    <span className="mono pill bg-white/5 text-white/50">
                      ⏱ {result.totalLatencyMs} ms
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-white/75">
                    {result.smartExplanation}
                  </p>
                  {result.requiresOutOfBand && (
                    <div className="mt-3 rounded-xl border border-warn/40 bg-warn/10 p-3 text-sm text-amber-200">
                      ⚠ <b>Out-of-band verification required.</b> Smart-contract policy
                      blocks this {ctx.transactionType} until a second, non-voice channel
                      confirmation (signed email / pre-agreed codeword) is completed.
                    </div>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button className="btn-primary !py-2 !text-xs" onClick={anchor} disabled={anchored}>
                      {anchored ? "✓ Anchored to ledger" : "⛓ Anchor to audit ledger"}
                    </button>
                    <span className="mono pill bg-white/5 text-[10px] text-white/40">
                      feat-hash {shortHash(result.featureHash)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* cascade tiers */}
            <div className="card p-6">
              <h3 className="mb-4 text-sm font-bold uppercase tracking-wide text-white/50">
                Cascade-triage trace
              </h3>
              <div className="space-y-3">
                {result.tiers.map((t) => (
                  <div
                    key={t.tier}
                    className={`flex items-start gap-4 rounded-xl border p-3 ${
                      t.invoked
                        ? "border-white/15 bg-white/5"
                        : "border-white/5 bg-white/[0.02] opacity-60"
                    }`}
                  >
                    <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-ink-700 font-bold">
                      T{t.tier}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-semibold">{t.name}</span>
                        {t.invoked ? (
                          <span className="mono text-xs text-white/50">
                            score {t.score} · {t.latencyMs} ms
                          </span>
                        ) : (
                          <span className="pill bg-emerald-500/15 text-[10px] text-emerald-400">
                            early-exit
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-white/55">{t.reason}</p>
                      {t.invoked && (
                        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${t.score * 100}%`,
                              background: t.score > 0.6 ? "#ef4444" : t.score > 0.35 ? "#f59e0b" : "#22c55e",
                            }}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* votes + shap */}
            <div className="grid gap-5 md:grid-cols-2">
              <div className="card p-6">
                <h3 className="mb-4 text-sm font-bold uppercase tracking-wide text-white/50">
                  Independent signal votes
                </h3>
                <div className="space-y-3">
                  {result.votes.map((v) => (
                    <div key={v.id}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-white/80">{v.label}</span>
                        <span className="mono text-xs text-white/50">
                          {v.score} · w{v.weight}
                        </span>
                      </div>
                      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${v.score * 100}%`,
                            background: v.score > 0.6 ? "#ef4444" : v.score > 0.35 ? "#f59e0b" : "#22c55e",
                          }}
                        />
                      </div>
                      <p className="mt-1 text-[11px] leading-tight text-white/40">{v.detail}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card p-6">
                <h3 className="mb-4 text-sm font-bold uppercase tracking-wide text-white/50">
                  SHAP explanation (why this score)
                </h3>
                <ShapBars shap={result.shap} />
              </div>
            </div>

            {/* visuals */}
            <div className="card p-6">
              <h3 className="mb-4 text-sm font-bold uppercase tracking-wide text-white/50">
                Signal visualisation
              </h3>
              <p className="mb-1.5 text-xs text-white/40">Waveform</p>
              <Waveform samples={samples} />
              <p className="mb-1.5 mt-4 text-xs text-white/40">Mel spectrogram</p>
              <MelSpectrogram samples={samples} />
            </div>

            {/* language distribution */}
            <div className="card p-6">
              <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-white/50">
                Indic LID → LoRA adapter routing
              </h3>
              <p
                className={`mb-3 rounded-lg p-2 text-xs ${
                  result.language.source === "undetermined"
                    ? "bg-white/5 text-white/60"
                    : result.language.source === "user-selected"
                    ? "bg-indiagreen/15 text-emerald-200"
                    : "bg-chakra/15 text-blue-200"
                }`}
              >
                {result.language.source === "undetermined" ? "ℹ️ " : "✓ "}
                {result.language.note}
              </p>
              {result.language.codeSwitching && (
                <p className="mb-3 rounded-lg bg-chakra/20 p-2 text-xs text-blue-200">
                  🔀 Code-switching detected — soft ensemble of top-2 adapters engaged.
                </p>
              )}
              <div className="space-y-2">
                {result.language.distribution.map((d) => (
                  <div key={d.code} className="flex items-center gap-3">
                    <span className="w-32 text-sm text-white/70">
                      {d.language} <span className="mono text-white/40">{d.code}</span>
                    </span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-saffron to-indiagreen"
                        style={{ width: `${d.prob * 100}%` }}
                      />
                    </div>
                    <span className="mono w-12 text-right text-xs text-white/50">
                      {(d.prob * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* raw features */}
            {features && (
              <details className="card p-6">
                <summary className="cursor-pointer text-sm font-bold uppercase tracking-wide text-white/50">
                  Extracted feature vector (edge-computed)
                </summary>
                <div className="mono mt-4 grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-white/60 sm:grid-cols-3">
                  {Object.entries(features)
                    .filter(([, v]) => typeof v === "number")
                    .map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-white/40">{k}</span>
                        <span>{v as number}</span>
                      </div>
                    ))}
                </div>
              </details>
            )}
          </>
        )}
      </section>

      <style jsx>{`
        .input {
          width: 100%;
          border-radius: 0.6rem;
          border: 1px solid rgba(255, 255, 255, 0.12);
          background: rgba(255, 255, 255, 0.04);
          padding: 0.5rem 0.7rem;
          color: white;
          font-size: 0.85rem;
        }
        .input:focus {
          outline: none;
          border-color: rgba(255, 153, 51, 0.6);
        }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs text-white/45">{label}</label>
      {children}
    </div>
  );
}
