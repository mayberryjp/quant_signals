"""Slice 8 tests: Validation boundaries and hardening."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.symbol_resolver import ResolvedSymbol, SymbolResolver, _StubBackend

VALID_SIGNAL = {
    "source": "test-src",
    "idempotency_key": "k1",
    "ticker": "AAPL",
    "reason": "test",
}


@pytest.fixture(autouse=True)
def seed_symbols():
    backend = _StubBackend()
    backend.seed("AAPL", ResolvedSymbol(symbol_id=1, canonical_ticker="AAPL"))
    SymbolResolver.set_backend(backend)
    yield
    SymbolResolver.set_backend(_StubBackend())


class TestValidationBoundaries:
    @pytest.mark.asyncio
    async def test_too_many_tags(self, app_client: AsyncClient):
        body = {**VALID_SIGNAL, "tags": [f"t{i}" for i in range(25)]}
        resp = await app_client.post("/signals", json=body)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_score_negative(self, app_client: AsyncClient):
        body = {**VALID_SIGNAL, "score": -0.1, "idempotency_key": "neg"}
        resp = await app_client.post("/signals", json=body)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_score_above_one(self, app_client: AsyncClient):
        body = {**VALID_SIGNAL, "score": 1.01, "idempotency_key": "high"}
        resp = await app_client.post("/signals", json=body)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_confidence_negative(self, app_client: AsyncClient):
        body = {**VALID_SIGNAL, "confidence": -0.5, "idempotency_key": "cneg"}
        resp = await app_client.post("/signals", json=body)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_direction(self, app_client: AsyncClient):
        body = {**VALID_SIGNAL, "direction": "sideways", "idempotency_key": "dir"}
        resp = await app_client.post("/signals", json=body)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_source(self, app_client: AsyncClient):
        body = {**VALID_SIGNAL, "source": "", "idempotency_key": "esrc"}
        resp = await app_client.post("/signals", json=body)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_idempotency_key(self, app_client: AsyncClient):
        body = {**VALID_SIGNAL, "idempotency_key": ""}
        resp = await app_client.post("/signals", json=body)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_reason_too_long(self, app_client: AsyncClient):
        body = {**VALID_SIGNAL, "reason": "x" * 3000, "idempotency_key": "longr"}
        resp = await app_client.post("/signals", json=body)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_manual_watchlist_empty_reason(self, app_client: AsyncClient):
        body = {"ticker": "AAPL", "reason": ""}
        resp = await app_client.post("/watchlist", json=body)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_patch_invalid_status(self, app_client: AsyncClient):
        post = await app_client.post("/watchlist", json={
            "ticker": "AAPL", "reason": "test", "source": "operator"
        })
        weid = post.json()["watchlist_entry_id"]
        resp = await app_client.patch(f"/watchlist/{weid}", json={"status": "bogus"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_two_sources_produce_separately(self, app_client: AsyncClient):
        """Two different sources can submit signals for the same ticker."""
        body1 = {**VALID_SIGNAL, "source": "src-a", "idempotency_key": "a:AAPL"}
        body2 = {**VALID_SIGNAL, "source": "src-b", "idempotency_key": "b:AAPL"}
        r1 = await app_client.post("/signals", json=body1)
        r2 = await app_client.post("/signals", json=body2)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["watchlist_entry_id"] != r2.json()["watchlist_entry_id"]
