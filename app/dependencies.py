"""FastAPI dependency injection helpers."""

from __future__ import annotations

from app.redis.client import get_redis
from app.redis.repository import SignalCacheRepository


async def get_repo() -> SignalCacheRepository:
    r = await get_redis()
    return SignalCacheRepository(r)
