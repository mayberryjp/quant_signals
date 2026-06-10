"""Slice 1 tests: Redis key patterns, domain models, TTL, idempotency, upsert."""

from __future__ import annotations

import pytest

from app.models.domain import (
    IdempotencyRecord,
    SignalCacheRecord,
    SignalSource,
    SignalStatus,
    WatchlistEntry,
    WatchlistStatus,
)
from app.redis import keys
from tests.conftest import make_signal_record, make_watchlist_entry


# ---------------------------------------------------------------------------
# Key pattern tests
# ---------------------------------------------------------------------------

class TestKeyPatterns:
    def test_source_key(self):
        assert keys.source_key("momentum-v1") == "qs:source:momentum-v1"

    def test_idempotency_key(self):
        assert keys.idempotency_key("src", "k1") == "qs:idem:src:k1"

    def test_signal_key(self):
        assert keys.signal_key("src", "k1") == "qs:signal:src:k1"

    def test_watchlist_key_uppercases_ticker(self):
        assert keys.watchlist_key("src", "watchlist_candidate", "aapl") == "qs:watchlist:src:watchlist_candidate:AAPL"

    def test_signal_cache_id(self):
        assert keys.signal_cache_id("src", "k1") == "signal:src:k1"

    def test_watchlist_entry_id(self):
        assert keys.watchlist_entry_id("src", "wc", "aapl") == "watchlist:src:wc:AAPL"

    def test_index_keys(self):
        assert "idx" in keys.RECENT_SIGNALS_INDEX
        assert "idx" in keys.ACTIVE_WATCHLIST_INDEX
        assert "idx" in keys.watchlist_source_index("src")
        assert "AAPL" in keys.watchlist_ticker_index("aapl")

    def test_counter_key(self):
        assert keys.counter_key("accepted") == "qs:counter:accepted"


# ---------------------------------------------------------------------------
# Domain model tests
# ---------------------------------------------------------------------------

class TestDomainModels:
    def test_signal_record_factory(self):
        rec = make_signal_record()
        assert rec.signal_cache_id == "signal:test-source:test-key-1"
        assert rec.status == SignalStatus.accepted
        assert rec.schema_version == 1

    def test_watchlist_entry_factory(self):
        entry = make_watchlist_entry()
        assert entry.status == WatchlistStatus.active
        assert entry.schema_version == 1

    def test_signal_record_json_roundtrip(self):
        rec = make_signal_record()
        j = rec.model_dump_json()
        restored = SignalCacheRecord.model_validate_json(j)
        assert restored.signal_cache_id == rec.signal_cache_id

    def test_watchlist_entry_json_roundtrip(self):
        entry = make_watchlist_entry()
        j = entry.model_dump_json()
        restored = WatchlistEntry.model_validate_json(j)
        assert restored.watchlist_entry_id == entry.watchlist_entry_id


# ---------------------------------------------------------------------------
# Redis repository tests (using fakeredis)
# ---------------------------------------------------------------------------

class TestRedisRepository:
    @pytest.mark.asyncio
    async def test_store_and_get_signal(self, repo):
        rec = make_signal_record()
        await repo.store_signal(rec)
        fetched = await repo.get_signal("test-source", "test-key-1")
        assert fetched is not None
        assert fetched.signal_cache_id == rec.signal_cache_id

    @pytest.mark.asyncio
    async def test_signal_ttl(self, repo, fake_redis):
        rec = make_signal_record()
        await repo.store_signal(rec)
        ttl = await fake_redis.ttl(keys.signal_key("test-source", "test-key-1"))
        assert ttl > 0

    @pytest.mark.asyncio
    async def test_idempotency_set_and_check(self, repo, fake_redis):
        idem = IdempotencyRecord(
            idempotency_key="k1",
            source="src",
            signal_cache_id="signal:src:k1",
            status=SignalStatus.accepted,
        )
        await repo.set_idempotency(idem)
        found = await repo.check_idempotency("src", "k1")
        assert found is not None
        assert found.signal_cache_id == "signal:src:k1"
        # TTL should be set
        ttl = await fake_redis.ttl(keys.idempotency_key("src", "k1"))
        assert ttl > 0

    @pytest.mark.asyncio
    async def test_idempotency_miss(self, repo):
        assert await repo.check_idempotency("no", "no") is None

    @pytest.mark.asyncio
    async def test_watchlist_upsert_creates_entry(self, repo):
        entry = make_watchlist_entry()
        await repo.upsert_watchlist_entry(entry)
        fetched = await repo.get_watchlist_entry("test-source", "watchlist_candidate", "AAPL")
        assert fetched is not None
        assert fetched.status == WatchlistStatus.active

    @pytest.mark.asyncio
    async def test_watchlist_upsert_is_idempotent(self, repo):
        entry = make_watchlist_entry(score=0.5)
        await repo.upsert_watchlist_entry(entry)
        entry.score = 0.9
        await repo.upsert_watchlist_entry(entry)
        fetched = await repo.get_watchlist_entry("test-source", "watchlist_candidate", "AAPL")
        assert fetched is not None
        assert fetched.score == 0.9

    @pytest.mark.asyncio
    async def test_watchlist_uniqueness_by_source_type_ticker(self, repo):
        e1 = make_watchlist_entry(source="a", signal_type="wc",
                                  watchlist_entry_id="watchlist:a:wc:AAPL")
        e2 = make_watchlist_entry(source="b", signal_type="wc",
                                  watchlist_entry_id="watchlist:b:wc:AAPL")
        await repo.upsert_watchlist_entry(e1)
        await repo.upsert_watchlist_entry(e2)
        assert await repo.get_watchlist_entry("a", "wc", "AAPL") is not None
        assert await repo.get_watchlist_entry("b", "wc", "AAPL") is not None

    @pytest.mark.asyncio
    async def test_active_index_updated(self, repo, fake_redis):
        entry = make_watchlist_entry()
        await repo.upsert_watchlist_entry(entry)
        members = await fake_redis.smembers(keys.ACTIVE_WATCHLIST_INDEX)
        assert entry.watchlist_entry_id in members

    @pytest.mark.asyncio
    async def test_get_or_create_source(self, repo):
        s = await repo.get_or_create_source("my-strategy")
        assert s.name == "my-strategy"
        # Second call returns existing
        s2 = await repo.get_or_create_source("my-strategy")
        assert s2.name == "my-strategy"

    @pytest.mark.asyncio
    async def test_counters(self, repo):
        rec = make_signal_record()
        await repo.store_signal(rec)
        counters = await repo.get_counters()
        assert counters["accepted"] == 1

    @pytest.mark.asyncio
    async def test_recent_signals_index(self, repo):
        rec = make_signal_record()
        await repo.store_signal(rec)
        recent = await repo.get_recent_signals(limit=10)
        assert len(recent) == 1
        assert recent[0].signal_cache_id == rec.signal_cache_id
