# VAANI-RAKSHAK — R2 Backend & Data Pipeline Subsystem

**VAANI-RAKSHAK** (वाणी-रक्षक — *Guardian of Voice*) is a real-time, multi-modal, zero-trust voice-cloning detection framework engineered for enterprise banking telephony and digital verification channels.

The **R2 Subsystem** owns the complete backend application, asynchronous event streaming pipeline, cascade orchestration, multi-modal risk fusion, telephony simulation, cryptographic audit ledger, and security hardening layer.

---

## Architecture Overview

```
                                  INBOUND INGESTION
                    (REST API / Audio Upload / Telephony / WebSocket)
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │          HARDENING & DEFENSE-IN-DEPTH         │
                 │   SecurityHeaders  •  413 RequestSizeLimit    │
                 │   429 RateLimiter  •  Server-Timing Profile   │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │       3-TIER CASCADE & SIDECARS (R2 Core)     │
                 │   Tier 0 (Micro-DSP) ─── Tier 1 (AASIST-L)   │
                 │              └─── Tier 2 (Indic-W2V)          │
                 │   Sidecars: Indic LID (10 languages) & ECAPA  │
                 └───────────────────────┬───────────────────────┘
                                         │
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │          MULTI-MODAL FUSION & POLICY          │
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
      └──────────────┬───────────────┘       └──────────────────────────────┘
                     │
                     ▼
      ┌──────────────────────────────┐
      │     REAL-TIME EVENT STREAM   │
      │   WebSocket /ws/calls/{id}   │
      │   WebSocket /ws/events (SOC) │
      │   SSE /events/stream         │
      └──────────────────────────────┘
```

---

## Subsystem Responsibilities & Scope Boundaries

| Role | Subsystem | Ownership & Current Status |
|---|---|---|
| **R1** | **ML / Audio Detection** | Tier 0/1/2 ONNX backbones, LoRA multilingual adapters, acoustic prosody. *(R1 model artifacts mocked in R2 test harness; pending real model delivery)* |
| **R2** | **Backend & Data Pipeline** | **COMPLETE (10/10 Phases)**: FastAPI, Cascade Orchestrator, LightGBM Fusion, Zero-Trust Policy, Kafka Pipeline, Telephony Simulation, Audit Ledger, Security Hardening. |
| **R3** | **Frontend & Alerting** | Real-time agent dashboard, SHAP waterfall visualizer, Out-of-band challenge modals. |
| **R4** | **Blockchain & Privacy** | Hyperledger Fabric consortium chaincode, Flower federated learning, Opacus differential privacy. *(R2 exports clean `AuditProofBundle` interfaces; pending R4 infra)* |

---

## Getting Started

### 1. Prerequisites
- **Python:** 3.12+
- **Package Manager:** `pip` / `uv`
- **Virtual Environment:** Recommended `.venv`

### 2. Installation
```powershell
# Navigate to backend directory
cd backend

# Create virtual environment & activate
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```

### 4. Running the Development Server
```powershell
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation is available at `http://localhost:8000/api/v1/docs`.

---

## Verification & Quality Assurance

```powershell
# Run full automated test suite (195 tests, 85% coverage)
.venv\Scripts\python -m pytest tests/ --cov=app --cov-report=term-missing

# Static analysis & linting
.venv\Scripts\ruff check app/ tests/

# Strict static type checking
.venv\Scripts\mypy app/
```

---

## REST API & WebSocket Endpoint Reference

### Health & Observability
| Method | Endpoint | Description |
|---|---|---|
| **`GET`** | `/api/v1/health/live` | Kubernetes liveness probe |
| **`GET`** | `/api/v1/health/ready` | Kubernetes readiness probe (Kafka & subsystem dependencies) |
| **`GET`** | `/api/v1/health` | Comprehensive health check status |

### Production Scoring
| Method | Endpoint | Description |
|---|---|---|
| **`POST`** | `/api/v1/score` | JSON feature vector & metadata detection scoring |
| **`POST`** | `/api/v1/score/upload` | Multipart WAV/PCM audio upload and scoring |

### Real-Time Event Streaming
| Method | Endpoint | Description |
|---|---|---|
| **`WS`** | `/api/v1/ws/calls/{call_id}` | Bi-directional interactive audio chunk analysis stream |
| **`WS`** | `/api/v1/ws/events` | SOC broadcast WebSocket channel for fraud investigators |
| **`GET`** | `/api/v1/events/stream` | Server-Sent Events (SSE) risk feed |

### Telephony Simulation
| Method | Endpoint | Description |
|---|---|---|
| **`POST`** | `/api/v1/calls/simulate` | Launch background simulated telephony call with temporal risk |
| **`GET`** | `/api/v1/calls` | List active simulation sessions |
| **`GET`** | `/api/v1/calls/{call_id}/status` | Query session cumulative risk trajectory & verdict history |
| **`POST`** | `/api/v1/calls/{call_id}/stop` | Terminate active telephony simulation |

### Cryptographic Audit Ledger (R4 Boundary)
| Method | Endpoint | Description |
|---|---|---|
| **`GET`** | `/api/v1/audit/blocks` | Query paginated cryptographic blocks |
| **`GET`** | `/api/v1/audit/blocks/{block_index}` | Inspect single block by monotonic index |
| **`GET`** | `/api/v1/audit/calls/{call_id}` | Retrieve complete immutable audit trail for a call session |
| **`GET`** | `/api/v1/audit/verify` | Comprehensive SHA-256 chain integrity verification |
| **`GET`** | `/api/v1/audit/proof/{call_id}` | Export verifiable proof bundle for R4 blockchain anchoring |
