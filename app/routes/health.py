"""Health, readiness, and operational visibility routes (Slice 7)."""

from __future__ import annotations

from bottle import Bottle

from app.dependencies import get_repo

sub = Bottle()


@sub.get('/signal-cache/health')
def health():
    return {"status": "ok"}


@sub.get('/signal-cache/ready')
def readiness():
    repo = get_repo()
    try:
        redis_ok = repo.r.ping()
    except Exception:
        redis_ok = False
    heartbeat = repo.get_heartbeat() if redis_ok else None
    return {
        "status": "ready" if redis_ok else "not_ready",
        "redis": "ok" if redis_ok else "unavailable",
        "maintenance_heartbeat": heartbeat,
    }


@sub.get('/signal-cache/stats')
def cache_stats():
    repo = get_repo()
    counters = repo.get_counters()
    active = repo.get_active_watchlist_count()
    last_maint = repo.get_last_cleanup()
    return {**counters, "active_watchlist": active, "last_maintenance": last_maint}
