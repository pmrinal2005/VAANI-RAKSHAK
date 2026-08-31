# VAANI-RAKSHAK — Real-Time Streaming & Kafka Bridge (`WebSocket & SSE`)

## Overview

VAANI-RAKSHAK exposes bi-directional WebSockets and Server-Sent Events (SSE) for low-latency live audio stream scoring, real-time SOC risk monitoring, and supervisor interception telemetry.

---

## 1. Architecture & Kafka Event Bridge

```
                     ┌────────────────────────────────────────────────────────┐
                     │                   FastAPI Application                  │
                     │                                                        │
  Live Audio Chunk ──┼──> WebSocket /api/v1/ws/calls/{call_id}                │
  (Base64 PCM)       │            │                                           │
                     │            ▼                                           │
                     │    CascadeOrchestrator ──> MultiModalFusionEngine      │
                     │                                 │                      │
                     │                                 ▼                      │
                     │                           EventProducer                │
                     │                                 │                      │
                     │                                 ▼                      │
                     │                           Kafka Topics                 │
                     │                           ├── vaani.fusion.result      │
                     │                           ├── vaani.risk.events        │
                     │                           └── vaani.workflow.events    │
                     │                                 │                      │
                     │                                 ▼                      │
                     │                           EventConsumer                │
                     │                                 │                      │
                     │                                 ▼                      │
                     │                       KafkaStreamingBridge             │
                     │                                 │                      │
                     │                                 ▼                      │
                     │                         ConnectionManager              │
                     │                           ├── Call Rooms               │
                     │                           ├── Global Broadcast         │
                     │                           └── SSE Listeners            │
                     │                                 │                      │
  Call Room Feed ────┼──<── WebSocket /ws/calls/{id} ──┤                      │
  SOC Dashboard ─────┼──<── WebSocket /ws/events ──────┤                      │
  Live Feed (SSE) ───┼──<── GET /events/stream ────────┘                      │
                     └────────────────────────────────────────────────────────┘
```

---

## 2. Endpoints

### 2.1 `WebSocket /api/v1/ws/calls/{call_id}`

Interactive bi-directional stream for an active telephone call.

#### Client to Server: Audio Chunk Message
```json
{
  "type": "audio_chunk",
  "request": {
    "segment": {
      "callId": "call-123",
      "segmentId": "seg-001",
      "rawPcmB64": "UklGRi4AAABXQVZFZm10...",
      "features": {
        "spectralFlatnessVoiced": 0.35,
        "hfEnergyRatio": 0.12,
        "jitter": 0.0009,
        "shimmer": 0.005,
        "f0RangeHz": 12.0
      }
    },
    "context": {
      "claimedSpeaker": "Priya Sharma",
      "transactionType": "wire-transfer",
      "transactionValueInr": 350000
    },
    "scenarioOverride": "CRITICAL_RISK"
  }
}
```

#### Server to Client: Detection Result Message
```json
{
  "type": "detection_result",
  "callId": "call-123",
  "payload": {
    "fusedScore": 0.88,
    "riskScore": 88,
    "band": "CRITICAL",
    "verdict": "LIKELY_CLONE",
    "recommendedAction": "BLOCK",
    "requiresOutOfBand": true,
    "smartExplanation": "Critical risk voice clone flagged primarily by Neural countermeasure.",
    "totalLatencyMs": 42.1
  }
}
```

---

### 2.2 `WebSocket /api/v1/ws/events`

Global broadcast channel for SOC dashboards, fraud investigator consoles, and security analytics.

#### Server to Client: Broadcast Envelope
```json
{
  "header": {
    "eventId": "01M1C8TH38DD87XW3BK7F5SWQM",
    "correlationId": "call-123",
    "eventType": "risk.events",
    "occurredAt": "2026-08-31T21:30:00Z"
  },
  "payload": {
    "callId": "call-123",
    "riskScore": 88,
    "band": "CRITICAL",
    "verdict": "LIKELY_CLONE",
    "requiresOutOfBand": true,
    "explanation": "Critical risk voice clone flagged primarily by Neural countermeasure."
  }
}
```

---

### 2.3 `GET /api/v1/events/stream` (Server-Sent Events)

HTTP `EventSource` compatible streaming endpoint returning `text/event-stream`.

```http
GET /api/v1/events/stream HTTP/1.1
Accept: text/event-stream
```

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: ping
data: {"status": "connected"}

event: risk.events
data: {"header": {"eventId": "..."}, "payload": {"callId": "call-123", "riskScore": 88, ...}}
```
