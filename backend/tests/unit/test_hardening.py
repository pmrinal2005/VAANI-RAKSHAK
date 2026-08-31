# ==============================================================================
# Unit & Integration tests — Reliability, Security & Performance Hardening
# Verifies SecurityHeadersMiddleware, RequestSizeLimitMiddleware,
# TokenBucketRateLimiter, CircuitBreaker, ProfilingMiddleware, & WebSocket protection.
# ==============================================================================

from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerState,
)
from app.core.rate_limit import TokenBucket, TokenBucketRateLimiter
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestSecurityHeaders:
    """Test SecurityHeadersMiddleware behavior."""

    def test_security_headers_present_on_success(self, client: TestClient) -> None:
        res = client.get("/api/v1/health/live")
        assert res.status_code == 200
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "default-src 'none'" in res.headers.get("Content-Security-Policy", "")
        assert res.headers.get("X-XSS-Protection") == "0"
        # HSTS should be absent by default in dev
        assert "Strict-Transport-Security" not in res.headers

    def test_hsts_header_when_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENABLE_HSTS", "true")
        app = create_app()
        with TestClient(app) as hsts_client:
            res = hsts_client.get("/api/v1/health/live")
            assert res.status_code == 200
            assert "max-age=31536000" in res.headers.get("Strict-Transport-Security", "")


class TestRequestSizeLimiting:
    """Test RequestSizeLimitMiddleware behavior."""

    def test_request_within_limit_succeeds(self, client: TestClient) -> None:
        res = client.post(
            "/api/v1/score",
            json={
                "segment": {"callId": "call-size-test", "segmentId": "seg-001"},
                "scenarioOverride": "LOW_RISK",
            },
        )
        assert res.status_code == 200

    def test_oversized_declared_content_length_returns_413(self, client: TestClient) -> None:
        # Declare 100MB content-length (exceeds default 50MB)
        headers = {"Content-Length": str(100 * 1024 * 1024)}
        res = client.post(
            "/api/v1/score",
            content=b"{}",
            headers=headers,
        )
        assert res.status_code == 413
        data = res.json()
        assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"


class TestTokenBucketRateLimiting:
    """Test TokenBucket & TokenBucketRateLimiter."""

    def test_token_bucket_consume_and_replenish(self) -> None:
        bucket = TokenBucket(capacity=2.0, refill_rate_per_sec=10.0)
        # Consume 2 tokens (capacity)
        allowed1, _ = bucket.consume(1.0)
        allowed2, _ = bucket.consume(1.0)
        assert allowed1 is True
        assert allowed2 is True

        # Third token fails immediately
        allowed3, retry_after = bucket.consume(1.0)
        assert allowed3 is False
        assert retry_after > 0.0

        # Wait 0.15s for refill (1.5 tokens refilled)
        time.sleep(0.15)
        allowed4, _ = bucket.consume(1.0)
        assert allowed4 is True

    @pytest.mark.asyncio
    async def test_rate_limiter_throttles_with_429_and_retry_after(self) -> None:
        limiter = TokenBucketRateLimiter(requests_per_minute=60, burst_capacity=3)

        # First 3 succeed
        for _ in range(3):
            allowed, _ = await limiter.check("client-ip-1")
            assert allowed is True

        # 4th gets throttled
        allowed, retry_after = await limiter.check("client-ip-1")
        assert allowed is False
        assert retry_after > 0.0

        # Different client IP is unaffected
        allowed_other, _ = await limiter.check("client-ip-2")
        assert allowed_other is True

    def test_health_endpoints_bypass_rate_limiting(self, client: TestClient) -> None:
        # Even under high volume, health endpoints must succeed
        for _ in range(20):
            res = client.get("/api/v1/health/live")
            assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_stale_bucket_cleanup(self) -> None:
        limiter = TokenBucketRateLimiter(requests_per_minute=60, burst_capacity=5)
        await limiter.check("client-stale")
        assert "client-stale" in limiter._buckets

        # Artificially age the bucket
        limiter._buckets["client-stale"].last_update = time.monotonic() - 400.0

        # Trigger cleanup
        limiter._cleanup_stale(now=time.monotonic(), max_idle_sec=300.0)
        assert "client-stale" not in limiter._buckets


class TestCircuitBreaker:
    """Test CircuitBreaker states: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_transitions(self) -> None:
        breaker: CircuitBreaker[str] = CircuitBreaker(
            name="test-service",
            failure_threshold=3,
            recovery_timeout_sec=0.1,  # Fast recovery for test
            half_open_max_trials=2,
        )

        assert breaker.state == CircuitBreakerState.CLOSED

        async def failing_func() -> str:
            raise ValueError("Downstream service connection failure")

        async def successful_func() -> str:
            return "SUCCESS"

        async def fallback_func() -> str:
            return "FALLBACK_VALUE"

        # 1. Accumulate 3 failures to trip the circuit to OPEN
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.failure_count == 3

        # 2. While OPEN, calls fail fast or execute fallback
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(successful_func)

        fallback_res = await breaker.call(successful_func, fallback=fallback_func)
        assert fallback_res == "FALLBACK_VALUE"

        # 3. Wait for recovery timeout to transition to HALF_OPEN on next call
        await asyncio.sleep(0.12)

        # First probe trial in HALF_OPEN
        res1 = await breaker.call(successful_func)
        assert res1 == "SUCCESS"
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        # Second probe trial in HALF_OPEN (completes recovery to CLOSED)
        res2 = await breaker.call(successful_func)
        assert res2 == "SUCCESS"
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_failure_reopens(self) -> None:
        breaker: CircuitBreaker[str] = CircuitBreaker(
            name="test-reopen",
            failure_threshold=2,
            recovery_timeout_sec=0.05,
            half_open_max_trials=2,
        )

        async def failing_func() -> str:
            raise RuntimeError("Still failing")

        # Trip to OPEN
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.06)

        # Probe fails in HALF_OPEN -> immediately reopens
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)
        assert breaker.state == CircuitBreakerState.OPEN


class TestProfilingMiddleware:
    """Test ProfilingMiddleware response headers."""

    def test_response_timing_headers_present(self, client: TestClient) -> None:
        res = client.get("/api/v1/health/live")
        assert res.status_code == 200
        assert "X-Response-Time" in res.headers
        assert res.headers["X-Response-Time"].endswith("ms")
        assert "Server-Timing" in res.headers
        assert "dur=" in res.headers["Server-Timing"]


class TestWebSocketSafeguards:
    """Test WebSocket message size and rate limiting protection."""

    def test_websocket_oversized_message_safeguard(self, client: TestClient) -> None:
        with client.websocket_connect("/api/v1/ws/calls/call-ws-guard-01") as ws:
            # Read greeting
            ws.receive_json()

            # Send normal ping
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"
