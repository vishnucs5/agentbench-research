"""Tests for cache layer."""
import time

import pytest
from packages.cache.memory import MemoryCache


@pytest.fixture
def cache():
    return MemoryCache()


@pytest.mark.asyncio
async def test_set_and_get(cache):
    await cache.set("key1", {"data": "value"}, ttl=60)
    result = await cache.get("key1")
    assert result == {"data": "value"}


@pytest.mark.asyncio
async def test_get_missing_key(cache):
    result = await cache.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_delete(cache):
    await cache.set("key1", "value")
    await cache.delete("key1")
    result = await cache.get("key1")
    assert result is None


@pytest.mark.asyncio
async def test_invalidate_pattern(cache):
    await cache.set("users:1", "a")
    await cache.set("users:2", "b")
    await cache.set("projects:1", "c")
    await cache.invalidate_pattern("users:*")
    assert await cache.get("users:1") is None
    assert await cache.get("users:2") is None
    assert await cache.get("projects:1") == "c"


@pytest.mark.asyncio
async def test_ttl_expiration(cache):
    await cache.set("expire_soon", "value", ttl=0)
    time.sleep(0.01)
    result = await cache.get("expire_soon")
    assert result is None


@pytest.mark.asyncio
async def test_set_overwrites(cache):
    await cache.set("key1", "first")
    await cache.set("key1", "second")
    result = await cache.get("key1")
    assert result == "second"


@pytest.mark.asyncio
async def test_delete_nonexistent(cache):
    await cache.delete("nonexistent")
    result = await cache.get("nonexistent")
    assert result is None
