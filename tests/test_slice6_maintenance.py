"""Slice 6 tests: Cache maintenance worker."""

from __future__ import annotations

import time

import pytest

from app.redis import keys
from app.redis.repository import SignalCacheRepository
from tests.conftest import make_signal_record


class TestMaintenance:
    @pytest.mark.asyncio
    async def test_heartbeat(self, repo: SignalCacheRepository):
        await repo.set_heartbeat()
        hb = await repo.get_heartbeat()
        assert hb is not None

    @pytest.mark.asyncio
    async def test_heartbeat_ttl(self, repo: SignalCacheRepository, fake_redis):
        await repo.set_heartbeat()
        ttl = await fake_redis.ttl(keys.MAINTENANCE_HEARTBEAT)
        assert ttl > 0

    @pytest.mark.asyncio
    async def test_last_cleanup(self, repo: SignalCacheRepository):
        await repo.set_heartbeat()
        lc = await repo.get_last_cleanup()
        assert lc is not None

    @pytest.mark.asyncio
    async def test_prune_recent_signals_no_op(self, repo: SignalCacheRepository):
        # Nothing to prune
        removed = await repo.prune_recent_signals()
        assert removed == 0

    @pytest.mark.asyncio
    async def test_prune_recent_signals_removes_old(self, repo: SignalCacheRepository, fake_redis):
        rec = make_signal_record()
        await repo.store_signal(rec)
        # Force the score to be old
        await fake_redis.zadd(keys.RECENT_SIGNALS_INDEX, {rec.signal_cache_id: 0})
        removed = await repo.prune_recent_signals(max_age_seconds=1)
        assert removed == 1

    @pytest.mark.asyncio
    async def test_prune_idempotent(self, repo: SignalCacheRepository, fake_redis):
        rec = make_signal_record()
        await repo.store_signal(rec)
        await fake_redis.zadd(keys.RECENT_SIGNALS_INDEX, {rec.signal_cache_id: 0})
        await repo.prune_recent_signals(max_age_seconds=1)
        removed2 = await repo.prune_recent_signals(max_age_seconds=1)
        assert removed2 == 0
