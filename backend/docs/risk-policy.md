# VAANI-RAKSHAK — Multi-Modal Evidence Fusion & Risk Policy Engine

## Overview

The Multi-Modal Fusion Engine (`app/fusion/engine.py`) and Enterprise Policy Engine (`app/fusion/policy.py`) provide categorical voice risk assessment, feature attribution explainability, and automated banking interceptor decisioning.

---

## 1. Multi-Modal Evidence Fusion Weights

The fusion engine combines multi-modal signals into a non-linear calibrated 0–100 integer risk score:

$$\text{Raw Score} = 0.55 \cdot \text{AcousticFloor} + 0.15 \cdot \text{ProsodyScore} + 0.15 \cdot \text{SpeakerPenalty} + 0.15 \cdot \text{ContextRisk}$$

- **Acoustic Floor:** $\max(T0, \text{ActiveNeuralCM})$
- **Non-Linear Deepfake Boost:** If $\text{AcousticFloor} \ge 0.70$, score is reinforced to prevent false negatives.

---

## 2. Categorical Risk Bands & Verdicts

| Risk Score | Risk Band | Verdict | Typical Action | Out-of-Band Trigger |
|---|---|---|---|---|
| **0 – 39** | `LOW` | `AUTHENTIC` | `ALLOW` | No |
| **40 – 64** | `ELEVATED` | `SUSPICIOUS` | `CHALLENGE` / `ALLOW_MONITORED` | Yes (if high-value/transfer) |
| **65 – 84** | `HIGH` | `LIKELY_CLONE` | `HOLD` | Yes (Mandatory) |
| **85 – 100** | `CRITICAL` | `LIKELY_CLONE` | `BLOCK` / `HOLD` | Yes (Mandatory) |

---

## 3. Enterprise Banking Policy & Interceptor Rules

```
                      ┌────────────────────────────┐
                      │        FusionOutput        │
                      └──────────────┬─────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │ Speaker Mismatch Detected?            │
                 └───┬───────────────────────────────┬───┘
                YES  │                               │ NO
                     ▼                               ▼
       ┌───────────────────────────┐    ┌───────────────────────────┐
       │ Critical Risk + Transfer? │    │ Evaluate Risk Band        │
       └───┬───────────────────┬───┘    └────────────┬──────────────┘
      YES  │               NO  │                     │
           ▼                   ▼                     ▼
    ┌─────────────┐     ┌─────────────┐        ┌─────────────┐
    │    BLOCK    │     │  CHALLENGE  │        │ CRITICAL:   │ ──> BLOCK (Transfer) / HOLD (Inquiry)
    │ (Immediate) │     │ (Step-up OOB│        │ HIGH:       │ ──> HOLD (Supervisor Queue)
    └─────────────┘     └─────────────┘        │ ELEVATED:   │ ──> CHALLENGE (High Stakes) / ALLOW
                                               │ LOW:        │ ──> ALLOW
                                               └─────────────┘
```

### Policy Rule Table

| Rule ID | Condition | Action Code | Decision | Out-of-Band | Rationale |
|---|---|---|---|---|---|
| `RULE_SEC_01` | Speaker mismatch + Critical Risk + High Stakes | `INTERCEPT_BLOCK_SPEAKER_MISMATCH_CRITICAL` | **`BLOCK`** | **YES** | Immediate block: Biometric mismatch combined with critical clone risk during sensitive transfer. |
| `RULE_SEC_02` | Speaker mismatch on any interaction | `INTERCEPT_CHALLENGE_SPEAKER_MISMATCH` | **`CHALLENGE`** | **YES** | Step-up biometric challenge: Voiceprint does not match enrolled profile baseline. |
| `RULE_RISK_01` | `CRITICAL` risk ($\ge 85$) + High Stakes / Transfer | `INTERCEPT_BLOCK_CRITICAL_FRAUD` | **`BLOCK`** | **YES** | High-probability voice clone detected on financial operation. |
| `RULE_RISK_02` | `CRITICAL` risk ($\ge 85$) on non-financial interaction | `INTERCEPT_HOLD_CRITICAL_REVIEW` | **`HOLD`** | **YES** | Routed to fraud queue awaiting manual investigator sign-off. |
| `RULE_RISK_03` | `HIGH` risk ($65 - 84$) | `INTERCEPT_HOLD_SUPERVISOR` | **`HOLD`** | **YES** | Multiple acoustic and prosodic indicators suggest voice synthesis. |
| `RULE_RISK_04` | `ELEVATED` risk ($40 - 64$) + High Stakes | `INTERCEPT_CHALLENGE_STEPUP_OTP` | **`CHALLENGE`** | **YES** | Step-up OTP or out-of-band verification required. |
| `RULE_RISK_05` | `ELEVATED` risk ($40 - 64$) + Low Stakes | `INTERCEPT_ALLOW_MONITORED` | **`ALLOW`** | **NO** | Allowed with enhanced telemetry monitoring. |
| `RULE_RISK_06` | `LOW` risk + Unknown Caller Number | `INTERCEPT_ALLOW_UNVERIFIED_CALLER` | **`ALLOW`** | **NO** | Authentic voice characteristics from unverified caller ANI. |
| `RULE_RISK_07` | `LOW` risk + Known Contact | `INTERCEPT_ALLOW_AUTHENTIC` | **`ALLOW`** | **NO** | Authentic biological voice confirmed. |

---

## 4. Transparent Explainability (XAI)

Feature attributions explain how each evidence stream influenced the final score:
- **Voiced spectral texture:** Spectral flatness & HF energy ratio.
- **Neural countermeasure:** Compact and multilingual graph activations.
- **Prosody / micro-tremor:** Pitch variability (F0 range), jitter, and shimmer.
- **Speaker voiceprint:** ECAPA-TDNN embedding cosine distance.
- **Call context:** ANI reputation and transaction value risk factor.
