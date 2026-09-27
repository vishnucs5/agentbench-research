from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""

    pass


class CircuitBreaker:
    """Production-grade circuit breaker with exponential backoff and fallback support."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        backoff_factor: float = 1.5,
        max_retries: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.backoff_factor = backoff_factor
        self.max_retries = max_retries

        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.last_failure_time: float = 0.0
        self.last_state_change: float = time.time()

    def _update_state(self) -> None:
        """Check and transition between OPEN and HALF_OPEN based on recovery timeout."""
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self.last_state_change
            if elapsed >= self.recovery_timeout:
                logger.info(
                    "Circuit breaker '%s' recovery timeout (%.1fs) elapsed. Transitioning OPEN -> HALF_OPEN.",
                    self.name,
                    self.recovery_timeout,
                )
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = time.time()

    def record_success(self) -> None:
        """Record successful invocation and reset failure counters."""
        if self.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
            logger.info("Circuit breaker '%s' recovered. Transitioning to CLOSED.", self.name)
            self.state = CircuitState.CLOSED
            self.last_state_change = time.time()
        self.failure_count = 0

    def record_failure(self, error: Exception) -> None:
        """Record an operation failure and trip to OPEN if threshold exceeded."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(
            "Circuit breaker '%s' recorded failure (%d/%d): %s",
            self.name,
            self.failure_count,
            self.failure_threshold,
            error,
        )
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.error(
                "Circuit breaker '%s' threshold reached (%d failures). Transitioning to OPEN.",
                self.name,
                self.failure_count,
            )

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute an async function protected by the circuit breaker."""
        self._update_state()

        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. Requests blocked until recovery timeout."
            )

        attempt = 0
        delay = 0.5
        while attempt <= self.max_retries:
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                attempt += 1
                if attempt > self.max_retries:
                    self.record_failure(e)
                    raise
                logger.debug(
                    "Circuit breaker '%s' retrying attempt %d/%d after error: %s",
                    self.name,
                    attempt,
                    self.max_retries,
                    e,
                )
                await asyncio.sleep(delay)
                delay *= self.backoff_factor

        raise RuntimeError(f"Circuit breaker '{self.name}' unexpected execution flow.")

    async def call_with_fallback(
        self,
        func: Callable[..., Awaitable[T]],
        fallback_func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute func under circuit breaker; call fallback_func if open or on error."""
        try:
            return await self.call(func, *args, **kwargs)
        except Exception as e:
            logger.warning(
                "Circuit breaker '%s' triggered fallback due to: %s",
                self.name,
                e,
            )
            return await fallback_func(*args, **kwargs)
