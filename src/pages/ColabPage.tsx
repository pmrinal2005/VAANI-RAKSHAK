const CELLS: [string, string, string][] = [
  ["1", "Environment setup", "Installs the free stack: torch, torchaudio, transformers, speechbrain, lightgbm, shap, onnx, onnxruntime, librosa, praat-parselmouth."],
  ["2", "Imports & config", "Seeds, device (GPU T4), SR=16kHz, mel config, workdir."],
  ["3", "Data loading", "Bona-fide + synthetic Indic speech. Auto-synthesises a labelled fallback so it always runs."],
  ["4", "Tier-0 DSP + prosody", "The same features the web app extracts in-browser — so training and demo speak one language."],
  ["5", "Tier-1 AASIST-L CM", "Compact mel-CNN with graph-attention-style pooling. Trains in minutes. Exports to ONNX."],
  ["6", "Tier-2 SSL front-end", "wav2vec2 / IndicWav2Vec utterance embeddings — the deep multilingual verifier."],
  ["6b", "IndicWav2Vec + LoRA", "Freezes one shared backbone, trains a few-MB adapter. Not a 22-model zoo."],
  ["6c", "Indic LID routing", "Language-ID head routes each utterance to its adapter and handles code-switch."],
  ["7", "ECAPA-TDNN speaker", "Voiceprint embeddings + cosine — the stolen-but-genuine-voice check."],
  ["8", "LightGBM + SHAP", "Explainable fusion of all signal streams. The web app's 'why' is born here."],
  ["9", "ONNX export", "Neural CM and fusion exported for the edge. Adapter bundled as a few MB zip."],
  ["10", "Cascade eval", "EER, calibration.json, feature order — the hand-off back into this app."],
];

const NB =
  "https://github.com/pmrinal2005/VAANI-RAKSHAK/raw/main/public/notebooks/VAANI_RAKSHAK_Training_Colab.ipynb";

export function ColabPage() {
  return (
    <div className="space-y-10">
      <header>
        <p className="mb-2 text-[10px] uppercase tracking-[0.28em] text-white/35">
          Colab / Models
        </p>
        <h1 className="font-heading text-4xl italic text-white md:text-5xl">
          Train the real ears. Keep the demo free.
        </h1>
        <p className="mt-3 max-w-3xl font-body text-sm font-light text-white/55 md:text-base">
          This app ships a deterministic, explainable proxy so the public demo runs with $0
          infrastructure. The notebook trains the real open-source models and exports them to ONNX
          for on-prem / edge deployment.
        </p>
      </header>

      <section className="card p-6">
        <div className="flex flex-wrap items-center gap-3">
          <a href={NB} className="btn-primary" target="_blank" rel="noreferrer">
            ⬇ Download the .ipynb notebook
          </a>
          <a
            href="https://colab.research.google.com/"
            target="_blank"
            rel="noreferrer"
            className="btn-ghost"
          >
            Open Google Colab ↗
          </a>
        </div>
        <p className="mt-3 text-xs text-white/45">
          In Colab: <b>File → Upload notebook</b> → select{" "}
          <span className="mono">VAANI_RAKSHAK_Training_Colab.ipynb</span>, then{" "}
          <b>Runtime → GPU (T4)</b> and run top-to-bottom. Offline fallbacks keep every cell working.
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
            <span className="mono">fusion_lgbm.onnx</span>, <span className="mono">calibration.json</span>.
          </li>
          <li>
            Place ONNX files in <span className="mono">public/models/</span> and load them with
            onnxruntime-web.
          </li>
          <li>
            Swap the Tier-1 / Tier-2 proxies in <span className="mono">detectionEngine.ts</span> —
            feature order already matches.
          </li>
          <li>
            For real Indic robustness, enable the LoRA cell and fine-tune on IndicSynth /
            IndicVoices-R / InDeepFake.
          </li>
        </ol>
      </section>

      <section className="card border-indiagreen/30 bg-indiagreen/5 p-6">
        <h2 className="text-lg font-bold">Why a proxy in the public demo?</h2>
        <p className="mt-2 text-sm text-white/60">
          A 318M-parameter SSL model cannot run inside a free static site within latency and size
          limits, and the brief mandates a $0 stack with edge-first, privacy-by-architecture
          inference. The deterministic proxy reproduces the trained decision surface from the same
          edge-computed features — so the live demo stays free, private and instant, while this
          notebook is the fully reproducible real-model path.
        </p>
      </section>
    </div>
  );
}
