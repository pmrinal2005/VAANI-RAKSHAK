# ==============================================================================
# VAANI-RAKSHAK — In-Memory Token Bucket HTTP Rate Limiter
# Protects REST endpoints from abuse and DoS with sliding token bucket per client IP.
# ==============================================================================

from __future__ import annotations

import asyncio
import math
import time

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class TokenBucket:
    """Sliding window token bucket state for a single client key."""

    def __init__(self, capacity: float, refill_rate_per_sec: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self.tokens = capacity
        self.last_update = time.monotonic()

    def consume(self, amount: float = 1.0) -> tuple[bool, float]:
        """
        Attempt to consume tokens.
        Returns (allowed: bool, retry_after_sec: float).
        """
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now

        # Replenish tokens based on elapsed wall time
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))

        if self.tokens >= amount:
            self.tokens -= amount
            return True, 0.0

        # Calculate time needed to replenish required tokens
        needed = amount - self.tokens
        retry_after = needed / self.refill_rate if self.refill_rate > 0 else 1.0
        return False, max(0.1, retry_after)


class TokenBucketRateLimiter:
    """
    Process-local in-memory token bucket rate limiter.
    Maintains independent bucket state per client IP or API key.
    """

    def __init__(
        self,
        requests_per_minute: int = 120,
        burst_capacity: int = 30,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.burst_capacity = burst_capacity
        self.refill_rate = requests_per_minute / 60.0
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = time.monotonic()

    async def check(self, key: str) -> tuple[bool, float]:
        """
        Check rate limit for a client key.
        Returns (allowed, retry_after_seconds).
        """
        async with self._lock:
            now = time.monotonic()
            if now - self._last_cleanup > 120.0:
                self._cleanup_stale(now)

            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = TokenBucket(
                    capacity=float(self.burst_capacity),
                    refill_rate_per_sec=self.refill_rate,
                )
                self._buckets[key] = bucket

            return bucket.consume(1.0)

    def _cleanup_stale(self, now: float, max_idle_sec: float = 300.0) -> None:
        """Evict buckets inactive for more than max_idle_sec to prevent memory leaks."""
        stale_keys = [
            k for k, b in self._buckets.items() if now - b.last_update > max_idle_sec
        ]
        for k in stale_keys:
            del self._buckets[k]
        self._last_cleanup = now
        if stale_keys:
            logger.debug("rate_limiter.stale_buckets_evicted", count=len(stale_keys))

    def reset(self) -> None:
        """Clear all bucket state (useful between tests)."""
        self._buckets.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware applying token bucket rate limiting to incoming HTTP requests.
    Excludes health endpoints from rate limiting.
    """

    EXCLUDED_PATH_PREFIXES = (
        "/health",
        "/api/v1/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    )

    def __init__(
        self,
        app: ASGIApp,
        limiter: TokenBucketRateLimiter | None = None,
        settings: Settings | None = None,
    ) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()
        self.limiter = limiter or TokenBucketRateLimiter(
            requests_per_minute=self.settings.rate_limit_requests_per_minute,
            burst_capacity=self.settings.rate_limit_burst_capacity,
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Bypass rate limiting for internal health checks and docs
        if any(path.startswith(prefix) for prefix in self.EXCLUDED_PATH_PREFIXES):
            return await call_next(request)

        # Extract client identifier (X-Forwarded-For or direct host)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "unknown-client"

        allowed, retry_after = await self.limiter.check(client_ip)

        if not allowed:
            retry_after_int = max(1, math.ceil(retry_after))
            logger.warning(
                "rate_limit.rejected",
                client=client_ip,
                path=path,
                retry_after=retry_after_int,
            )
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests. Please retry in {retry_after_int} seconds.",
                        "retryAfter": retry_after_int,
                    }
                },
            )
            response.headers["Retry-After"] = str(retry_after_int)
            return response

        return await call_next(request)
