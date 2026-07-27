"""Slice 7 tests: Health, readiness, and operational visibility."""

from __future__ import annotations

import pytest


class TestHealth:
    def test_health_ok(self, app_client):
        resp = app_client.get("/signal-cache/health")
        assert resp.status_int == 200
        assert resp.json["status"] == "ok"

    def test_readiness_ok(self, app_client):
        resp = app_client.get("/signal-cache/ready")
        assert resp.status_int == 200
        data = resp.json
        assert data["status"] == "ready"
        assert data["redis"] == "ok"

    def test_cache_stats(self, app_client):
        resp = app_client.get("/signal-cache/stats")
        assert resp.status_int == 200
        data = resp.json
        assert "accepted" in data
        assert "watchlist_upserts" in data
        assert "active_watchlist" in data

    def test_cache_stats_counts_watchlist_upserts(self, app_client):
        body = {
            "source": "stats-test",
            "idempotency_key": "stats-test:AAPL:1",
            "ticker": "AAPL",
            "reason": "stats test",
        }
        app_client.post_json("/signals", body)
        body["idempotency_key"] = "stats-test:AAPL:2"
        app_client.post_json("/signals", body)

        resp = app_client.get("/signal-cache/stats")
        assert resp.status_int == 200
        assert resp.json["watchlist_upserts"] == 2
