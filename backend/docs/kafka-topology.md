# VAANI-RAKSHAK — Kafka Streaming & Topic Topology

## Overview

VAANI-RAKSHAK uses Apache Kafka (`aiokafka`) for asynchronous, event-driven audio ingestion, multi-tiered detection dispatch, fusion aggregation, and tamper-evident audit ledger anchoring.

---

## 1. Canonical Topic Topology

All topics support dynamic environment prefixing via `TopicManager` (`vaani.<topic_name>` by default, configurable via `KAFKA_TOPIC_PREFIX`).

| Topic Name | Purpose | Message Key | Payload Schema | Retention |
|---|---|---|---|---|
| `vaani.audio.ingest` | Inbound telephony/upload audio capture | `call_id` | `AudioIngestPayload` | 24 hours |
| `vaani.audio.segment` | Discrete 2-second audio chunks for analysis | `call_id` | `AudioSegmentPayload` | 12 hours |
| `vaani.detection.tier0` | Micro-DSP fast pre-filter scores | `call_id` | `TierDetectionPayload` | 12 hours |
| `vaani.detection.tier1` | Compact neural countermeasure (AASIST-L) | `call_id` | `TierDetectionPayload` | 12 hours |
| `vaani.detection.tier2` | Deep multilingual SSL (IndicWav2Vec) | `call_id` | `TierDetectionPayload` | 12 hours |
| `vaani.detection.prosody` | Behavioural biomarker analysis | `call_id` | `ProsodyPayload` | 12 hours |
| `vaani.detection.speaker` | Cross-session speaker verification | `call_id` | `SpeakerPayload` | 12 hours |
| `vaani.fusion.result` | Multi-modal fused risk assessment | `call_id` | `FusionResultPayload` | 7 days |
| `vaani.risk.events` | Downstream dashboard & high-risk alerts | `call_id` | `RiskEventPayload` | 30 days |
| `vaani.workflow.events` | Interceptor actions (ALLOW, BLOCK, HOLD, CHALLENGE) | `call_id` | `WorkflowEventPayload` | 90 days |
| `vaani.audit.events` | Blockchain / hash-chain anchoring events | `call_id` | `AuditEventPayload` | Permanent (compacted) |
| `vaani.deadletter` | Unprocessable or poison-pill message queue | `call_id` | `DeadLetterPayload` | 30 days |

---

## 2. Partitioning & Ordering Guarantee

To maintain strict causal order during streaming calls (e.g. Segment 0 -> Segment 1 -> Fusion -> Escalation):
- **Partition Key:** `correlation_id` (`call_id`).
- **Guarantee:** All events belonging to the same call session land on the exact same Kafka partition and are processed strictly sequentially by consumer worker tasks.

---

## 3. Producer Guarantees

- **Idempotence:** `enable_idempotence=True` avoids duplicate messages on network retries.
- **Durability:** `acks="all"` ensures all in-sync replicas acknowledge before proceeding.
- **Compression:** Optional gzip/snappy compression for high-throughput batching.
- **Dead-Letter Routing:** Messages that exceed exponential retry attempts (`stop_after_attempt(3)`) are automatically routed to `vaani.deadletter`.

---

## 4. Dual Operation Modes

1. **Production Mode (`AIOKafkaEventProducer` & `AIOKafkaEventConsumer`):**
   - Connects to Kafka broker specified in `KAFKA_BOOTSTRAP_SERVERS` (`localhost:9092`).
   - Uses manual offset commits after handler completion.
2. **Development / Test Mode (`MockEventProducer` & `MockEventConsumer`):**
   - Zero external dependencies.
   - Operates in-memory using thread-safe FIFO queues and async callbacks.
   - Automatically engaged when running unit tests or when `DETECTION_MODE=mock`.
