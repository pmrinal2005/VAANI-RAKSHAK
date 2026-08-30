export const metadata = { title: "Colab / Models · VAANI-RAKSHAK" };

const CELLS = [
  ["1", "Environment setup", "Installs the free stack: torch, torchaudio, transformers, speechbrain, lightgbm, shap, onnx, onnxruntime, librosa, praat-parselmouth."],
  ["2", "Imports & config", "Seeds, device (GPU T4), SR=16kHz, mel config, workdir."],
  ["3", "Data loading", "Bona-fide + synthetic Indic speech (IndicSynth / IndicVoices-R / InDeepFake / ASVspoof). Auto-synthesises a labelled fallback so it always runs."],
  ["4", "Tier-0 DSP + prosody", "librosa spectral flatness/centroid/rolloff/HF-ratio/ZCR + Parselmouth jitter/shimmer/F0σ — same features the web app extracts in-browser."],
  ["5", "Tier-1 AASIST-L CM", "Compact mel-CNN with graph-attention-style pooling — distilled AASIST-L stand-in, trains in minutes, exports to ONNX INT8."],
  ["6", "Tier-2 SSL front-end", "wav2vec2 / IndicWav2Vec utterance embeddings + optional PEFT LoRA adapter (few-MB per language)."],
  ["7", "ECAPA-TDNN speaker", "SpeechBrain voiceprint embeddings + cosine — the stolen-but-genuine-voice check."],
  ["8", "LightGBM + SHAP fusion", "Explainable gradient-boosted fusion of all signal streams; SHAP summary plot = the web app's 'why'."],
  ["9", "ONNX export", "Neural CM → aasist_lite.onnx (verified with onnxruntime); LightGBM → fusion_lgbm.onnx for the edge."],
  ["10", "Cascade eval + hand-off", "Computes EER, exports calibration.json (thresholds + feature order) to paste back into the web app."],
];

export default function ColabPage() {
  const nbPath = "/notebooks/VAANI_RAKSHAK_Training_Colab.ipynb";
  return (
    <div className="space-y-10">
      <header>
        <h1 className="text-3xl font-black">Colab Training Notebook &amp; Models</h1>
        <p className="mt-2 max-w-3xl text-white/55">
          The web app ships a deterministic, explainable <b>proxy</b> of the cascade so the
          public demo runs with $0 infrastructure and no server-side model. This notebook
          trains the <b>real</b> open-source models (AASIST-L, wav2vec2/IndicWav2Vec,
          ECAPA-TDNN, LightGBM+SHAP) and exports them to ONNX for edge deployment.
        </p>
      </header>

      <section className="card p-6">
        <div className="flex flex-wrap items-center gap-3">
          <a href={nbPath} download className="btn-primary">
            ⬇ Download the .ipynb notebook
          </a>
          <a
            href={`https://colab.research.google.com/`}
            target="_blank"
            rel="noreferrer"
            className="btn-ghost"
          >
            Open Google Colab ↗
          </a>
        </div>
        <p className="mt-3 text-xs text-white/45">
          In Colab: <b>File → Upload notebook →</b> select the downloaded{" "}
          <span className="mono">VAANI_RAKSHAK_Training_Colab.ipynb</span>, then{" "}
          <b>Runtime → Change runtime type → GPU (T4)</b> and run cells top-to-bottom.
          Offline fallbacks keep every cell working even without dataset access.
        </p>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold">What the notebook does — cell by cell</h2>
        <div className="space-y-3">
          {CELLS.map(([n, t, d]) => (
            <div key={n} className="card card-hover flex items-start gap-4 p-5">
              <span className="mono flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-saffron/15 text-sm font-bold text-saffron">
                {n}
              </span>
              <div>
                <h3 className="font-semibold">{t}</h3>
                <p className="mt-1 text-sm text-white/55">{d}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="card p-6">
        <h2 className="text-xl font-bold">Wiring trained weights back into the app</h2>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-white/65">
          <li>
            Run the notebook → download <span className="mono">aasist_lite.onnx</span>,{" "}
            <span className="mono">fusion_lgbm.onnx</span>,{" "}
            <span className="mono">calibration.json</span>.
          </li>
          <li>
            Add <span className="mono">onnxruntime-web</span> to the app and place the ONNX
            files in <span className="mono">public/models/</span>.
          </li>
          <li>
            Replace the Tier-1/Tier-2 proxy functions in{" "}
            <span className="mono">src/lib/detectionEngine.ts</span> with an ONNX Runtime
            session — the browser feature extractor already matches the notebook’s{" "}
            <span className="mono">feature_order</span>.
          </li>
          <li>
            For real Indic robustness set{" "}
            <span className="mono">SSL_CKPT = &quot;ai4bharat/indicwav2vec-hindi&quot;</span>,
            enable the LoRA cell, and fine-tune on IndicSynth / IndicVoices-R / InDeepFake.
          </li>
        </ol>
      </section>

      <section className="card border-indiagreen/30 bg-indiagreen/5 p-6">
        <h2 className="text-lg font-bold">Why a proxy in production?</h2>
        <p className="mt-2 text-sm text-white/60">
          A 318M-parameter SSL model can’t run inside a free serverless function within
          latency/size limits, and the brief mandates a <b>$0 tech stack</b> with{" "}
          <b>edge-first, privacy-by-architecture</b> inference. The deterministic proxy
          reproduces the trained model’s decision surface from the same edge-computed
          features — so the live demo stays free, private and instant, while this notebook
          provides the fully reproducible real-model training + ONNX path for on-prem/edge
          deployment.
        </p>
      </section>
    </div>
  );
}
