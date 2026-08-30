#!/usr/bin/env python3
"""Generate the VAANI-RAKSHAK Google Colab training notebook (.ipynb).

Produces a real, runnable, GPU-friendly notebook that:
  - installs the open-source stack (transformers, speechbrain, lightgbm, shap, onnx, librosa, praat-parselmouth)
  - loads bona-fide + synthetic Indic speech (IndicSynth / ASVspoof-style, with a
    synthetic fallback so the notebook always runs even offline)
  - builds Tier-0 DSP + prosody features, a compact AASIST-L-style neural CM,
    a wav2vec2 / IndicWav2Vec SSL front-end (Tier-2), ECAPA-TDNN speaker embeddings,
    a LightGBM fusion head with SHAP explanations,
  - exports everything to ONNX for the edge (ONNX Runtime / TFLite).
Every cell has an explanatory markdown header + inline instructions.
"""
import json
import os

cells = []

def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)})

def code(text):
    cells.append({
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": text.rstrip("\n").splitlines(keepends=True),
    })

# ---------------------------------------------------------------------------
md("""# 🎙️ VAANI-RAKSHAK — Model Training & ONNX Export (Google Colab)
### वाणी-रक्षक · AI-Powered Real-Time Voice-Cloning Detection Framework

This notebook trains the **real** open-source models behind the VAANI-RAKSHAK cascade and
exports them to **ONNX** for zero-cost edge deployment. It is the training counterpart to
the Vercel web app (which ships a deterministic, explainable proxy of these models so the
demo runs with $0 infrastructure).

**What you will build, cell by cell:**
1. Environment setup (100% free/open-source)
2. Data loading — bona-fide + synthetic Indic speech (IndicSynth / ASVspoof-style) with an offline synthetic fallback
3. **Tier-0** DSP + prosody feature extraction (librosa + Parselmouth)
4. **Tier-1** compact AASIST-L-style neural countermeasure (PyTorch)
5. **Tier-2** wav2vec2 / IndicWav2Vec SSL front-end + LoRA adapter hook
6. **Speaker** ECAPA-TDNN embeddings (SpeechBrain)
7. **Fusion** LightGBM ensemble + **SHAP** explanations
8. **ONNX export** for ONNX Runtime / TensorFlow Lite edge inference
9. Cascade evaluation (EER) + how to wire results back into the web app

> ✅ **Runtime:** `Runtime → Change runtime type → GPU (T4)` recommended.
> Every cell is self-contained; run top-to-bottom. Offline fallbacks keep it working even without dataset access.
""")

# --- Cell 1 ---
md("""## Cell 1 — Environment setup
Installs the free/open-source stack. Safe to re-run (Colab caches wheels).""")
code(r'''# @title Install dependencies (run once)
!pip -q install torch torchaudio --upgrade
!pip -q install transformers==4.44.2 speechbrain==1.0.0 lightgbm shap onnx onnxruntime
!pip -q install librosa praat-parselmouth soundfile scikit-learn matplotlib seaborn tqdm
print("✅ Environment ready")
import torch
print("CUDA available:", torch.cuda.is_available(), "| device:", "cuda" if torch.cuda.is_available() else "cpu")''')

# --- Cell 2 ---
md("""## Cell 2 — Imports & config""")
code(r'''import os, math, json, random, warnings, numpy as np, pandas as pd
import torch, torch.nn as nn, torchaudio, librosa
warnings.filterwarnings("ignore")
random.seed(42); np.random.seed(42); torch.manual_seed(42)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SR = 16000
N_MELS = 64
TARGET_FRAMES = 200
WORK = "/content/vaani"; os.makedirs(WORK, exist_ok=True)
print("Device:", DEVICE, "| workdir:", WORK)''')

# --- Cell 3 ---
md(r"""## Cell 3 — Data loading (bona-fide + synthetic Indic speech)

**Preferred real datasets** (all openly released — plug in your download paths):
- **IndicSynth** — 12 low-resource Indian languages, 4,000+h synthetic (spoof / label=1)
- **IndicVoices-R** — 1,704h, 22 languages bona-fide speech (label=0)
- **InDeepFake** — 7 Indian languages × 7 generators (spoof / label=1)
- **ASVspoof 2019/2021 LA** — the standard anti-spoofing benchmark

Set `DATA_ROOT` to a folder with `real/*.wav` and `fake/*.wav`. If none is found, the
notebook **synthesises** a small labelled set (natural vs vocoder-like) so it still runs.""")
code(r'''DATA_ROOT = "/content/data"   # <-- point to real/ and fake/ subfolders if you have them

def synth_clip(kind, seconds=2.0, sr=SR):
    """Fallback synth: 'real' = jitter/shimmer + HF hiss; 'fake' = over-smooth + HF cutoff."""
    N = int(sr*seconds); t = np.arange(N)/sr
    f0 = 120 + 30*np.random.rand()
    jit = 0.03 if kind=="real" else 0.002
    shim = 0.18 if kind=="real" else 0.02
    hf = 0.05 if kind=="real" else 0.004
    f0c = f0*(1+jit*np.sin(2*np.pi*5*t)+jit*0.5*np.random.randn(N))
    amp = (0.6+0.4*np.sin(2*np.pi*0.7*t))*(1+shim*np.sin(2*np.pi*8*t))
    sig = np.zeros(N)
    for h in range(1,13):
        g = 1.0/h
        for F in (700,1220,2600): g *= 1+0.9/(1+((f0*h-F)/120)**2)
        if kind=="fake" and f0*h>6000: g*=0.15
        sig += g*np.sin(2*np.pi*np.cumsum(f0c)*h/sr)
    sig = amp*(sig/6) + hf*np.random.randn(N)
    return (sig/ (np.abs(sig).max()+1e-9)).astype(np.float32)

records = []
if os.path.isdir(os.path.join(DATA_ROOT,"real")):
    for lab,sub in [(0,"real"),(1,"fake")]:
        d = os.path.join(DATA_ROOT,sub)
        for f in os.listdir(d):
            if f.lower().endswith((".wav",".flac",".mp3")):
                records.append({"path":os.path.join(d,f),"label":lab})
    print(f"Loaded {len(records)} real files from {DATA_ROOT}")
else:
    print("⚠ No dataset found — generating a synthetic labelled set (offline fallback).")
    os.makedirs(f"{WORK}/real",exist_ok=True); os.makedirs(f"{WORK}/fake",exist_ok=True)
    import soundfile as sf
    for i in range(120):
        for lab,kind in [(0,"real"),(1,"fake")]:
            p=f"{WORK}/{kind}/{kind}_{i:03d}.wav"
            sf.write(p, synth_clip(kind), SR)
            records.append({"path":p,"label":lab})

df = pd.DataFrame(records).sample(frac=1,random_state=42).reset_index(drop=True)
print(df.label.value_counts()); df.head()''')

# --- Cell 4 ---
md(r"""## Cell 4 — Tier-0 DSP + prosody feature extraction
Classical, GPU-free features (librosa + Parselmouth): spectral flatness/centroid/rolloff,
HF-energy ratio, ZCR, plus **prosody biomarkers** F0 σ, **jitter**, **shimmer** — the exact
features the web app computes in-browser (edge-first).""")
code(r'''import parselmouth
from parselmouth.praat import call

def dsp_prosody_features(path):
    y, sr = librosa.load(path, sr=SR, mono=True)
    y = y/(np.abs(y).max()+1e-9)
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=256))+1e-9
    freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
    flat = float(np.mean(librosa.feature.spectral_flatness(y=y)))
    cent = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    roll = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)))
    zcr  = float(np.mean(librosa.feature.zero_crossing_rate(y)))
    hf   = float(S[freqs>6000].sum()/S.sum())
    rms  = float(np.sqrt(np.mean(y**2)+1e-9))
    crest= float(np.max(np.abs(y))/(rms+1e-9))
    # prosody via Praat
    try:
        snd = parselmouth.Sound(y, sampling_frequency=sr)
        pp  = call(snd, "To PointProcess (periodic, cc)", 70, 400)
        jitter  = call(pp, "Get jitter (local)", 0,0, 1e-4,0.02,1.3)
        shimmer = call([snd,pp], "Get shimmer (local)", 0,0, 1e-4,0.02,1.3,1.6)
        pitch = snd.to_pitch(); f0v = pitch.selected_array['frequency']; f0v=f0v[f0v>0]
        f0std = float(np.std(f0v)) if len(f0v) else 0.0
    except Exception:
        jitter=shimmer=f0std=0.0
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13).mean(axis=1)
    return dict(flat=flat, cent=cent, roll=roll, zcr=zcr, hf=hf, crest=crest,
                jitter=float(jitter or 0), shimmer=float(shimmer or 0), f0std=f0std,
                **{f"mfcc{i}":float(v) for i,v in enumerate(mfcc)})

from tqdm.auto import tqdm
feat_rows=[]
for _,r in tqdm(df.iterrows(), total=len(df)):
    try:
        f=dsp_prosody_features(r["path"]); f["label"]=r["label"]; f["path"]=r["path"]; feat_rows.append(f)
    except Exception as e:
        pass
feat_df=pd.DataFrame(feat_rows)
print("Feature matrix:", feat_df.shape); feat_df.head()''')

# --- Cell 5 ---
md(r"""## Cell 5 — Tier-1: compact AASIST-L-style neural countermeasure
A lightweight mel-spectrogram CNN with a graph-attention-style pooling head — a distilled
stand-in for **AASIST-L** (deployable via ONNX/TFLite INT8). For the full official model use
`clovaai/aasist`; this compact variant trains in minutes on Colab.""")
code(r'''def to_mel(path):
    y,_=librosa.load(path,sr=SR,mono=True); y=y/(np.abs(y).max()+1e-9)
    m=librosa.feature.melspectrogram(y=y,sr=SR,n_fft=1024,hop_length=256,n_mels=N_MELS)
    m=librosa.power_to_db(m)
    if m.shape[1]<TARGET_FRAMES: m=np.pad(m,((0,0),(0,TARGET_FRAMES-m.shape[1])))
    else: m=m[:,:TARGET_FRAMES]
    return m.astype(np.float32)

class MelDS(torch.utils.data.Dataset):
    def __init__(self, frame): self.f=frame.reset_index(drop=True)
    def __len__(self): return len(self.f)
    def __getitem__(self,i):
        r=self.f.iloc[i]
        return torch.tensor(to_mel(r["path"]))[None], torch.tensor(float(r["label"]))

class AASISTLite(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc=nn.Sequential(
            nn.Conv2d(1,16,3,padding=1), nn.BatchNorm2d(16), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16,32,3,padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32,64,3,padding=1), nn.BatchNorm2d(64), nn.ReLU())
        self.attn=nn.Conv2d(64,1,1)          # graph-attention-style saliency map
        self.fc=nn.Sequential(nn.Dropout(0.3), nn.Linear(64,1))
    def forward(self,x):
        h=self.enc(x); a=torch.softmax(self.attn(h).flatten(2),dim=-1).unsqueeze(1)
        h=(h.flatten(2).unsqueeze(1)*a).sum(-1).squeeze(1)
        return self.fc(h).squeeze(1)

from sklearn.model_selection import train_test_split
tr,va=train_test_split(feat_df,test_size=0.25,stratify=feat_df.label,random_state=42)
dl_tr=torch.utils.data.DataLoader(MelDS(tr),batch_size=16,shuffle=True)
dl_va=torch.utils.data.DataLoader(MelDS(va),batch_size=16)

cm=AASISTLite().to(DEVICE); opt=torch.optim.Adam(cm.parameters(),1e-3,weight_decay=1e-4)
crit=nn.BCEWithLogitsLoss()
for ep in range(8):
    cm.train()
    for xb,yb in dl_tr:
        xb,yb=xb.to(DEVICE),yb.to(DEVICE); opt.zero_grad()
        loss=crit(cm(xb),yb*0.9+0.05); loss.backward(); opt.step()
    cm.eval(); P,Y=[],[]
    with torch.no_grad():
        for xb,yb in dl_va:
            P+=torch.sigmoid(cm(xb.to(DEVICE))).cpu().tolist(); Y+=yb.tolist()
    from sklearn.metrics import f1_score
    print(f"epoch {ep+1} | val F1 {f1_score(Y,[p>=0.5 for p in P]):.3f}")
torch.save(cm.state_dict(), f"{WORK}/aasist_lite.pt"); print("saved aasist_lite.pt")''')

# --- Cell 6 ---
md(r"""## Cell 6 — Tier-2: wav2vec2 / IndicWav2Vec SSL front-end (+ LoRA adapter hook)
The deep multilingual verifier. Swap the checkpoint to **`ai4bharat/indicwav2vec-hindi`** (or
other Indic checkpoints) for Indic robustness. A **LoRA adapter** (`peft`) attaches a few-MB,
per-language head on the shared backbone — this is the anti-catastrophic-degradation strategy.""")
code(r'''from transformers import Wav2Vec2Model, Wav2Vec2FeatureExtractor
SSL_CKPT = "facebook/wav2vec2-base"      # or: "ai4bharat/indicwav2vec-hindi"
fe  = Wav2Vec2FeatureExtractor.from_pretrained(SSL_CKPT)
ssl = Wav2Vec2Model.from_pretrained(SSL_CKPT).to(DEVICE).eval()

def ssl_embed(path):
    y,_=librosa.load(path,sr=SR,mono=True)
    iv=fe(y,sampling_rate=SR,return_tensors="pt").input_values.to(DEVICE)
    with torch.no_grad(): h=ssl(iv).last_hidden_state.mean(1)   # (1, 768) utterance embedding
    return h.squeeze(0).cpu().numpy()

print("SSL embedding dim:", ssl_embed(df.path.iloc[0]).shape)

# Optional LoRA adapter (per-language, few MB) — uncomment to enable:
# !pip -q install peft
# from peft import LoraConfig, get_peft_model
# ssl_lora = get_peft_model(Wav2Vec2Model.from_pretrained(SSL_CKPT),
#     LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj","v_proj"], lora_dropout=0.05))
# ssl_lora.print_trainable_parameters()   # ~0.3% of params -> a few MB per language''')

# --- Cell 7 ---
md(r"""## Cell 7 — Speaker cross-session consistency (ECAPA-TDNN, SpeechBrain)
Computes a compact voiceprint for the **stolen-but-genuine voice** blind spot. Compare a live
embedding to an enrolled one with cosine similarity — a mismatch raises risk independent of
whether the audio is AI-generated.""")
code(r'''from speechbrain.inference.speaker import EncoderClassifier
spk = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb",
                                     run_opts={"device":DEVICE})
def spk_embed(path):
    sig,_=torchaudio.load(path); 
    if sig.shape[0]>1: sig=sig.mean(0,keepdim=True)
    return spk.encode_batch(sig).squeeze().detach().cpu().numpy()

e0,e1 = spk_embed(df.path.iloc[0]), spk_embed(df.path.iloc[1])
cos = float(np.dot(e0,e1)/(np.linalg.norm(e0)*np.linalg.norm(e1)+1e-9))
print("example voiceprint cosine similarity:", round(cos,3))''')

# --- Cell 8 ---
md(r"""## Cell 8 — Fusion: LightGBM ensemble + SHAP explanations
Fuses DSP + prosody + neural-CM score + (optional SSL/speaker) into a single explainable
0–1 impersonation likelihood. **SHAP** gives the per-feature 'why' the web app renders.""")
code(r'''import lightgbm as lgb, shap
from sklearn.metrics import classification_report

# add neural CM score as a feature
cm.eval()
def cm_score(path):
    with torch.no_grad():
        return float(torch.sigmoid(cm(torch.tensor(to_mel(path))[None,None].to(DEVICE))).cpu())
feat_df["cm_score"]=[cm_score(p) for p in feat_df.path]

X = feat_df.drop(columns=["label","path"]); yv=feat_df["label"].values
Xtr,Xte,ytr,yte=train_test_split(X,yv,test_size=0.25,stratify=yv,random_state=42)
gbm=lgb.LGBMClassifier(n_estimators=300,learning_rate=0.05,num_leaves=31)
gbm.fit(Xtr,ytr)
pred=gbm.predict(Xte)
print(classification_report(yte,pred,target_names=["Real","Fake"],digits=3))

explainer=shap.TreeExplainer(gbm)
sv=explainer.shap_values(Xte)
shap.summary_plot(sv, Xte, plot_type="bar", show=True)
import joblib; joblib.dump(gbm, f"{WORK}/fusion_lgbm.pkl"); print("saved fusion_lgbm.pkl")''')

# --- Cell 9 ---
md(r"""## Cell 9 — ONNX export for edge deployment (ONNX Runtime / TFLite)
Export the neural CM to ONNX so it runs client-side with low CPU usage on constrained devices —
the same edge-first pattern the framework mandates. LightGBM exports via `onnxmltools`.""")
code(r'''# Neural CM -> ONNX
cm.eval()
dummy=torch.randn(1,1,N_MELS,TARGET_FRAMES,device=DEVICE)
torch.onnx.export(cm, dummy, f"{WORK}/aasist_lite.onnx",
                  input_names=["mel"], output_names=["logit"],
                  dynamic_axes={"mel":{0:"batch"}}, opset_version=14)
print("✅ exported aasist_lite.onnx")

# verify with onnxruntime
import onnxruntime as ort
sess=ort.InferenceSession(f"{WORK}/aasist_lite.onnx", providers=["CPUExecutionProvider"])
out=sess.run(None,{"mel":dummy.cpu().numpy()}); print("ONNX logit:", out[0].ravel()[:1])

# LightGBM fusion -> ONNX (optional)
try:
    !pip -q install onnxmltools skl2onnx
    from onnxmltools import convert_lightgbm
    from onnxmltools.convert.common.data_types import FloatTensorType
    onx=convert_lightgbm(gbm, initial_types=[("input",FloatTensorType([None,X.shape[1]]))])
    open(f"{WORK}/fusion_lgbm.onnx","wb").write(onx.SerializeToString())
    print("✅ exported fusion_lgbm.onnx")
except Exception as e:
    print("LightGBM ONNX export optional — skipped:", e)''')

# --- Cell 10 ---
md(r"""## Cell 10 — Cascade evaluation (EER) & feeding results back to the web app
Compute Equal Error Rate on the held-out set, then export a small JSON of calibrated
thresholds you can paste into the web app's engine to align the deployed proxy with the
trained model.""")
code(r'''from sklearn.metrics import roc_curve
proba=gbm.predict_proba(Xte)[:,1]
fpr,tpr,thr=roc_curve(yte,proba); fnr=1-tpr
eer_idx=np.nanargmin(np.abs(fnr-fpr)); eer=fpr[eer_idx]
print(f"Fusion EER = {eer*100:.2f}%  @ threshold {thr[eer_idx]:.3f}")

calib={
  "fusion_threshold": float(thr[eer_idx]),
  "eer_percent": float(eer*100),
  "cm_ckpt": "aasist_lite.onnx",
  "ssl_ckpt": SSL_CKPT,
  "n_features": int(X.shape[1]),
  "feature_order": list(X.columns),
}
json.dump(calib, open(f"{WORK}/calibration.json","w"), indent=2)
print(json.dumps(calib, indent=2))

from google.colab import files    # download the artefacts
for f in ["aasist_lite.onnx","fusion_lgbm.pkl","calibration.json"]:
    p=f"{WORK}/{f}"
    if os.path.exists(p): files.download(p)''')

md("""---
### ✅ Done
You now have: `aasist_lite.onnx` (Tier-1 edge model), `fusion_lgbm.pkl` + optional
`fusion_lgbm.onnx` (explainable fusion), and `calibration.json` (thresholds).

**Wire back into the web app:** the Vercel app ships a deterministic proxy of these models so
the public demo needs no server. To use the *trained* weights, serve the ONNX files and load
them client-side with `onnxruntime-web`, replacing the Tier-1/Tier-2 proxy functions in
`src/lib/detectionEngine.ts` — the feature extractor, fusion weights and SHAP layout already
match this notebook's `feature_order`.

**For real Indic robustness:** set `SSL_CKPT = "ai4bharat/indicwav2vec-hindi"`, enable the
LoRA adapter cell, and train on IndicSynth / IndicVoices-R / InDeepFake.
""")

nb = {
    "cells": cells,
    "metadata": {
        "colab": {"provenance": [], "toc_visible": True},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
        "accelerator": "GPU",
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

out = os.path.join(os.path.dirname(__file__), "..", "public", "notebooks",
                   "VAANI_RAKSHAK_Training_Colab.ipynb")
out = os.path.abspath(out)
with open(out, "w") as f:
    json.dump(nb, f, indent=1)
print("Wrote", out, "with", len(cells), "cells")
