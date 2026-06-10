"""Slice 5 tests: Manual watchlist API and audit fields."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.symbol_resolver import ResolvedSymbol, SymbolResolver, _StubBackend

MANUAL_BODY = {
    "ticker": "AAPL",
    "market": "stocks",
    "locale": "us",
    "source": "operator",
    "reason": "Manual review candidate from external scan",
    "tags": ["manual", "review"],
    "metadata": {"note": "Added during morning review"},
}


@pytest.fixture(autouse=True)
def seed_symbols():
    backend = _StubBackend()
    backend.seed("AAPL", ResolvedSymbol(symbol_id=1, canonical_ticker="AAPL"))
    SymbolResolver.set_backend(backend)
    yield
    SymbolResolver.set_backend(_StubBackend())


class TestManualWatchlist:
    @pytest.mark.asyncio
    async def test_manual_add(self, app_client: AsyncClient):
        resp = await app_client.post("/watchlist", json=MANUAL_BODY)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "active"
        assert data["source"] == "operator"
        assert data["symbol_id"] == 1
        assert data["canonical_ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_manual_add_duplicate_is_idempotent(self, app_client: AsyncClient):
        await app_client.post("/watchlist", json=MANUAL_BODY)
        resp = await app_client.post("/watchlist", json=MANUAL_BODY)
        assert resp.status_code == 201
        # Only one entry in watchlist
        wl = await app_client.get("/watchlist")
        assert wl.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_manual_add_missing_reason(self, app_client: AsyncClient):
        body = {**MANUAL_BODY}
        del body["reason"]
        resp = await app_client.post("/watchlist", json=body)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_manual_add_unresolved_ticker(self, app_client: AsyncClient):
        body = {**MANUAL_BODY, "ticker": "ZZZZ"}
        resp = await app_client.post("/watchlist", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["symbol_id"] is None

    @pytest.mark.asyncio
    async def test_deactivate_entry(self, app_client: AsyncClient):
        post = await app_client.post("/watchlist", json=MANUAL_BODY)
        weid = post.json()["watchlist_entry_id"]
        resp = await app_client.patch(f"/watchlist/{weid}", json={"status": "inactive"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "inactive"

    @pytest.mark.asyncio
    async def test_deactivate_preserves_history(self, app_client: AsyncClient):
        post = await app_client.post("/watchlist", json=MANUAL_BODY)
        weid = post.json()["watchlist_entry_id"]
        await app_client.patch(f"/watchlist/{weid}", json={"status": "inactive"})
        # Entry still exists, just inactive
        resp = await app_client.get(f"/watchlist/{weid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "inactive"

    @pytest.mark.asyncio
    async def test_patch_invalid_id(self, app_client: AsyncClient):
        resp = await app_client.patch("/watchlist/watchlist:no:exist:ZZZZ", json={"status": "inactive"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_patch_tags_and_metadata(self, app_client: AsyncClient):
        post = await app_client.post("/watchlist", json=MANUAL_BODY)
        weid = post.json()["watchlist_entry_id"]
        resp = await app_client.patch(f"/watchlist/{weid}", json={
            "tags": ["updated"],
            "metadata": {"note": "Updated"},
        })
        assert resp.status_code == 200
        assert resp.json()["tags"] == ["updated"]
