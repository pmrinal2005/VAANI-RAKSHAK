# VAANI-RAKSHAK — Master Backend Architecture Specification

> **Subsystem:** R2 Backend & Data Pipeline Subsystem  
> **Status:** ✅ INTEGRATION VERIFIED (10/10 Phases Complete)  
> **Overall Test Suite:** 195 Tests Passing • 85% Code Coverage • 0 Lint/Type Errors

---

## 1. Executive System Architecture

```
                                  INBOUND INGESTION
                    (REST API / Audio Upload / Telephony / WebSocket)
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │       HARDENING & SECURITY LAYER (Phase 9)    │
                 │   SecurityHeaders  •  413 RequestSizeLimit    │
                 │   429 RateLimiter  •  Server-Timing Profile   │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │       3-TIER CASCADE & SIDECARS (Phase 1, 3)  │
                 │   Tier 0 (Micro-DSP) ─── Tier 1 (AASIST-L)   │
                 │              └─── Tier 2 (Indic-W2V)          │
                 │   Sidecars: Indic LID (10 languages) & ECAPA  │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │       MULTI-MODAL FUSION & POLICY (Phase 4)   │
                 │   Calibrated Risk Score (0-100) & SHAP Expl.  │
                 │   Zero-Trust Policy Interceptor (ALLOW/BLOCK) │
                 └───────────┬───────────────────────┬───────────┘
                             │                       │
                             ▼                       ▼
      ┌──────────────────────────────┐       ┌──────────────────────────────┐
      │   KAFKA STREAMING PIPELINE   │       │ CRYPTOGRAPHIC AUDIT LEDGER   │
      │   vaani.fusion.result        │       │ Canonical SHA-256 Chaining   │
      │   vaani.risk.events          │       │ Zero-Trust Compliance Log    │
      │   vaani.workflow.events      │       │ R4 Verifiable Proof Bundles  │
      │   (Phase 2, 6)               │       │ (Phase 8)                    │
      └──────────────┬───────────────┘       └──────────────────────────────┘
                     │
                     ▼
      ┌──────────────────────────────┐
      │  REAL-TIME EVENT STREAM      │
      │  WebSocket /ws/calls/{id}    │
      │  WebSocket /ws/events (SOC)  │
      │  SSE /events/stream          │
      │  (Phase 6, 7)                │
      └──────────────────────────────┘
```

---

## 2. Phase-by-Phase Implementation Blueprint

| Phase | Subsystem Component | Implementation Details | Status |
|---|---|---|---|
| **Phase 0** | **Foundation** | FastAPI app factory, Pydantic Settings v2, structlog, 3-endpoint health probes (`/health/live`, `/health/ready`, `/health`), Docker Compose. | ✅ COMPLETE |
| **Phase 1** | **Domain Contracts & Mock Adapters** | Standardized `DetectionRequest`, `DetectionResult`, and `AudioSegment` contracts. Mock implementations for Tier 0, Tier 1, Tier 2, LID, Prosody, and ECAPA-TDNN Speaker Check. | ✅ COMPLETE |
| **Phase 2** | **Kafka Event Pipeline** | `aiokafka` producer & consumer abstractions, fallback mock pipeline, Dead Letter Queue (DLQ), retry backoff, canonical topic topology (`vaani.audio.ingest`, `vaani.detection.*`, `vaani.fusion.result`, `vaani.risk.events`, `vaani.workflow.events`). | ✅ COMPLETE |
| **Phase 3** | **Cascade Orchestration** | `CascadeOrchestrator` coordinating Tier 0 early-exit (`score < 0.22`), Tier 1 neural inference, Tier 2 deep SSL escalation (`score > 0.50` or `delta > 0.30`), high-stakes transaction bypass, and concurrent sidecar execution. | ✅ COMPLETE |
| **Phase 4** | **Fusion Engine & Risk Policy** | Calibrated integer risk score (0–100), risk bands (`LOW`, `ELEVATED`, `HIGH`, `CRITICAL`), SHAP feature attribution waterfall, and Zero-Trust `PolicyInterceptor` (`ALLOW`, `HOLD`, `CHALLENGE`, `BLOCK`). | ✅ COMPLETE |
| **Phase 5** | **Production Scoring REST API** | High-throughput `POST /api/v1/score` (JSON feature vector) and `POST /api/v1/score/upload` (multipart WAV/PCM audio) endpoints with automated Kafka emission and audit anchoring. | ✅ COMPLETE |
| **Phase 6** | **Real-Time Event Stream** | Bi-directional interactive WebSocket `/api/v1/ws/calls/{call_id}`, SOC broadcast channel `/api/v1/ws/events`, Server-Sent Events `/api/v1/events/stream`, and `KafkaStreamingBridge`. | ✅ COMPLETE |
| **Phase 7** | **Telephony Simulation Pipeline** | `CallSessionManager` and `TelephonySimulator` driving real-time RTP audio chunking with temporal risk trajectories (`STEADY`, `AUTHENTIC_TO_CLONE`, `CLONE_BURST`, `SPEAKER_TAKEOVER`) and automated zero-trust `BLOCK` interception. | ✅ COMPLETE |
| **Phase 8** | **Cryptographic Audit Ledger** | `CryptographicAuditLedger` providing canonical SHA-256 hash chaining, privacy guarantees (raw audio never stored), full-chain verification (`verify_chain`), and `AuditProofBundle` generation for R4 blockchain anchoring. | ✅ COMPLETE |
| **Phase 9** | **Reliability & Security Hardening** | `RequestSizeLimitMiddleware` (413), in-memory `TokenBucketRateLimiter` (429), `SecurityHeadersMiddleware`, asynchronous `CircuitBreaker` pattern, `ProfilingMiddleware` (`Server-Timing`), and WebSocket flood protection. | ✅ COMPLETE |
| **Phase 10** | **Final Integration Verification** | Comprehensive end-to-end integration test suite (`tests/integration/test_e2e_pipeline.py`) validating cross-subsystem correlation and live pipeline flows. | ✅ COMPLETE |

---

## 3. Component Status & Dependency Matrix

```
┌────────────────────────────────────────────────────────────────────────┐
│                        R2 BACKEND SUBSYSTEM                            │
│  FastAPI API Layer:           ✅ IMPLEMENTED & VERIFIED                │
│  Cascade Orchestrator:        ✅ IMPLEMENTED & VERIFIED                │
│  Fusion & Risk Engine:        ✅ IMPLEMENTED & VERIFIED                │
│  Zero-Trust Policy:           ✅ IMPLEMENTED & VERIFIED                │
│  Kafka Event Pipeline:        ✅ IMPLEMENTED & VERIFIED                │
│  Telephony Simulation:        ✅ IMPLEMENTED & VERIFIED                │
│  Cryptographic Audit Ledger:  ✅ IMPLEMENTED & VERIFIED                │
│  Security & Hardening:        ✅ IMPLEMENTED & VERIFIED                │
│  Automated Test Suite:        ✅ 195/195 PASSING (85% COVERAGE)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         │                                                     │
         ▼                                                     ▼
┌─────────────────────────────────┐   ┌──────────────────────────────────┐
│     R1 ML DETECTION BOUNDARY    │   │    R4 BLOCKCHAIN TRUST BOUNDARY  │
│  Tier 0 (Micro-DSP ONNX):  🟡   │   │  Hyperledger Fabric:        🔒   │
│  Tier 1 (AASIST-L ONNX):   🟡   │   │  Consortium Chaincode:      🔒   │
│  Tier 2 (Indic-W2V):       🟡   │   │  Flower Federated Learning: 🔒   │
│  Indic LID & ECAPA:        🟡   │   │  Opacus Differential Priv.: 🔒   │
│  [Protocols Defined & Ready]    │   │  [AuditProofBundles Ready]       │
└─────────────────────────────────┘   └──────────────────────────────────┘
```

> **Legend:**
> - ✅ **Implemented & Verified:** Fully functional, hardened, and regression-tested in R2.
> - 🟡 **Mocked & Protocol Ready:** Clean Python `Protocol` interfaces exist in R2; ready for R1 ONNX/Torch model artifact injection without code rewriting.
> - 🔒 **Integration Interface Ready:** Cryptographic SHA-256 proof bundle boundary defined in R2; ready for R4 Hyperledger Fabric consortium anchoring.

---

## 4. Middleware Pipeline Order (`app/main.py`)

Requests traverse the following pipeline in deliberate order:
1. **`SecurityHeadersMiddleware`**: Injects `X-Content-Type-Options`, `X-Frame-Options`, `CSP`, `Referrer-Policy`, and environment-aware `Strict-Transport-Security`.
2. **`ProfilingMiddleware`**: Measures backend execution latency with a monotonic clock, injecting `X-Response-Time` and `Server-Timing`.
3. **`RequestSizeLimitMiddleware`**: Rejects requests exceeding `MAX_REQUEST_SIZE_MB` with `HTTP 413 Payload Too Large` before memory buffering.
4. **`RateLimitMiddleware`**: In-memory sliding token bucket rejecting excessive requests with `HTTP 429 Too Many Requests` and `Retry-After`.
5. **`TrustedHostMiddleware`**: Protects against Host header injection.
6. **`CORSMiddleware`**: Manages browser origin access.
7. **`RequestIDMiddleware`**: Binds unique `X-Request-ID` to structlog contextvars.
8. **Route Dispatchers**: `/score`, `/calls`, `/audit`, `/health`, `/ws/*`.
