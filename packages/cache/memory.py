"""In-memory cache fallback when Redis is unavailable."""
from __future__ import annotations

import fnmatch
import time
from typing import Any


class MemoryCache:
    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}

    async def get(self, key: str) -> Any | None:
        if key in self._store:
            value, expires_at = self._store[key]
            if expires_at > time.time():
                return value
            del self._store[key]
        return None

    async def set(self, key: str, value: Any, ttl: int = 30) -> None:
        self._store[key] = (value, time.time() + ttl)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def invalidate_pattern(self, pattern: str) -> None:
        keys_to_delete = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
        for key in keys_to_delete:
            del self._store[key]
