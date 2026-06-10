"""Slice 2 tests: POST /signals intake API."""

from __future__ import annotations

import pytest

from app.services.symbol_resolver import ResolvedSymbol, SymbolResolver, _StubBackend


@pytest.fixture(autouse=True)
def seed_symbols():
    backend = _StubBackend()
    backend.seed("AAPL", ResolvedSymbol(symbol_id=1, canonical_ticker="AAPL", name="Apple Inc."))
    backend.seed("MSFT", ResolvedSymbol(symbol_id=2, canonical_ticker="MSFT", name="Microsoft Corp."))
    SymbolResolver.set_backend(backend)
    yield
    SymbolResolver.set_backend(_StubBackend())


VALID_SIGNAL = {
    "source": "momentum-v1",
    "idempotency_key": "momentum-v1:2026-06-09:AAPL",
    "ticker": "AAPL",
    "market": "stocks",
    "locale": "us",
    "signal_type": "watchlist_candidate",
    "direction": "long",
    "score": 0.87,
    "confidence": 0.72,
    "horizon": "5d",
    "reason": "Relative strength breakout with above-average volume",
    "tags": ["momentum", "breakout", "volume"],
    "metadata": {"strategy_version": "momentum-v1.0", "lookback_days": 20},
}


class TestSignalIntake:
    def test_valid_submission(self, app_client):
        resp = app_client.post_json("/signals", VALID_SIGNAL)
        assert resp.status_int == 201
        data = resp.json
        assert data["status"] == "accepted"
        assert "signal_cache_id" in data
        assert data["watchlist_status"] == "active"
        assert data["watchlist_entry_id"] is not None

    def test_duplicate_idempotency_key(self, app_client):
        app_client.post_json("/signals", VALID_SIGNAL)
        resp = app_client.post_json("/signals", VALID_SIGNAL)
        assert resp.status_int == 201
        data = resp.json
        assert data["status"] == "duplicate"

    def test_missing_required_fields(self, app_client):
        resp = app_client.post_json("/signals", {"source": "x"}, expect_errors=True)
        assert resp.status_int == 422

    def test_missing_ticker(self, app_client):
        body = {**VALID_SIGNAL, "ticker": ""}
        resp = app_client.post_json("/signals", body, expect_errors=True)
        assert resp.status_int == 422

    def test_unresolved_ticker(self, app_client):
        body = {**VALID_SIGNAL, "ticker": "ZZZZ", "idempotency_key": "k-unknown"}
        resp = app_client.post_json("/signals", body)
        assert resp.status_int == 201
        data = resp.json
        assert data["status"] == "unresolved"

    def test_invalid_score_range(self, app_client):
        body = {**VALID_SIGNAL, "score": 1.5, "idempotency_key": "k-badscore"}
        resp = app_client.post_json("/signals", body, expect_errors=True)
        assert resp.status_int == 422

    def test_invalid_confidence_range(self, app_client):
        body = {**VALID_SIGNAL, "confidence": -0.1, "idempotency_key": "k-badconf"}
        resp = app_client.post_json("/signals", body, expect_errors=True)
        assert resp.status_int == 422

    def test_recent_signals_endpoint(self, app_client):
        app_client.post_json("/signals", VALID_SIGNAL)
        resp = app_client.get("/signals/recent")
        assert resp.status_int == 200
        data = resp.json
        assert len(data) >= 1

    def test_get_signal_by_id(self, app_client):
        post_resp = app_client.post_json("/signals", VALID_SIGNAL)
        scid = post_resp.json["signal_cache_id"]
        resp = app_client.get(f"/signals/{scid}")
        assert resp.status_int == 200
        assert resp.json["submitted_ticker"] == "AAPL"

    def test_get_signal_not_found(self, app_client):
        resp = app_client.get("/signals/signal:no:exist", expect_errors=True)
        assert resp.status_int == 404
