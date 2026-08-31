Given the architecture's natural fault lines (ML/audio, backend/data infra, frontend/UX+alerting, blockchain/privacy/DevOps), the cleanest split is:

| Role | Member | Owns |
|---|---|---|
| **R1 — ML/Audio Detection Lead** | Member A | Tier 0, Tier 1, Tier 2 detection models, multilingual adapters |
| **R2 — Backend/Data Pipeline Lead** | Member B | Fusion engine, APIs, Kafka, telephony/SIP integration |
| **R3 — Frontend/Workflow & Alerting Lead** | Member C | Dashboard, alerting, OOB workflow, SHAP visualization |
| **R4 — Blockchain/Privacy/DevOps Lead** | Member D | Hyperledger Fabric, Flower/Opacus, Docker/K3s, monitoring |

---

### **Member A — ML/Audio Detection Lead**
*Owns everything that turns raw audio into a score.*

**Phase 0:** Download/validate AASIST, AASIST-L, SSL-AASIST, AASIST3, IndicWav2Vec, RawNet2 checkpoints; curate IndicSynth/IndicVoices-R/InDeepFake subsets.
**Phase 1:** Build Tier 0 DSP feature extractors (CQCC/LFCC/spectral flatness/phase discontinuity); quantize AASIST-L to INT8 ONNX/TFLite; build streaming chunk wrapper with rolling cache.
**Phase 2:** Integrate IndicWav2Vec + AASIST3 backbone for Tier 2; train LoRA adapters per language; build/integrate IndicLID router with soft top-2 ensemble for code-switching.
**Phase 3:** Build prosody branch (Parselmouth/openSMILE) and ECAPA-TDNN speaker-embedding module (SpeechBrain) with cosine similarity scoring.
**Phase 5:** Provide model artifacts for Flower federated learning rounds; validate DP-noised updates don't collapse accuracy.
**Phase 7:** Run all EER/accuracy benchmarks per tier/per language; write the detection-accuracy section of the final report.

---

### **Member B — Backend/Data Pipeline Lead**
*Owns the plumbing that moves audio and scores through the system.*

**Phase 0:** Set up Kafka single-node cluster; scaffold FastAPI service skeletons; define gRPC/REST contracts between tiers.
**Phase 1–2:** Wire Tier 0/1/2 modules (from Member A) into Kafka topics/FastAPI endpoints so they can be called as services.
**Phase 3:** Build the LightGBM fusion engine consuming the 4 signal streams + contextual metadata (ANI reputation, transaction amount, historical flags); integrate SHAP for explanations; expose `/score` API.
**Phase 4:** Build backend logic for threshold configuration per workflow type and trigger events to the alerting layer.
**Phase 6:** Integrate FreeSWITCH/Kamailio-RTPengine to stream live RTP into Kafka; own end-to-end pipeline orchestration and latency profiling.
**Phase 7:** Load-test Kafka/API throughput; document API contracts and data-flow diagrams.

---

### **Member C — Frontend/Workflow & Alerting Lead**
*Owns everything the human (agent, analyst, regulator) sees and interacts with.*

**Phase 0:** Scaffold React/Next.js project; design UI wireframes for agent-desktop risk dashboard.
**Phase 3:** Build UI components to render risk score (0–100) + SHAP "why" explanation in human-readable form.
**Phase 4:** Implement WebSocket/SSE live score feed; build mandatory out-of-band confirmation workflow UI (codeword entry, secondary-channel confirmation simulation); implement configurable threshold controls in the UI for admins.
**Phase 5:** Build a simple "audit trail viewer" that queries the Hyperledger Fabric ledger (via Member D's exposed endpoints) and displays tamper-evident incident history to a regulator/analyst persona.
**Phase 6:** Integrate dashboard with the live Kafka-driven pipeline for real-time demo.
**Phase 7:** Polish UI/UX for demo, script and record the walkthrough, prepare presentation slides/architecture visuals.

---

### **Member D — Blockchain/Privacy/DevOps Lead**
*Owns trust infrastructure, privacy guarantees, and deployment.*

**Phase 0:** Stand up Hyperledger Fabric test network (`fabric-samples`) simulating bank/telecom/regulator orgs; set up Docker/K3s cluster shell.
**Phase 3:** Design the on-chain data schema (consent hashes, risk-score+SHAP packet hashes, escalation logs) — coordinate with Member B on what gets hashed and when.
**Phase 5:** Write chaincode/smart contracts for consent logging, risk-event logging, and the two-factor-OOB approval gate; wire backend submission of SHA-256 hashes to Fabric after each scored call; set up Flower federated-learning coordinator across simulated nodes; layer Opacus differential privacy on gradient updates.
**Phase 6:** Containerize all services (Docker), deploy on K3s, set up Prometheus/Grafana dashboards tracking per-tier invocation rates, latency, and CPU overhead.
**Phase 7:** Run Fabric throughput/latency benchmarks; write the privacy/compliance and blockchain-audit sections of the final report; ensure DPDP Act data-minimization claims are verifiable in the deployed system (raw audio never leaves edge nodes).

---

## CROSS-CUTTING COORDINATION NOTES

- **Weekly integration checkpoint** (all 4 members): merge Tier 0/1/2 outputs (A) → fusion API (B) → dashboard (C) → ledger (D) into one running docker-compose stack, so integration debt never piles up till the end.
- **Interface contracts must be frozen early**: Member A and B should agree on the exact JSON schema for tier scores by end of Phase 1; Member B and D should agree on the hash-payload schema by end of Phase 3; Member B and C should agree on the WebSocket event schema by end of Phase 3.
- **Shared responsibility on Phase 7**: benchmarking, documentation, and demo packaging should be a joint sprint, each member writing the section of the report/demo corresponding to their owned subsystem, since the "self-verification checklist" nature of this project rewards traceable, per-component evidence rather than one person's narrative.

This division keeps each member's workload roughly balanced (each owns 1 major subsystem end-to-end), avoids idle time (Phases overlap so no one waits on another for weeks), and ensures a demoable system exists as early as Phase 4, with the more "impressive but riskier" layers (blockchain, federated learning, multilingual adapters) added incrementally on top of a working core — reducing the risk of a non-functional final demo.