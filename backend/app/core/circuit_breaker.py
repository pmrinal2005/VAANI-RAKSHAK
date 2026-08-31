# ==============================================================================
# VAANI-RAKSHAK — Asynchronous Circuit Breaker Pattern
# Protects downstream ML inference, Kafka, and telephony services from cascading failures.
# ==============================================================================

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any, Generic, TypeVar

import structlog

from app.core.exceptions import VaaniError

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CircuitBreakerState(StrEnum):
    """Lifecycle states of the Circuit Breaker."""

    CLOSED = "CLOSED"      # Normal operation: all requests pass through
    OPEN = "OPEN"          # Tripped: fast-failing requests to protect downstream
    HALF_OPEN = "HALF_OPEN"  # Testing recovery with limited probe trials


class CircuitBreakerOpenError(VaaniError):
    """Raised when an operation is attempted while the circuit breaker is in OPEN state."""

    error_code = "CIRCUIT_BREAKER_OPEN"

    def __init__(self, breaker_name: str, message: str | None = None) -> None:
        super().__init__(
            message=message or f"Circuit breaker '{breaker_name}' is OPEN. Fast-failing request.",
            error_code="CIRCUIT_BREAKER_OPEN",
        )
        self.breaker_name = breaker_name


class CircuitBreaker(Generic[T]):
    """
    Thread-safe asynchronous circuit breaker for external service boundaries.
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout_sec: float = 30.0,
        half_open_max_trials: int = 3,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.half_open_max_trials = half_open_max_trials

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_active_trials = 0
        self._last_state_change = time.monotonic()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitBreakerState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,  # noqa: ANN401
        fallback: Callable[..., Awaitable[T]] | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> T:
        """
        Execute an async function with circuit breaker protection and optional fallback.
        """
        # 1. Evaluate State Before Call
        async with self._lock:
            now = time.monotonic()

            if self._state == CircuitBreakerState.OPEN:
                if now - self._last_state_change >= self.recovery_timeout_sec:
                    self._transition_to(CircuitBreakerState.HALF_OPEN)
                    self._half_open_active_trials = 1
                else:
                    if fallback is not None:
                        return await fallback(*args, **kwargs)
                    raise CircuitBreakerOpenError(self.name)

            elif self._state == CircuitBreakerState.HALF_OPEN:
                if self._half_open_active_trials < self.half_open_max_trials:
                    self._half_open_active_trials += 1
                else:
                    if fallback is not None:
                        return await fallback(*args, **kwargs)
                    raise CircuitBreakerOpenError(
                        self.name,
                        f"Circuit breaker '{self.name}' is HALF_OPEN (probe trials saturated).",
                    )

        # 2. Execute Operation
        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            # 3. Handle Failure
            async with self._lock:
                if self._state == CircuitBreakerState.HALF_OPEN:
                    self._transition_to(CircuitBreakerState.OPEN)
                elif self._state == CircuitBreakerState.CLOSED:
                    self._failure_count += 1
                    if self._failure_count >= self.failure_threshold:
                        self._transition_to(CircuitBreakerState.OPEN)

            if fallback is not None:
                return await fallback(*args, **kwargs)
            raise exc

        # 4. Handle Success
        async with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_trials:
                    self._transition_to(CircuitBreakerState.CLOSED)
            elif self._state == CircuitBreakerState.CLOSED:
                self._failure_count = 0

        return result

    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        """Internal helper to mutate state and reset metrics."""
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.monotonic()

        if new_state == CircuitBreakerState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            self._half_open_active_trials = 0
        elif new_state == CircuitBreakerState.HALF_OPEN:
            self._success_count = 0
            self._half_open_active_trials = 0
        elif new_state == CircuitBreakerState.OPEN:
            self._success_count = 0
            self._half_open_active_trials = 0

        logger.info(
            "circuit_breaker.state_changed",
            breaker=self.name,
            from_state=old_state.value,
            to_state=new_state.value,
        )

    def reset(self) -> None:
        """Manually reset the circuit breaker to normal CLOSED state."""
        self._transition_to(CircuitBreakerState.CLOSED)
