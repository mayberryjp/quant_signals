"""Thin async Redis client wrapper with health helpers."""

from __future__ import annotations

import redis.asyncio as aioredis

from app.config import settings

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()  # type: ignore[union-attr]
        _pool = None


async def ping_redis() -> bool:
    try:
        r = await get_redis()
        return await r.ping()
    except Exception:
        return False
