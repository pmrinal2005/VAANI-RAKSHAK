# 🎙️ VAANI-RAKSHAK · वाणी-रक्षक — "Guardian of Voice"

### AI-Powered Real-Time Voice-Cloning Detection Framework — Zero-Cost, Privacy-First, Multilingual

VAANI-RAKSHAK is a **sophisticated-yet-lightweight, 100% free/open-source** framework that flags
AI-cloned voices mid-call, explains **why** with SHAP, enforces out-of-band verification, and
anchors every decision to a tamper-evident consortium ledger — engineered for Indian banking &
telecom under RBI / DPDP data-localisation constraints.

This repository is the **web application + reproducible training notebook** implementation of the
architecture blueprint. The web app ships a deterministic, explainable **proxy** of the trained
cascade so the public demo runs with **$0 infrastructure and no server-side model**; the Google
Colab notebook trains the **real** open-source models (AASIST-L, wav2vec2 / IndicWav2Vec + LoRA,
ECAPA-TDNN, LightGBM+SHAP) and exports them to ONNX for edge deployment.

---

## 📌 Project Overview

- **Name**: VAANI-RAKSHAK (वाणी-रक्षक — "Guardian of Voice")
- **Goal**: Real-time, explainable, privacy-preserving detection of AI voice-cloning / deepfake-vishing fraud on Indian voice channels, at zero cost, resilient across 22 Indian languages.
- **Theme integration**: Cybersecurity + Blockchain (permissioned Hyperledger-Fabric-style audit ledger).
- **Stack**: Next.js 14 (App Router) · React 18 · TypeScript · Tailwind CSS · Web Audio API · Web Crypto — deployed on **Vercel**.
- **Design philosophy**: **Cascade-triage, not brute force** — a three-tier cascade so expensive compute runs only when cheap checks are ambiguous.

---

## ✅ Currently Completed Features

| # | Feature | Where |
|---|---------|-------|
| 1 | **Cascade-triage detection engine** — Tier 0 DSP → Tier 1 compact neural CM (AASIST-L proxy) → Tier 2 deep multilingual SSL (IndicWav2Vec+AASIST3 proxy), with early-exit | `src/lib/detectionEngine.ts` |
| 2 | **Browser-side audio feature extraction** (Web Audio API + pure-JS DSP): spectral flatness/centroid/rolloff, HF-energy ratio, ZCR, phase discontinuity, F0σ, jitter, shimmer, 13-d MFCC | `src/lib/audioFeatures.ts` |
| 3 | **Live mic streaming + upload + in-browser demo synthesiser** (authentic / borderline / cloned profiles) | `src/components/DetectorClient.tsx`, `src/lib/demoSynth.ts` |
| 4 | **Real-time risk-scoring engine** — LightGBM-style weighted additive fusion of 4 independent signal votes + call context → 0–100 impersonation risk | `src/lib/detectionEngine.ts` |
| 5 | **SHAP-style explanation** — signed per-feature contributions + a plain-language "why" | `src/lib/detectionEngine.ts`, `src/components/ShapBars.tsx` |
| 6 | **Multi-layer voice authenticity** — acoustic/spectral, prosody/behavioural biomarkers, and ECAPA-TDNN speaker cross-session voiceprint (catches stolen-but-genuine voice) | `src/lib/detectionEngine.ts`, `DetectorClient.tsx` |
| 7 | **Out-of-band workflow enforcement** — smart-contract-style block whenever risk crosses a per-workflow threshold | `DetectorClient.tsx` |
| 8 | **Blockchain-anchored audit ledger** — SHA-256 hash chain (PoW-lite), consent + risk + escalation blocks, tamper detection & chain re-verification | `src/lib/ledger.ts`, `src/components/LedgerClient.tsx` |
| 9 | **Indic multilingual LID + LoRA adapter routing simulation** — 12-language distribution, code-switch soft-ensemble of top-2 adapters | `src/lib/indicRouter.ts` |
| 10 | **Privacy-by-architecture** — all inference & feature extraction client-side; only irreversible feature-vector hashes + scores leave the device | `src/lib/crypto.ts`, `audioFeatures.ts` |
| 11 | **Signal visualisation** — live waveform + mel-spectrogram canvas | `src/components/Waveform.tsx`, `MelSpectrogram.tsx` |
| 12 | **Deep-research writeup pages** — Parts 1→4 landscape/gap-analysis/architecture/outcomes + self-verification | `src/app/research/page.tsx`, `architecture/page.tsx` |
| 13 | **Google Colab training notebook** (26 cells) — real AASIST-L, wav2vec2/IndicWav2Vec **+ LoRA fine-tuning**, Indic LID routing, ECAPA-TDNN, LightGBM+SHAP, **ONNX export** | `public/notebooks/VAANI_RAKSHAK_Training_Colab.ipynb`, `colab_src/build_notebook.py` |

---

## 🌐 Functional Entry URIs (routes & parameters)

All routes are **static** (no server-side parameters) — the app is a fully client-side SPA-style
Next.js App Router site. Interactivity is driven by in-browser state, not URL params.

| Path | Description | Key interactions |
|------|-------------|------------------|
| `/` | Landing page — stats, cascade tiers, mapped key components | Navigation CTAs |
| `/detect` | **Live Voice-Cloning Detector** | Upload audio, record mic, load demo profile (`authentic`/`borderline`/`cloned`), set call context (claimed speaker, txn type/value, ANI reputation, known-contact, force-Tier-2), enroll voiceprint, anchor result to ledger |
| `/architecture` | Full architecture blueprint | Cascade data-flow diagram, components A–F, Indic strategy, stack table |
| `/ledger` | **Blockchain-Anchored Audit Ledger** | View chain, add consent/escalation blocks, verify chain, **tamper** to watch verification fail, reset |
| `/research` | **Deep Research & Gap Analysis** | Parts 1–4 + self-verification checklist |
| `/colab` | Colab / Models | **Download the `.ipynb`**, cell-by-cell explanation, weight hand-off guide |

**Static asset**: `GET /notebooks/VAANI_RAKSHAK_Training_Colab.ipynb` — the runnable training notebook.

---

## 🧠 Data Architecture

- **Data models** (`src/lib/types.ts`): `AudioFeatures`, `TierResult`, `SignalVote`, `ShapContribution`, `LanguageRouting`, `SpeakerCheck`, `CallContext`, `RiskAssessment`, `LedgerBlock`.
- **Storage services**:
  - **No server database** — this is privacy-by-architecture. All computation is client-side.
  - **Browser `localStorage`** persists the audit ledger hash chain (`vaani_ledger_v1`) and enrolled voiceprint embeddings — never raw audio.
  - The Colab notebook produces model artefacts (`aasist_lite.onnx`, `fusion_lgbm.pkl/onnx`, `lora_adapter_hi.zip`, `ssl_spoof_head.pt`, `calibration.json`) for optional on-prem/edge deployment.
- **Data flow**:
  `mic/upload → Web Audio decode (16 kHz mono) → in-browser feature extraction → cascade tiers (0/1/2) → 4 independent votes + context → LightGBM-style fusion → 0–100 risk + SHAP + out-of-band gate → SHA-256 feature hash → optional anchor to local hash-chain ledger.`
  Raw waveforms **never** leave the browser; only derived features, their irreversible hash, and the fused score/explanation are produced.

---

## 🇮🇳 Indian Multilingual Strategy (anti-cross-lingual-degradation)

The single biggest technical risk is catastrophic degradation across languages (~42.6% EER even
for a strong 318M-param open baseline on multilingual data). The framework solves this **without
training 22 heavy models**:

1. **One shared IndicWav2Vec backbone** (AI4Bharat, all 22 scheduled languages) as the universal Tier-2 feature extractor.
2. **Lightweight LID** routes each utterance to the correct **few-MB LoRA adapter** (not a whole new model).
3. Adapters fine-tuned on **IndicSynth** (12 langs, 4,000+h synthetic), **IndicVoices-R** (1,704h bona-fide), **InDeepFake** (7 langs, 7 generators).
4. **Code-switching** handled by a *distribution* over languages → soft ensemble of the top-2 adapters.
5. New dialects = a few-MB adapter, not a full retrain.

The Colab notebook (Cells 6, 6b, 6c) implements this concretely: it freezes the backbone, trains a
LoRA adapter + spoof head (PEFT), and adds an LID→adapter router matching `src/lib/indicRouter.ts`.

---

## 📓 Google Colab Notebook (real model training + ONNX export)

- **File**: [`public/notebooks/VAANI_RAKSHAK_Training_Colab.ipynb`](public/notebooks/VAANI_RAKSHAK_Training_Colab.ipynb) — 26 cells, formally `nbformat`-valid.
- **Regenerate**: `python3 colab_src/build_notebook.py`
- **Run**: In Colab → *File → Upload notebook* → select the `.ipynb` → *Runtime → Change runtime type → GPU (T4)* → run top-to-bottom. Every cell has an offline fallback so it runs even without dataset access.
- **What it builds**: environment → data loading → Tier-0 DSP+prosody features → Tier-1 AASIST-L CNN → Tier-2 wav2vec2/IndicWav2Vec → **IndicWav2Vec + LoRA fine-tuning** → Indic LID routing → ECAPA-TDNN speaker → LightGBM+SHAP fusion → **ONNX export** → EER evaluation + calibration hand-off.

---

## 🚀 Deployment

- **Platform**: **Vercel** (Next.js 14 App Router — zero-config).
- **Status**: ✅ Builds cleanly (all routes prerendered static); ready for Vercel deploy.
- **Tech Stack**: Next.js 14 · React 18 · TypeScript · Tailwind CSS.

### Deploy to Vercel (recommended — Git integration)
1. Push this repo to GitHub (already configured to `pmrinal2005/VAANI-RAKSHAK`).
2. Go to [vercel.com/new](https://vercel.com/new) → **Import** the GitHub repo.
3. Framework preset auto-detects **Next.js**. No env vars needed. Click **Deploy**.

### Deploy via Vercel CLI
```bash
npm i -g vercel
vercel            # preview
vercel --prod     # production
```

### Local development / testing
```bash
npm install
npm run dev       # http://localhost:3000 (Vite/Next dev server)
# or production-mode:
npm run build && npm run start
```

> ⚠️ **Note on this environment**: this project is a **Next.js app targeting Vercel** (per the brief:
> *never use Cloudflare/Hono*). It is built & tested on Linux; the final Vercel deploy is done by
> the repo owner via Git import or the Vercel CLI.

---

## 🧩 Not Yet Implemented (future work)

- Wiring the **real trained ONNX weights** into the browser via `onnxruntime-web` (the app currently ships the deterministic proxy; the notebook exports the ONNX + `calibration.json` hand-off).
- Live **WebSocket/SSE** agent-desktop alerting and SMTP/SMS out-of-band delivery (currently the UI enforces the out-of-band gate; transport is described in the architecture).
- Real **Hyperledger Fabric** consortium network (the app models the tamper-evident ledger client-side as a SHA-256 hash chain).
- **Flower** federated learning + **Opacus** differential-privacy training loop (documented; not wired into the demo).
- **FreeSWITCH / Kamailio** SIP/RTP ingest + **Kafka** streaming backbone (architecture-level; not part of the $0 web demo).

## 🗺️ Recommended Next Steps

1. Add `onnxruntime-web`, drop `aasist_lite.onnx` + `fusion_lgbm.onnx` into `public/models/`, and replace the Tier-1/Tier-2 proxy functions with an ONNX session (feature order already matches the notebook).
2. Stand up a small edge sidecar (FastAPI + ONNX Runtime) for on-prem banks that want server-side Tier-2.
3. Deploy a Hyperledger Fabric test network and repoint `src/lib/ledger.ts` at a Fabric gateway.
4. Fine-tune real LoRA adapters on IndicSynth / IndicVoices-R / InDeepFake and ship the adapter zoo.

---

## 📂 Project Structure

```
webapp/
├── src/
│   ├── app/                 # Next.js App Router pages
│   │   ├── page.tsx          # Home
│   │   ├── detect/           # Live detector
│   │   ├── architecture/     # Architecture blueprint
│   │   ├── ledger/           # Blockchain audit ledger
│   │   ├── research/         # Deep research & gap analysis
│   │   ├── colab/            # Colab / models
│   │   ├── layout.tsx        # Root layout + nav + footer
│   │   └── globals.css       # Tailwind + theme
│   ├── components/           # DetectorClient, LedgerClient, RiskGauge, ShapBars, Waveform, MelSpectrogram, NavBar
│   └── lib/                  # detectionEngine, audioFeatures, indicRouter, ledger, crypto, demoSynth, types
├── colab_src/build_notebook.py            # generator for the .ipynb
├── public/notebooks/VAANI_RAKSHAK_Training_Colab.ipynb
├── vercel.json               # Vercel build config
├── next.config.mjs · tailwind.config.ts · tsconfig.json · package.json
└── README.md
```

---

## 🔓 License & Ethics

Research & engineering prototype. Every named component (IndicWav2Vec, AASIST/AASIST3,
SpeechBrain/ECAPA-TDNN, LightGBM, SHAP, ONNX Runtime/TFLite, librosa/Parselmouth/openSMILE,
FastAPI/gRPC, Kafka, FreeSWITCH/Kamailio, Flower, Opacus, Hyperledger Fabric, Docker/K3s,
React/Next.js, and the IndicSynth/IndicVoices(-R)/InDeepFake/ASVspoof datasets) is free and
permissively-licensed / openly released — satisfying the **$0 tech-stack** mandate. No paid SaaS
(Resemble, Reality Defender, Pindrop, CloudSEK, Oracle OCCAS) is used in the build; those were
referenced only for competitive/gap analysis.

*Inspired by the open Voice-Cloning & Fake-Audio-Detection (VCFAD) mel-spectrogram-CNN research
lineage, re-architected into a resilient, multilingual, privacy-preserving, blockchain-audited
framework.*
