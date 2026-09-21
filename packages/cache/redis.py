"""Redis-backed cache with TTL support."""
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis
from packages.domain.config import get_settings


class RedisCache:
    def __init__(self, redis_url: str | None = None):
        settings = get_settings()
        self._redis_url = redis_url or settings.redis_url
        self._client: redis.Redis | None = None
        self._prefix = "agentbench:"

    async def connect(self) -> None:
        self._client = redis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> Any | None:
        if not self._client:
            return None
        value = await self._client.get(f"{self._prefix}{key}")
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if not self._client:
            return
        settings = get_settings()
        ttl = ttl or settings.cache_default_ttl
        await self._client.setex(
            f"{self._prefix}{key}",
            ttl,
            json.dumps(value, default=str),
        )

    async def delete(self, key: str) -> None:
        if not self._client:
            return
        await self._client.delete(f"{self._prefix}{key}")

    async def invalidate_pattern(self, pattern: str) -> None:
        """Delete all keys matching a pattern."""
        if not self._client:
            return
        cursor = 0
        while True:
            cursor, keys = await self._client.scan(
                cursor, match=f"{self._prefix}{pattern}", count=100
            )
            if keys:
                await self._client.delete(*keys)
            if cursor == 0:
                break
