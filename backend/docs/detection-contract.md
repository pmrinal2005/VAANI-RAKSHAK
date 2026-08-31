# VAANI-RAKSHAK — R1 Model Interface Contract
## Backend (R2) <-> ML Model Subsystem (R1) Integration Specification

> **Status:** 🟡 MOCKED (Phase 1). This contract defines the exact interface required for future R1 models when unblocked.

---

## 1. Overview & Principles

1. **Dependency Inversion:** R2 orchestrator depends exclusively on Python Protocols (`Tier0Detector`, `Tier1Detector`, `Tier2Detector`, `ProsodyDetector`, `SpeakerVerifier`, `LanguageRouter`).
2. **Deterministic Schemas:** All model inputs and outputs pass through strictly typed Pydantic v2 schemas (`DetectionRequest`, `DetectionResult`, `SignalVote`, `SpeakerCheckResult`, `LanguageRoutingResult`).
3. **No Silent Failures:** If a model fails or times out, it must return `status=TIMEOUT` or `status=ERROR` with explicit error details, or raise `ModelUnavailableError` / `ModelTimeoutError`. A model failure **must NEVER silently produce `score = 0.0`**.
4. **Privacy First:** Raw audio waveforms are never permanently stored or exposed in logs. Models receive in-memory audio buffers, feature vectors, or temporary ephemeral references.

---

## 2. R1 Model Interface Contracts

### Tier 0: Micro-DSP Pre-Filter
- **Target Architecture:** Spectral heuristic analyzer / ONNX linear acoustic pre-filter
- **Protocol:** `app.detection.base.Tier0Detector`
- **Input:**
  - `DetectionRequest.segment.features: AudioFeatures` (Acoustic feature vector) or raw audio buffer
  - `DetectionRequest.context: CallContext`
- **Output:**
  - `DetectionResult`
    - `tier: 0`
    - `score: float` (0.0 to 1.0, where 0.0=authentic, 1.0=synthetic)
    - `confidence: float` (0.0 to 1.0)
    - `label: DetectionLabel` (`AUTHENTIC` | `SUSPICIOUS` | `LIKELY_CLONE` | `INCONCLUSIVE`)
    - `latency_ms: float` (target: < 3ms)
    - `model_name: str` (e.g. `"micro-dsp-prefilter"`)
    - `model_version: str` (e.g. `"1.0.0"`)
    - `signals: dict` (e.g. `{"spectral_flatness": 0.35, "voicing_ratio": 0.82}`)
    - `status: DetectionStatus` (`SUCCESS` | `ERROR` | `TIMEOUT`)

---

### Tier 1: Compact Neural Countermeasure
- **Target Architecture:** AASIST-L / RawNet3 (Graph Attention Spectro-Temporal Network)
- **Protocol:** `app.detection.base.Tier1Detector`
- **Input:**
  - `DetectionRequest.segment: AudioSegment` (16 kHz mono PCM / Float32Array)
  - `DetectionRequest.context: CallContext`
- **Output:**
  - `DetectionResult`
    - `tier: 1`
    - `score: float` (0.0 to 1.0)
    - `confidence: float` (0.0 to 1.0)
    - `label: DetectionLabel` (`AUTHENTIC` | `SUSPICIOUS` | `LIKELY_CLONE` | `INCONCLUSIVE`)
    - `latency_ms: float` (target: < 20ms)
    - `model_name: str` (e.g. `"aasist-l-onnx"`)
    - `model_version: str` (e.g. `"2.1.0"`)
    - `signals: dict` (e.g. `{"gat_attention_entropy": 0.74, "vocoder_anomaly": 0.88}`)
    - `status: DetectionStatus`

---

### Tier 2: Deep Multilingual SSL Countermeasure
- **Target Architecture:** IndicWav2Vec + AASIST3 + Language-Specific LoRA Adapters
- **Protocol:** `app.detection.base.Tier2Detector`
- **Input:**
  - `DetectionRequest.segment: AudioSegment` (16 kHz mono PCM)
  - `DetectionRequest.language_override: str | None` (Target Indic language adapter code)
  - `tier1_score: float | None` (Corroborating prior score)
- **Output:**
  - `DetectionResult`
    - `tier: 2`
    - `score: float` (0.0 to 1.0)
    - `confidence: float` (0.0 to 1.0)
    - `label: DetectionLabel` (`AUTHENTIC` | `SUSPICIOUS` | `LIKELY_CLONE` | `INCONCLUSIVE`)
    - `latency_ms: float` (target: < 100ms)
    - `model_name: str` (e.g. `"indic-wav2vec-aasist3"`)
    - `model_version: str` (e.g. `"1.4.0"`)
    - `signals: dict` (e.g. `{"ssl_layer_activations": [0.81, 0.92], "active_adapter": "lora-hi-v2"}`)
    - `status: DetectionStatus`

---

### Prosody & Behavioural Biomarkers
- **Target Architecture:** Statistical acoustic prosody extractor (pitch drift, jitter, shimmer, modulation)
- **Protocol:** `app.detection.base.ProsodyDetector`
- **Input:**
  - `DetectionRequest.segment.features: AudioFeatures`
- **Output:**
  - `SignalVote`
    - `id: "prosody"`
    - `label: "Prosody / behavioural biomarkers"`
    - `score: float` (0.0 to 1.0)
    - `weight: 0.22`
    - `detail: str` (Diagnostic description of F0 range, jitter, shimmer)

---

### Speaker Verification
- **Target Architecture:** ECAPA-TDNN x-vector / embedding extractor
- **Protocol:** `app.detection.base.SpeakerVerifier`
- **Input:**
  - `DetectionRequest.segment: AudioSegment`
  - `DetectionRequest.enrolled_mfcc: list[float]` (Enrolled speaker reference vector)
  - `DetectionRequest.context.claimed_speaker: str | None`
- **Output:**
  - `SpeakerCheckResult`
    - `enrolled: bool`
    - `claimed_speaker: str | None`
    - `cosine_similarity: float | None`
    - `mismatch: bool` (`True` if `cosine_similarity < 0.55`)
    - `note: str`

---

### Indic Spoken Language Identification (LID)
- **Target Architecture:** IndicLID ONNX classifier (12 Indic languages + Code-Switching detector)
- **Protocol:** `app.detection.base.LanguageRouter`
- **Input:**
  - `DetectionRequest.segment: AudioSegment`
  - `DetectionRequest.language_override: str | None`
- **Output:**
  - `LanguageRoutingResult`
    - `detected: str` (e.g. `"Hindi"`)
    - `code: str` (e.g. `"hi"`)
    - `confidence: float` (0.0 to 1.0)
    - `distribution: list[LanguageDistributionItem]` (Top-k language probabilities)
    - `adapter: str` (e.g. `"lora-hi-v2"` or `"lora-hi-v2 ⊕ lora-enIN-v2"`)
    - `code_switching: bool`
    - `source: LanguageRoutingSource` (`onnx-lid` | `user-selected` | `undetermined`)
    - `note: str`

---

## 3. Required Model Metadata

Every real R1 model wrapper delivered must publish standard metadata:
```python
{
    "model_name": "aasist-l-onnx",
    "model_version": "1.0.0",
    "framework": "onnxruntime",
    "input_sample_rate": 16000,
    "input_channels": 1,
    "input_shape": [1, 64000],  # 4-second audio window
    "quantization": "int8" | "fp16" | "fp32",
    "execution_provider": "CPUExecutionProvider" | "CUDAExecutionProvider"
}
```
