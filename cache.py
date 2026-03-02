"""
In-memory cache с TTL для funding rates.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from fetchers.base import FundingRate


@dataclass
class CachedItem:
    value: Any
    expires_at: float


class Cache:
    """Thread-safe in-memory cache с TTL."""

    def __init__(self, ttl_sec: int = 60):
        self._ttl = ttl_sec
        self._data: dict[str, CachedItem] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> list[FundingRate] | None:
        async with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            if time.monotonic() > item.expires_at:
                del self._data[key]
                return None
            return item.value

    async def set(self, key: str, value: list[FundingRate]) -> None:
        async with self._lock:
            self._data[key] = CachedItem(
                value=value,
                expires_at=time.monotonic() + self._ttl,
            )

    async def invalidate(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)

    async def invalidate_all(self) -> None:
        async with self._lock:
            self._data.clear()


# Глобальный экземпляр
funding_cache: Cache | None = None


def get_cache(ttl: int = 60) -> Cache:
    global funding_cache
    if funding_cache is None:
        funding_cache = Cache(ttl_sec=ttl)
    return funding_cache
