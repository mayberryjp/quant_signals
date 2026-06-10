"""Slice 7 tests: Health, readiness, and operational visibility."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_ok(self, app_client: AsyncClient):
        resp = await app_client.get("/signal-cache/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_readiness_ok(self, app_client: AsyncClient):
        resp = await app_client.get("/signal-cache/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_cache_stats(self, app_client: AsyncClient):
        resp = await app_client.get("/signal-cache/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "accepted" in data
        assert "active_watchlist" in data
