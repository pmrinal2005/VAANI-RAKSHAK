# VAANI-RAKSHAK — Reliability, Security & Performance Hardening Specification

## Overview

Phase 9 equips the VAANI-RAKSHAK R2 backend with production-grade defense-in-depth security, sliding token bucket rate limiting, payload size protections, asynchronous circuit breakers, and sub-millisecond response latency profiling.

---

## 1. Security Headers & Payload Size Protection (`app/core/security.py`)

### 1.1 HTTP Security Headers
Every HTTP response, including error responses, is decorated with standard defense-in-depth headers:
- `X-Content-Type-Options: nosniff` (prevents MIME sniffing)
- `X-Frame-Options: DENY` (clickjacking protection)
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`
- `X-XSS-Protection: 0` (modern standard disables legacy buggy reflective XSS filters)
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (enabled when `ENABLE_HSTS=true` behind HTTPS)

### 1.2 Request Size Limiter (`RequestSizeLimitMiddleware`)
- Rejects requests whose `Content-Length` exceeds `MAX_REQUEST_SIZE_MB` (default: 50MB) immediately with `HTTP 413 Payload Too Large`.
- Protects memory against buffer exhaustion before body consumption.

---

## 2. In-Memory Token Bucket Rate Limiting (`app/core/rate_limit.py`)

### 2.1 Sliding Window Token Bucket
- Process-local token bucket per client IP (derived from `X-Forwarded-For` or client host).
- Configured via:
  - `RATE_LIMIT_REQUESTS_PER_MINUTE`: Token replenishment rate (default: 120 rpm = 2 tokens/sec).
  - `RATE_LIMIT_BURST_CAPACITY`: Maximum burst tokens (default: 30).
- Exceeded rate limits return `HTTP 429 Too Many Requests` with a `Retry-After: <seconds>` header.
- Health endpoints (`/health/*`) bypass the rate limiter.

> **Process-Local State Limitation:**
> The current rate limiter is process-local. In a multi-replica deployment, each replica maintains its own token bucket state. Distributed rate limiting (e.g. Redis) is outside Phase 9.

---

## 3. Real-Time WebSocket Protection (`app/api/routes/streaming.py`)

Interactive WebSockets (`/api/v1/ws/calls/{call_id}` and `/api/v1/ws/events`) enforce:
1. **Message Size Limit:** Messages exceeding `WS_MAX_MESSAGE_SIZE_MB` (5MB) receive an error response.
2. **Audio Chunk Size Limit:** Audio payloads exceeding `MAX_AUDIO_CHUNK_SIZE_MB` (10MB) are safely rejected.
3. **Message Rate Limit:** Clients sending more than `WS_MAX_MESSAGES_PER_SECOND` (20 msg/sec) are throttled with `RATE_LIMIT_EXCEEDED` errors without terminating valid ongoing sessions.

---

## 4. Asynchronous Circuit Breaker Pattern (`app/core/circuit_breaker.py`)

Protects external dependencies (Kafka brokers, telephony gateways, ML inference engines) from cascading failure storms.

```
                    ┌────────────────────────┐
                    │         CLOSED         │◄────────────────┐
                    │ (All requests execute) │                 │
                    └───────────┬────────────┘                 │
                                │ Failures >= threshold        │ Trials succeed
                                ▼                              │
                    ┌────────────────────────┐                 │
                    │          OPEN          │                 │
                    │  (Fast-fails requests) │                 │
                    └───────────┬────────────┘                 │
                                │ Elapsed >= recovery_timeout  │
                                ▼                              │
                    ┌────────────────────────┐                 │
                    │       HALF_OPEN        ├─────────────────┘
                    │ (Limited probe trials) │
                    └───────────┬────────────┘
                                │ Any probe fails
                                ▼
                             (To OPEN)
```

### Circuit Breaker States & Transitions
- **`CLOSED`**: Requests proceed normally. Consecutive failures increment `_failure_count`. If `_failure_count >= failure_threshold` (default: 5), transitions to `OPEN`.
- **`OPEN`**: Immediately raises `CircuitBreakerOpenError` (or executes optional `fallback`). When `elapsed_time >= recovery_timeout_sec` (default: 30.0s), transitions to `HALF_OPEN`.
- **`HALF_OPEN`**: Permits up to `half_open_max_trials` (default: 3) probe trials. If all succeed, resets and returns to `CLOSED`. If any probe fails, immediately trips back to `OPEN`.

---

## 5. Request Latency Profiling (`app/core/profiling.py`)

- Injects response headers:
  - `X-Response-Time: <ms>ms` (monotonic clock measurement of backend execution time).
  - `Server-Timing: total;dur=<ms>` (standard W3C server-timing specification).
- Structured warning log emitted when request duration exceeds `SLOW_REQUEST_THRESHOLD_MS` (default: 500ms).
- **Privacy Assurance:** Latency logs never contain raw audio, request bodies, or credentials.

---

## 6. Deliberate Middleware Pipeline Order (`app/main.py`)

```
   Incoming Request
          │
          ▼
   1. SecurityHeadersMiddleware       (Guarantees security headers on ALL responses)
          │
          ▼
   2. ProfilingMiddleware             (Monitors total request lifecycle duration)
          │
          ▼
   3. RequestSizeLimitMiddleware      (Rejects payloads > 50MB with 413 before memory allocation)
          │
          ▼
   4. RateLimitMiddleware             (Throttles DoS/brute-force attacks with 429)
          │
          ▼
   5. TrustedHostMiddleware           (Protects against Host header injection)
          │
          ▼
   6. CORSMiddleware                  (Enforces origin policy)
          │
          ▼
   7. RequestIDMiddleware             (Injects X-Request-ID and contextual logging vars)
          │
          ▼
   FastAPI Route Handlers
```
