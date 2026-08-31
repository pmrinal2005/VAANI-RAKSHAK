# VAANI-RAKSHAK — Production Scoring REST API (`POST /score`)

## Overview

The Production Scoring REST API exposes two primary endpoints under `/api/v1/score` for real-time voice-cloning detection:
- `POST /api/v1/score`: JSON request containing audio features, base64 audio chunks, or references.
- `POST /api/v1/score/upload`: Multipart audio file upload (`.wav`, `.mp3`, `.ogg`, `.flac`, `.webm`).

Every scoring invocation automatically executes the 3-tier cascade countermeasure engine, evaluates multi-modal evidence fusion, triggers enterprise banking policy actions, publishes events to Kafka, and anchors an immutable audit block.

---

## 1. Endpoints

### 1.1 `POST /api/v1/score`

#### Request Headers
- `Content-Type: application/json`
- `X-Request-ID: <uuid>` (Optional correlation ID)

#### Request Body Schema (`DetectionRequest`)

```json
{
  "segment": {
    "callId": "call-12345",
    "segmentId": "seg-001",
    "features": {
      "spectralFlatnessVoiced": 0.38,
      "hfEnergyRatio": 0.15,
      "jitter": 0.0009,
      "shimmer": 0.006,
      "f0RangeHz": 14.5
    }
  },
  "context": {
    "claimedSpeaker": "Priya Sharma",
    "transactionType": "wire-transfer",
    "transactionValueInr": 250000,
    "knownContact": false,
    "aniReputation": 0.25
  },
  "forceTier2": false,
  "scenarioOverride": "CRITICAL_RISK",
  "languageOverride": "hi"
}
```

#### Response Body Schema (`FusionOutput`)

```json
{
  "fusedScore": 0.88,
  "riskScore": 88,
  "band": "CRITICAL",
  "verdict": "LIKELY_CLONE",
  "tiers": [
    {
      "tier": 0,
      "name": "Micro-DSP Pre-Filter",
      "invoked": true,
      "score": 0.88,
      "latencyMs": 1.2,
      "reason": "Status: SUCCESS"
    },
    {
      "tier": 1,
      "name": "Compact Neural Countermeasure",
      "invoked": true,
      "score": 0.89,
      "latencyMs": 14.5,
      "reason": "Status: SUCCESS"
    },
    {
      "tier": 2,
      "name": "Deep Multilingual SSL Countermeasure",
      "invoked": true,
      "score": 0.92,
      "latencyMs": 52.3,
      "reason": "Status: SUCCESS"
    }
  ],
  "votes": [
    {
      "id": "tier0",
      "label": "Micro-DSP Fast Pre-Filter",
      "score": 0.88,
      "weight": 0.20,
      "detail": "Status: SUCCESS"
    },
    {
      "id": "tier1",
      "label": "Compact Neural CM (AASIST-L)",
      "score": 0.89,
      "weight": 0.35,
      "detail": "Model: aasist-l-compact"
    },
    {
      "id": "tier2",
      "label": "Deep Multilingual SSL (IndicWav2Vec)",
      "score": 0.92,
      "weight": 0.45,
      "detail": "Model: indic-wav2vec-deep-hi"
    },
    {
      "id": "prosody",
      "label": "Prosody Biomarker Analysis",
      "score": 0.85,
      "weight": 0.15,
      "detail": "Flattened pitch dynamics and unnaturally low jitter"
    },
    {
      "id": "context",
      "label": "Call & Transaction Risk",
      "score": 0.80,
      "weight": 0.15,
      "detail": "ANI Rep: 0.25, Tx Value: INR 250,000"
    }
  ],
  "shap": [
    {
      "feature": "Neural countermeasure",
      "contribution": 32.5,
      "direction": "increases",
      "detail": "IndicWav2Vec synthetic artifacts"
    },
    {
      "feature": "Voiced spectral texture",
      "contribution": 28.2,
      "direction": "increases",
      "detail": "Voiced flatness 0.38 · HF ratio 0.150"
    }
  ],
  "requiresOutOfBand": true,
  "recommendedAction": "BLOCK",
  "smartExplanation": "Critical risk voice clone flagged primarily by Neural countermeasure.",
  "totalLatencyMs": 68.4
}
```

---

### 1.2 `POST /api/v1/score/upload`

#### Multipart Form Data
- `file`: Binary audio file (`.wav`, `.mp3`, `.ogg`, `.flac`, `.webm`)
- `context_json` *(optional)*: JSON serialized `CallContext`
- `scenario` *(optional)*: `LOW_RISK` | `HIGH_RISK` | `CRITICAL_RISK` | `TIER_DISAGREEMENT` | etc.
- `force_tier2` *(optional)*: `true` | `false`
- `claimed_speaker` *(optional)*: Speaker identity string
- `language_override` *(optional)*: Language ISO code (`hi`, `ta`, `te`, `bn`, etc.)

#### Example Curl

```bash
curl -X POST http://localhost:8000/api/v1/score/upload \
  -F "file=@call_recording.wav;type=audio/wav" \
  -F "scenario=LOW_RISK" \
  -F "context_json={\"transactionType\":\"funds-transfer\",\"transactionValueInr\":45000}"
```

---

## 2. HTTP Status Codes

| Status Code | Description |
|---|---|
| **200 OK** | Successful detection scoring with full `FusionOutput`. |
| **400 Bad Request** | Unsupported audio MIME type or empty file (0 bytes). |
| **422 Unprocessable Entity** | Schema validation error or malformed `context_json`. |
| **500 Internal Server Error** | Unexpected internal pipeline error (traces correlated with request ID). |
