"""Slice 6 tests: Cache maintenance worker."""

from __future__ import annotations

import pytest

from app.redis import keys
from app.redis.repository import SignalCacheRepository
from tests.conftest import make_signal_record


class TestMaintenance:
    def test_heartbeat(self, repo: SignalCacheRepository):
        repo.set_heartbeat()
        hb = repo.get_heartbeat()
        assert hb is not None

    def test_heartbeat_ttl(self, repo: SignalCacheRepository, fake_redis):
        repo.set_heartbeat()
        ttl = fake_redis.ttl(keys.MAINTENANCE_HEARTBEAT)
        assert ttl > 0

    def test_last_cleanup(self, repo: SignalCacheRepository):
        repo.set_heartbeat()
        lc = repo.get_last_cleanup()
        assert lc is not None

    def test_prune_recent_signals_no_op(self, repo: SignalCacheRepository):
        # Nothing to prune
        removed = repo.prune_recent_signals()
        assert removed == 0

    def test_prune_recent_signals_removes_old(self, repo: SignalCacheRepository, fake_redis):
        rec = make_signal_record()
        repo.store_signal(rec)
        # Force the score to be old
        fake_redis.zadd(keys.RECENT_SIGNALS_INDEX, {rec.signal_cache_id: 0})
        removed = repo.prune_recent_signals(max_age_seconds=1)
        assert removed == 1

    def test_prune_idempotent(self, repo: SignalCacheRepository, fake_redis):
        rec = make_signal_record()
        repo.store_signal(rec)
        fake_redis.zadd(keys.RECENT_SIGNALS_INDEX, {rec.signal_cache_id: 0})
        repo.prune_recent_signals(max_age_seconds=1)
        removed2 = repo.prune_recent_signals(max_age_seconds=1)
        assert removed2 == 0
