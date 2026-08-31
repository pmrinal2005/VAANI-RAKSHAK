# VAANI-RAKSHAK — Simulated Real-Time Telephony Pipeline

## Overview

The telephony simulation subsystem emulates active telephone calls (RTP/SIP stream chunks) entering the VAANI-RAKSHAK fraud interception engine. It supports deterministic temporal transitions, allowing frontend and SOC dashboards to observe real-time deepfake voice injections mid-call and verify automatic banking policy interceptor triggers (`BLOCK`, `HOLD`, `CHALLENGE`).

---

## 1. Architecture

```
                      ┌──────────────────────────────────────────────┐
                      │              POST /calls/simulate            │
                      └──────────────────────┬───────────────────────┘
                                             │ Creates Session
                                             ▼
                                ┌──────────────────────────┐
                                │    CallSessionManager    │
                                └────────────┬─────────────┘
                                             │ Spawns Task
                                             ▼
                                ┌──────────────────────────┐
                                │    TelephonySimulator    │
                                └────────────┬─────────────┘
                                             │ Emits 1.0s RTP Chunks
                                             ▼
                                ┌──────────────────────────┐
                                │   score_audio_segment    │
                                └────────────┬─────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
               Kafka Event Bus                             ConnectionManager
         (vaani.fusion.result, vaani.risk.events)     (WS /ws/calls/{id} & Global SOC)
```

---

## 2. Temporal Trajectory Patterns

| Pattern | Description | Interceptor Behavior |
|---|---|---|
| **`STEADY`** | Constant risk scenario (e.g. `LOW_RISK`) throughout call. | Remains `ALLOW`. |
| **`AUTHENTIC_TO_CLONE`** | Starts authentic (first 40%), switches to high-risk voice clone mid-call. | Triggers instant `BLOCK` or `HOLD`, setting call status to `INTERCEPTED`. |
| **`CLONE_BURST`** | Authentic -> 3-chunk high-risk burst -> Authentic. | Tests recovery or sustained alert state. |
| **`SPEAKER_TAKEOVER`** | Voiceprint abruptly changes to an unauthorized speaker mid-call. | Triggers speaker mismatch override, forcing `CHALLENGE`/`HOLD` with OOB verification. |

---

## 3. Telephony API Endpoints

### 3.1 `POST /api/v1/calls/simulate`

Launches a background telephony simulation.

#### Request Body
```json
{
  "callId": "telephony-demo-01",
  "callerNumber": "+919876543210",
  "claimedSpeaker": "Rahul Roy",
  "pattern": "AUTHENTIC_TO_CLONE",
  "totalDurationSec": 10.0,
  "chunkDurationSec": 1.0,
  "playbackSpeed": 1.0,
  "context": {
    "claimedSpeaker": "Rahul Roy",
    "transactionType": "wire-transfer",
    "transactionValueInr": 500000
  }
}
```

#### Response (202 Accepted)
```json
{
  "callId": "telephony-demo-01",
  "status": "ACTIVE",
  "pattern": "AUTHENTIC_TO_CLONE",
  "totalDurationSec": 10.0,
  "processedDurationSec": 0.0,
  "currentSegmentIndex": 0,
  "currentRiskScore": 0,
  "currentBand": "LOW",
  "currentVerdict": "AUTHENTIC",
  "recommendedAction": "ALLOW",
  "requiresOutOfBand": false,
  "riskHistory": [],
  "verdictHistory": [],
  "actionHistory": [],
  "websocketUrl": "/api/v1/ws/calls/telephony-demo-01",
  "startedAt": "2026-08-31T21:38:00Z",
  "completedAt": null
}
```

---

### 3.2 `GET /api/v1/calls/{call_id}/status`

Retrieves live call state and cumulative risk trajectory.

```http
GET /api/v1/calls/telephony-demo-01/status HTTP/1.1
```

```json
{
  "callId": "telephony-demo-01",
  "status": "INTERCEPTED",
  "pattern": "AUTHENTIC_TO_CLONE",
  "totalDurationSec": 10.0,
  "processedDurationSec": 5.0,
  "currentSegmentIndex": 5,
  "currentRiskScore": 92,
  "currentBand": "CRITICAL",
  "currentVerdict": "LIKELY_CLONE",
  "recommendedAction": "BLOCK",
  "requiresOutOfBand": true,
  "riskHistory": [8, 12, 10, 15, 92],
  "verdictHistory": ["AUTHENTIC", "AUTHENTIC", "AUTHENTIC", "AUTHENTIC", "LIKELY_CLONE"],
  "actionHistory": ["ALLOW", "ALLOW", "ALLOW", "ALLOW", "BLOCK"],
  "websocketUrl": "/api/v1/ws/calls/telephony-demo-01",
  "startedAt": "2026-08-31T21:38:00Z",
  "completedAt": "2026-08-31T21:38:05Z"
}
```

---

### 3.3 `POST /api/v1/calls/{call_id}/stop`

Manually terminates an ongoing simulated call session.

---

### 3.4 `GET /api/v1/calls?activeOnly=true`

Lists active and completed simulated call sessions.
