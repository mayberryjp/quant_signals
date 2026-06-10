"""Shared fixtures for the quant_signals test suite."""

from __future__ import annotations

import fakeredis
import pytest
from webtest import TestApp

from app.models.domain import SignalCacheRecord, SignalStatus, WatchlistEntry, WatchlistStatus
from app.redis import client as redis_client
from app.redis.repository import SignalCacheRepository


@pytest.fixture
def fake_redis():
    """Provide a fresh fakeredis instance per test."""
    r = fakeredis.FakeRedis(decode_responses=True)
    yield r
    r.close()


@pytest.fixture
def repo(fake_redis) -> SignalCacheRepository:
    return SignalCacheRepository(fake_redis)


@pytest.fixture
def app_client(fake_redis) -> TestApp:
    """HTTP test client with Redis dependency overridden."""
    original = redis_client._pool
    redis_client._pool = fake_redis
    from app.main import app
    test_app = TestApp(app)
    yield test_app
    redis_client._pool = original


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_signal_record(**overrides) -> SignalCacheRecord:
    defaults = dict(
        signal_cache_id="signal:test-source:test-key-1",
        source="test-source",
        idempotency_key="test-key-1",
        submitted_ticker="AAPL",
        market="stocks",
        locale="us",
        signal_type="watchlist_candidate",
        score=0.85,
        confidence=0.70,
        reason="Test reason",
        tags=["test"],
        status=SignalStatus.accepted,
    )
    defaults.update(overrides)
    return SignalCacheRecord(**defaults)


def make_watchlist_entry(**overrides) -> WatchlistEntry:
    defaults = dict(
        watchlist_entry_id="watchlist:test-source:watchlist_candidate:AAPL",
        source="test-source",
        signal_type="watchlist_candidate",
        submitted_ticker="AAPL",
        market="stocks",
        locale="us",
        status=WatchlistStatus.active,
        reason="Test reason",
        tags=["test"],
    )
    defaults.update(overrides)
    return WatchlistEntry(**defaults)
