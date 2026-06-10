"""Shared fixtures for the quant_signals test suite."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.models.domain import SignalCacheRecord, SignalStatus, WatchlistEntry, WatchlistStatus
from app.redis import keys
from app.redis.repository import SignalCacheRepository


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def fake_redis():
    """Provide a fresh fakeredis instance per test."""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


@pytest_asyncio.fixture
async def repo(fake_redis) -> SignalCacheRepository:
    return SignalCacheRepository(fake_redis)


@pytest_asyncio.fixture
async def app_client(fake_redis) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with Redis dependency overridden."""
    from app.main import app
    from app.dependencies import get_repo

    async def _override_repo():
        return SignalCacheRepository(fake_redis)

    app.dependency_overrides[get_repo] = _override_repo
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


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
