# VAANI-RAKSHAK — 3-Tier Cascade Orchestration Engine

## Overview

The Cascade Orchestrator (`app/cascade/orchestrator.py`) executes multi-tiered voice countermeasure evaluation with cost-aware early-exit mechanisms, non-blocking parallel sidecar extraction, and resilient error degradation.

```
                      ┌────────────────────────────┐
                      │    Incoming Audio Segment  │
                      └──────────────┬─────────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │                   │                   │
                 ▼                   ▼                   ▼
          ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
          │   Prosody   │     │   Speaker   │     │  Indic LID  │
          │  Biomarkers │     │ Verification│     │ & Routing   │
          └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
                 │                   │                   │
                 └───────────────────┼───────────────────┘ (Parallel async sidecars)
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │   Tier 0: Micro-DSP  │ (< 3ms)
                          └──────────┬───────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │ Score < 0.22, Conf >= 0.85,   │
                     │ Low-Stakes & not forced?      │
                     └───┬───────────────────────┬───┘
                    YES  │                       │ NO
                         ▼                       ▼
                  ┌──────────────┐      ┌─────────────────┐
                  │  Early Exit  │      │  Tier 1: AASIST │ (< 20ms)
                  │ (AUTHENTIC)  │      └────────┬────────┘
                  └──────────────┘               │
                                  ┌──────────────┴──────────────┐
                                  │ Score < 0.35, |T1-T0| < 0.30│
                                  │ Low-Stakes & not forced?    │
                                  └───┬─────────────────────┬───┘
                                 YES  │                     │ NO (Escalate)
                                      ▼                     ▼
                               ┌──────────────┐    ┌─────────────────┐
                               │  Early Exit  │    │  Tier 2: SSL    │ (< 100ms)
                               │ (AUTHENTIC)  │    │ IndicWav2Vec+LoRA│
                               └──────────────┘    └────────┬────────┘
                                                            │
                                     ┌──────────────────────┘
                                     ▼
                          ┌──────────────────────┐
                          │     FusionInput      │
                          │      Collection      │
                          └──────────────────────┘
```

---

## 1. Execution Tiers & Early-Exit Criteria

| Tier | Engine / Model | Target Latency | Early-Exit Criteria |
|---|---|---|---|
| **Tier 0** | Micro-DSP spectral heuristics | < 3 ms | `score < 0.22` AND `confidence >= 0.85` AND not high stakes AND not `force_tier2` |
| **Tier 1** | Compact Neural (AASIST-L) | < 20 ms | `score < 0.35` AND `\|T1 - T0\| < 0.30` AND not high stakes AND not `force_tier2` |
| **Tier 2** | Deep Multilingual SSL (IndicWav2Vec + LoRA) | < 100 ms | Terminal tier. Runs when escalated by disagreement, high stakes, or high Tier 1 score. |

---

## 2. Escalation Triggers for Deep SSL (Tier 2)

Tier 2 is invoked when **any** of the following conditions are met:
1. **Tier Disagreement:** `|t1_score - t0_score| > 0.30`.
2. **High Transaction Value:** `transaction_value_inr >= 200,000 INR`.
3. **High Stakes Workflow:** `transaction_type` matches transfer, wire, recovery, OTP, or KYC.
4. **Unknown Contact:** `known_contact == False`.
5. **Manual Flag:** `request.force_tier2 == True`.
6. **Tier 1 Degradation:** Tier 1 timeout or model execution error.

---

## 3. Sidecar Analytics (Concurrent Execution)

The following sidecars run concurrently via `asyncio.create_task` during the cascade:
- **Prosody Detector (`ProsodyDetector`):** F0 contour range, vocal fold jitter suppression, shimmer regularity.
- **Speaker Verifier (`SpeakerVerifier`):** ECAPA-TDNN embedding extraction and cosine similarity comparison against enrolled caller identity.
- **Language Router (`LanguageRouter`):** 12 Indic languages + Code-Switching detection, selecting target LoRA adapter configuration for Tier 2.

---

## 4. Timeout Budgets & Graceful Degradation

| Tier | Timeout Budget | Degradation Behavior |
|---|---|---|
| **Tier 0** | 100 ms | Sets `status=TIMEOUT`, `confidence=0.0`, score=0.50, escalates to Tier 1 |
| **Tier 1** | 500 ms | Sets `status=TIMEOUT`, `confidence=0.0`, score=0.50, escalates to Tier 2 |
| **Tier 2** | 1500 ms | Sets `status=TIMEOUT`, `confidence=0.50`, falls back to Tier 1 score |
| **Sidecars** | Background | On error/timeout, returns fallback neutral vote / unverified flag without stalling cascade |
