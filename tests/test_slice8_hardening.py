"""Slice 8 tests: Validation boundaries and hardening."""

from __future__ import annotations

import pytest

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
    def test_too_many_tags(self, app_client):
        body = {**VALID_SIGNAL, "tags": [f"t{i}" for i in range(25)]}
        resp = app_client.post_json("/signals", body, expect_errors=True)
        assert resp.status_int == 422

    def test_score_negative(self, app_client):
        body = {**VALID_SIGNAL, "score": -0.1, "idempotency_key": "neg"}
        resp = app_client.post_json("/signals", body, expect_errors=True)
        assert resp.status_int == 422

    def test_score_above_one(self, app_client):
        body = {**VALID_SIGNAL, "score": 1.01, "idempotency_key": "high"}
        resp = app_client.post_json("/signals", body, expect_errors=True)
        assert resp.status_int == 422

    def test_confidence_negative(self, app_client):
        body = {**VALID_SIGNAL, "confidence": -0.5, "idempotency_key": "cneg"}
        resp = app_client.post_json("/signals", body, expect_errors=True)
        assert resp.status_int == 422

    def test_invalid_direction(self, app_client):
        body = {**VALID_SIGNAL, "direction": "sideways", "idempotency_key": "dir"}
        resp = app_client.post_json("/signals", body, expect_errors=True)
        assert resp.status_int == 422

    def test_empty_source(self, app_client):
        body = {**VALID_SIGNAL, "source": "", "idempotency_key": "esrc"}
        resp = app_client.post_json("/signals", body, expect_errors=True)
        assert resp.status_int == 422

    def test_empty_idempotency_key(self, app_client):
        body = {**VALID_SIGNAL, "idempotency_key": ""}
        resp = app_client.post_json("/signals", body, expect_errors=True)
        assert resp.status_int == 422

    def test_reason_too_long(self, app_client):
        body = {**VALID_SIGNAL, "reason": "x" * 3000, "idempotency_key": "longr"}
        resp = app_client.post_json("/signals", body, expect_errors=True)
        assert resp.status_int == 422

    def test_manual_watchlist_empty_reason(self, app_client):
        body = {"ticker": "AAPL", "reason": ""}
        resp = app_client.post_json("/watchlist", body, expect_errors=True)
        assert resp.status_int == 422

    def test_patch_invalid_status(self, app_client):
        post = app_client.post_json("/watchlist", {
            "ticker": "AAPL", "reason": "test", "source": "operator"
        })
        weid = post.json["watchlist_entry_id"]
        resp = app_client.patch_json(f"/watchlist/{weid}", {"status": "bogus"}, expect_errors=True)
        assert resp.status_int == 422

    def test_two_sources_produce_separately(self, app_client):
        """Two different sources can submit signals for the same ticker."""
        body1 = {**VALID_SIGNAL, "source": "src-a", "idempotency_key": "a:AAPL"}
        body2 = {**VALID_SIGNAL, "source": "src-b", "idempotency_key": "b:AAPL"}
        r1 = app_client.post_json("/signals", body1)
        r2 = app_client.post_json("/signals", body2)
        assert r1.status_int == 201
        assert r2.status_int == 201
        assert r1.json["watchlist_entry_id"] != r2.json["watchlist_entry_id"]
