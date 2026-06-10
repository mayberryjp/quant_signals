"""Slice 4 tests: Watchlist read API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.symbol_resolver import ResolvedSymbol, SymbolResolver, _StubBackend

SIGNAL_BODY = {
    "source": "momentum-v1",
    "idempotency_key": "m-v1:AAPL",
    "ticker": "AAPL",
    "reason": "test",
}


@pytest.fixture(autouse=True)
def seed_symbols():
    backend = _StubBackend()
    backend.seed("AAPL", ResolvedSymbol(symbol_id=1, canonical_ticker="AAPL"))
    backend.seed("MSFT", ResolvedSymbol(symbol_id=2, canonical_ticker="MSFT"))
    SymbolResolver.set_backend(backend)
    yield
    SymbolResolver.set_backend(_StubBackend())


class TestWatchlistRead:
    @pytest.mark.asyncio
    async def test_list_empty(self, app_client: AsyncClient):
        resp = await app_client.get("/watchlist")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_after_signal(self, app_client: AsyncClient):
        await app_client.post("/signals", json=SIGNAL_BODY)
        resp = await app_client.get("/watchlist")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["submitted_ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_filter_by_source(self, app_client: AsyncClient):
        await app_client.post("/signals", json=SIGNAL_BODY)
        resp = await app_client.get("/watchlist", params={"source": "momentum-v1"})
        assert len(resp.json()["items"]) == 1
        resp2 = await app_client.get("/watchlist", params={"source": "nonexistent"})
        assert len(resp2.json()["items"]) == 0

    @pytest.mark.asyncio
    async def test_filter_by_ticker(self, app_client: AsyncClient):
        await app_client.post("/signals", json=SIGNAL_BODY)
        resp = await app_client.get("/watchlist", params={"ticker": "AAPL"})
        assert len(resp.json()["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_by_id(self, app_client: AsyncClient):
        post = await app_client.post("/signals", json=SIGNAL_BODY)
        weid = post.json()["watchlist_entry_id"]
        resp = await app_client.get(f"/watchlist/{weid}")
        assert resp.status_code == 200
        assert resp.json()["watchlist_entry_id"] == weid

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, app_client: AsyncClient):
        resp = await app_client.get("/watchlist/watchlist:no:exist:ZZZZ")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_by_ticker_lookup(self, app_client: AsyncClient):
        await app_client.post("/signals", json=SIGNAL_BODY)
        resp = await app_client.get("/watchlist/by-ticker/AAPL")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    @pytest.mark.asyncio
    async def test_by_ticker_empty(self, app_client: AsyncClient):
        resp = await app_client.get("/watchlist/by-ticker/ZZZZ")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_pagination(self, app_client: AsyncClient):
        # Create two entries
        await app_client.post("/signals", json=SIGNAL_BODY)
        await app_client.post("/signals", json={
            **SIGNAL_BODY, "ticker": "MSFT", "idempotency_key": "m-v1:MSFT",
        })
        resp = await app_client.get("/watchlist", params={"page_size": 1})
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 2
