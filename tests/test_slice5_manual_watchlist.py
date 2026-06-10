"""Slice 5 tests: Manual watchlist API and audit fields."""

from __future__ import annotations

import pytest

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
    def test_manual_add(self, app_client):
        resp = app_client.post_json("/watchlist", MANUAL_BODY)
        assert resp.status_int == 201
        data = resp.json
        assert data["status"] == "active"
        assert data["source"] == "operator"
        assert data["symbol_id"] == 1
        assert data["canonical_ticker"] == "AAPL"

    def test_manual_add_duplicate_is_idempotent(self, app_client):
        app_client.post_json("/watchlist", MANUAL_BODY)
        resp = app_client.post_json("/watchlist", MANUAL_BODY)
        assert resp.status_int == 201
        # Only one entry in watchlist
        wl = app_client.get("/watchlist")
        assert wl.json["total"] == 1

    def test_manual_add_missing_reason(self, app_client):
        body = {**MANUAL_BODY}
        del body["reason"]
        resp = app_client.post_json("/watchlist", body, expect_errors=True)
        assert resp.status_int == 422

    def test_manual_add_unresolved_ticker(self, app_client):
        body = {**MANUAL_BODY, "ticker": "ZZZZ"}
        resp = app_client.post_json("/watchlist", body)
        assert resp.status_int == 201
        data = resp.json
        assert data["symbol_id"] is None

    def test_deactivate_entry(self, app_client):
        post = app_client.post_json("/watchlist", MANUAL_BODY)
        weid = post.json["watchlist_entry_id"]
        resp = app_client.patch_json(f"/watchlist/{weid}", {"status": "inactive"})
        assert resp.status_int == 200
        assert resp.json["status"] == "inactive"

    def test_deactivate_preserves_history(self, app_client):
        post = app_client.post_json("/watchlist", MANUAL_BODY)
        weid = post.json["watchlist_entry_id"]
        app_client.patch_json(f"/watchlist/{weid}", {"status": "inactive"})
        # Entry still exists, just inactive
        resp = app_client.get(f"/watchlist/{weid}")
        assert resp.status_int == 200
        assert resp.json["status"] == "inactive"

    def test_patch_invalid_id(self, app_client):
        resp = app_client.patch_json("/watchlist/watchlist:no:exist:ZZZZ", {"status": "inactive"}, expect_errors=True)
        assert resp.status_int == 404

    def test_patch_tags_and_metadata(self, app_client):
        post = app_client.post_json("/watchlist", MANUAL_BODY)
        weid = post.json["watchlist_entry_id"]
        resp = app_client.patch_json(f"/watchlist/{weid}", {
            "tags": ["updated"],
            "metadata": {"note": "Updated"},
        })
        assert resp.status_int == 200
        assert resp.json["tags"] == ["updated"]
