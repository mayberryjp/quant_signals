"""Dependency helpers."""

from __future__ import annotations

from app.redis.client import get_redis
from app.redis.repository import SignalCacheRepository


def get_repo() -> SignalCacheRepository:
    r = get_redis()
    return SignalCacheRepository(r)
