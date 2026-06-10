"""Health, readiness, and operational visibility routes (Slice 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_repo
from app.models.responses import CacheStatsResponse, HealthResponse, ReadinessResponse
from app.redis.repository import SignalCacheRepository

router = APIRouter(tags=["health"])


@router.get("/signal-cache/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


@router.get("/signal-cache/ready", response_model=ReadinessResponse)
async def readiness(repo: SignalCacheRepository = Depends(get_repo)):
    try:
        redis_ok = await repo.r.ping()
    except Exception:
        redis_ok = False
    heartbeat = await repo.get_heartbeat() if redis_ok else None
    return ReadinessResponse(
        status="ready" if redis_ok else "not_ready",
        redis="ok" if redis_ok else "unavailable",
        maintenance_heartbeat=heartbeat,
    )


@router.get("/signal-cache/stats", response_model=CacheStatsResponse)
async def cache_stats(repo: SignalCacheRepository = Depends(get_repo)):
    counters = await repo.get_counters()
    active = await repo.get_active_watchlist_count()
    last_maint = await repo.get_last_cleanup()
    return CacheStatsResponse(
        **counters,
        active_watchlist=active,
        last_maintenance=last_maint,
    )
