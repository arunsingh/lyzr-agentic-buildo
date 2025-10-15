from __future__ import annotations
import asyncio
import os
from typing import Optional

try:
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover
    aioredis = None  # type: ignore


class AbstractLease:
    async def acquire(self, key: str, ttl_secs: int) -> bool: ...
    async def release(self, key: str) -> None: ...


class NoopLease(AbstractLease):
    async def acquire(self, key: str, ttl_secs: int) -> bool:
        return True

    async def release(self, key: str) -> None:
        return None


class RedisLease(AbstractLease):
    def __init__(self, url: Optional[str] = None):
        if aioredis is None:
            raise RuntimeError("redis async client not available")
        self.url = url or os.getenv("AOB_REDIS_URL", "redis://localhost:6379/0")
        self._client = aioredis.from_url(self.url, decode_responses=True)

    async def acquire(self, key: str, ttl_secs: int) -> bool:
        # SET key value NX EX ttl
        return await self._client.set(f"lease:{key}", "1", nx=True, ex=ttl_secs) is True

    async def release(self, key: str) -> None:
        try:
            await self._client.delete(f"lease:{key}")
        except Exception:
            pass

