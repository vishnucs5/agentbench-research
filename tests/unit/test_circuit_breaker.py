from __future__ import annotations

import asyncio

import pytest
from packages.agent.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState


@pytest.mark.asyncio
async def test_circuit_breaker_normal_execution():
    cb = CircuitBreaker("test-cb", failure_threshold=2, recovery_timeout=0.1)

    async def add(a: int, b: int) -> int:
        return a + b

    result = await cb.call(add, 2, 3)
    assert result == 5
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_trips_to_open_on_failures():
    cb = CircuitBreaker("test-cb-fail", failure_threshold=2, recovery_timeout=0.2, max_retries=0)

    async def fail():
        raise ConnectionError("External service down")

    with pytest.raises(ConnectionError):
        await cb.call(fail)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1

    with pytest.raises(ConnectionError):
        await cb.call(fail)
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 2

    # Subsequent call fails immediately with CircuitBreakerOpenError without calling function
    called = False

    async def should_not_run():
        nonlocal called
        called = True
        return "ok"

    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(should_not_run)
    assert not called


@pytest.mark.asyncio
async def test_circuit_breaker_recovery_half_open_to_closed():
    cb = CircuitBreaker("test-cb-rec", failure_threshold=1, recovery_timeout=0.1, max_retries=0)

    async def fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await cb.call(fail)
    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(0.15)

    async def success():
        return "recovered"

    result = await cb.call(success)
    assert result == "recovered"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_fallback():
    cb = CircuitBreaker("test-cb-fb", failure_threshold=1, recovery_timeout=1.0, max_retries=0)

    async def primary():
        raise ConnectionError("primary service down")

    async def fallback():
        return "mock-response"

    res = await cb.call_with_fallback(primary, fallback)
    assert res == "mock-response"
    assert cb.state == CircuitState.OPEN

    # Next call also directly uses fallback
    res2 = await cb.call_with_fallback(primary, fallback)
    assert res2 == "mock-response"
