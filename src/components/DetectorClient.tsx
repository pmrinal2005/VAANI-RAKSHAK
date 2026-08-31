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
import { Mic, ShieldAlert, Sparkles, Upload, UserPlus, Link2 } from "lucide-react";

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

const TXN_TYPES = [
  "customer-service",
  "kyc",
  "otp",
  "wire-transfer",
  "recovery",
  "approval",
];

export function DetectorClient() {
  const [samples, setSamples] = useState<Float32Array | null>(null);
  const [features, setFeatures] = useState<AudioFeatures | null>(null);
  const [result, setResult] = useState<RiskAssessment | null>(null);
  const [busy, setBusy] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [anchored, setAnchored] = useState(false);
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
  const [language, setLanguage] = useState("auto");
  const [enrolled, setEnrolled] = useState<Enrolled | null>(null);
  const mediaRec = useRef<MediaRecorder | null>(null);
  const [recording, setRecording] = useState(false);

  const runFromSamples = useCallback(
    async (wav: Float32Array, sr: number) => {
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

        const r = await assess(
          feats,
          { ...ctx, claimedSpeaker: enrolled?.name ?? ctx.claimedSpeaker },
          speaker,
          { forceTier2, language }
        );
        setResult(r);
        void fetch("/api/detections", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            verdict: r.verdict,
            band: r.band,
            riskScore: r.riskScore,
            language: r.language.detected,
            explanation: r.smartExplanation,
            featureHash: r.featureHash,
            latencyMs: r.totalLatencyMs,
            requiresOutOfBand: r.requiresOutOfBand,
            payload: {
              votes: r.votes,
              shap: r.shap,
              language: r.language,
            },
          }),
        }).catch(() => {});
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : String(e));
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
        await runFromSamples(s, sampleRate);
      } catch (e: unknown) {
        setError("Could not decode audio: " + (e instanceof Error ? e.message : e));
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
      await runFromSamples(wav, 16000);
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
        await runFromSamples(s, sampleRate);
      };
      mediaRec.current = rec;
      rec.start();
      setRecording(true);
    } catch {
      setError("Microphone permission denied.");
    }
  }, [runFromSamples]);

  const stopRec = () => {
    mediaRec.current?.stop();
    setRecording(false);
  };

  const enroll = () => {
    if (!features) return;
    const name = ctx.claimedSpeaker?.trim() || "enrolled-speaker";
    setEnrolled({ name, mfcc: features.mfcc });
  };

  const anchor = async () => {
    if (!result) return;
    const chain = await anchorRiskAssessment(result);
    const last = chain[chain.length - 1];
    if (last) {
      void fetch("/api/ledger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(last),
      }).catch(() => {});
    }
    setAnchored(true);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.15fr)]">
      <div className="space-y-4">
        <div className="card p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-white/50">
            Feed the cascade
          </h2>
          <div className="flex flex-wrap gap-2">
            <label className="btn-primary cursor-pointer">
              <Upload className="h-4 w-4" />
              Upload clip
              <input
                type="file"
                accept="audio/*,.wav,.mp3,.webm,.ogg,.m4a"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void handleFile(f);
                }}
              />
            </label>
            {!recording ? (
              <button className="btn-ghost" onClick={() => void startRec()}>
                <Mic className="h-4 w-4" /> Record mic
              </button>
            ) : (
              <button className="btn-ghost text-danger" onClick={stopRec}>
                ■ Stop
              </button>
            )}
          </div>
          <p className="mt-3 text-xs text-white/40">Or load a built-in profile — no upload needed.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(
              [
                ["authentic", "Authentic"],
                ["borderline", "Borderline"],
                ["cloned", "Cloned"],
              ] as const
            ).map(([k, label]) => (
              <button
                key={k}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                  k === "cloned"
                    ? "bg-danger/20 text-danger hover:bg-danger/30"
                    : k === "authentic"
                      ? "bg-safe/20 text-safe hover:bg-safe/30"
                      : "bg-warn/20 text-warn hover:bg-warn/30"
                }`}
                onClick={() => void loadDemo(k)}
              >
                {label}
              </button>
            ))}
          </div>
          {audioUrl && (
            <audio className="mt-4 w-full" src={audioUrl} controls preload="metadata" />
          )}
        </div>

        <div className="card space-y-4 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-white/50">
            Call context
          </h2>
          <label className="block text-xs text-white/50">
            Claimed speaker
            <input
              className="mt-1 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white"
              value={ctx.claimedSpeaker ?? ""}
              onChange={(e) => setCtx((c) => ({ ...c, claimedSpeaker: e.target.value || null }))}
              placeholder="e.g. Priya Sharma"
            />
          </label>
          <label className="block text-xs text-white/50">
            Transaction type
            <select
              className="mt-1 w-full rounded-xl border border-white/10 bg-ink-850 px-3 py-2 text-sm text-white"
              value={ctx.transactionType}
              onChange={(e) => setCtx((c) => ({ ...c, transactionType: e.target.value }))}
            >
              {TXN_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs text-white/50">
            Value (₹)
            <input
              type="number"
              className="mt-1 w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white"
              value={ctx.transactionValueInr}
              onChange={(e) =>
                setCtx((c) => ({ ...c, transactionValueInr: Number(e.target.value) || 0 }))
              }
            />
          </label>
          <label className="block text-xs text-white/50">
            ANI reputation {ctx.aniReputation.toFixed(2)}
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              className="mt-1 w-full"
              value={ctx.aniReputation}
              onChange={(e) =>
                setCtx((c) => ({ ...c, aniReputation: Number(e.target.value) }))
              }
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-white/70">
            <input
              type="checkbox"
              checked={ctx.knownContact}
              onChange={(e) => setCtx((c) => ({ ...c, knownContact: e.target.checked }))}
            />
            Known contact
          </label>
          <label className="flex items-center gap-2 text-sm text-white/70">
            <input
              type="checkbox"
              checked={forceTier2}
              onChange={(e) => setForceTier2(e.target.checked)}
            />
            Force Tier-2 (deep SSL)
          </label>
          <label className="block text-xs text-white/50">
            Caller language
            <select
              className="mt-1 w-full rounded-xl border border-white/10 bg-ink-850 px-3 py-2 text-sm text-white"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="auto">Auto / undetermined</option>
              {INDIC_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.language}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-wrap gap-2 pt-1">
            <button className="btn-ghost" disabled={!features} onClick={enroll}>
              <UserPlus className="h-4 w-4" /> Enroll voiceprint
            </button>
            <button className="btn-ghost" disabled={!result || anchored} onClick={() => void anchor()}>
              <Link2 className="h-4 w-4" /> {anchored ? "Anchored" : "Anchor to ledger"}
            </button>
          </div>
          {enrolled && (
            <p className="text-xs text-safe">Voiceprint enrolled for {enrolled.name}.</p>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {error && <div className="card border-danger/40 p-4 text-sm text-danger">{error}</div>}
        {busy && (
          <div className="card p-6 text-center text-sm text-white/60">
            <Sparkles className="mx-auto mb-2 h-5 w-5 animate-pulse text-saffron" />
            Running cascade…
          </div>
        )}
        {!result && !busy && (
          <div className="card flex flex-col items-center justify-center p-12 text-center">
            <p className="text-4xl">🎙️</p>
            <p className="mt-3 max-w-sm text-sm text-white/55">
              Load a demo profile or upload a clip to run the full detection cascade. Try{" "}
              <b className="text-danger">Cloned</b> to see a CRITICAL escalation.
            </p>
          </div>
        )}

        {result && !busy && (
          <>
            <div className="card flex flex-col items-center gap-5 p-6 md:flex-row md:items-start">
              <RiskGauge score={result.riskScore} band={result.band} />
              <div className="min-w-0 flex-1">
                <p
                  className={`text-2xl font-heading italic ${
                    result.verdict === "AUTHENTIC"
                      ? "text-safe"
                      : result.verdict === "LIKELY_CLONE"
                        ? "text-danger"
                        : result.verdict === "INCONCLUSIVE"
                          ? "text-white/60"
                          : "text-warn"
                  }`}
                >
                  {result.verdict.replace("_", " ")}
                </p>
                <p className="mt-1 text-xs text-white/45">
                  🌐 {result.language.detected} · {result.language.adapter}
                  {result.language.source === "undetermined" && " (?)"}
                  <span className="ml-3">⏱ {result.totalLatencyMs} ms</span>
                </p>
                <p className="mt-3 text-sm leading-relaxed text-white/70">
                  {result.smartExplanation}
                </p>
                {result.requiresOutOfBand && (
                  <div className="mt-3 flex gap-2 rounded-xl border border-danger/30 bg-danger/10 p-3 text-xs text-danger">
                    <ShieldAlert className="h-4 w-4 shrink-0" />
                    Out-of-band verification required. Smart-contract policy blocks this{" "}
                    {ctx.transactionType} until a second, non-voice channel confirmation (signed
                    email / pre-agreed codeword) is completed.
                  </div>
                )}
                <p className="mt-3 font-mono text-[11px] text-white/35">
                  feat-hash {shortHash(result.featureHash)}
                </p>
              </div>
            </div>

            <div className="card p-5">
              <h3 className="mb-3 text-sm font-semibold">Cascade-triage trace</h3>
              <div className="space-y-3">
                {result.tiers.map((t) => (
                  <div key={t.tier} className="flex gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white/8 text-xs font-bold">
                      T{t.tier}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <p className="text-sm font-medium">{t.name}</p>
                        {t.invoked ? (
                          <span className="text-xs text-white/40">
                            score {t.score} · {t.latencyMs} ms
                          </span>
                        ) : (
                          <span className="text-xs text-white/30">early-exit</span>
                        )}
                      </div>
                      <p className="text-xs text-white/50">{t.reason}</p>
                      {t.invoked && (
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${t.score * 100}%`,
                              background:
                                t.score > 0.6 ? "#ef4444" : t.score > 0.35 ? "#f59e0b" : "#22c55e",
                            }}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="card p-5">
                <h3 className="mb-3 text-sm font-semibold">Independent signal votes</h3>
                <div className="space-y-3">
                  {result.votes.map((v) => (
                    <div key={v.id}>
                      <div className="flex justify-between text-xs">
                        <span className="text-white/80">{v.label}</span>
                        <span className="text-white/40">
                          {v.score} · w{v.weight}
                        </span>
                      </div>
                      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${v.score * 100}%`,
                            background:
                              v.score > 0.6 ? "#ef4444" : v.score > 0.35 ? "#f59e0b" : "#22c55e",
                          }}
                        />
                      </div>
                      <p className="mt-1 text-[11px] text-white/40">{v.detail}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="card p-5">
                <h3 className="mb-3 text-sm font-semibold">SHAP explanation (why this score)</h3>
                {result.shap.length ? <ShapBars shap={result.shap} /> : <p className="text-xs text-white/40">No SHAP (inconclusive).</p>}
              </div>
            </div>

            <div className="card p-5">
              <h3 className="mb-3 text-sm font-semibold">Signal visualisation</h3>
              <p className="mb-1 text-xs text-white/40">Waveform</p>
              <Waveform samples={samples} />
              <p className="mb-1 mt-3 text-xs text-white/40">Mel spectrogram</p>
              <MelSpectrogram samples={samples} />
            </div>

            <div className="card p-5">
              <h3 className="mb-2 text-sm font-semibold">Indic LID → LoRA adapter routing</h3>
              <p className="text-xs text-white/50">
                {result.language.source === "undetermined" ? "ℹ️ " : "✓ "}
                {result.language.note}
              </p>
              {result.language.codeSwitching && (
                <p className="mt-2 text-xs text-saffron">
                  🔀 Code-switching detected — soft ensemble of top-2 adapters engaged.
                </p>
              )}
              <div className="mt-3 space-y-1.5">
                {result.language.distribution.map((d) => (
                  <div key={d.code} className="flex items-center gap-3 text-xs">
                    <span className="w-36 truncate text-white/70">
                      {d.language} {d.code}
                    </span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full bg-saffron"
                        style={{ width: `${d.prob * 100}%` }}
                      />
                    </div>
                    <span className="w-10 text-right text-white/40">
                      {(d.prob * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {features && (
              <div className="card p-5">
                <h3 className="mb-3 text-sm font-semibold">Extracted feature vector (edge-computed)</h3>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {Object.entries(features)
                    .filter(([, v]) => typeof v === "number")
                    .map(([k, v]) => (
                      <div key={k} className="rounded-lg bg-white/5 px-2 py-1.5">
                        <p className="truncate text-[10px] uppercase tracking-wide text-white/35">
                          {k}
                        </p>
                        <p className="font-mono text-xs text-white/80">{v as number}</p>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
