"""Response schemas for the signal cache and watchlist API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SignalAcceptedResponse(BaseModel):
    status: str
    signal_cache_id: str
    watchlist_status: str | None = None
    watchlist_entry_id: str | None = None


class SignalDetailResponse(BaseModel):
    signal_cache_id: str
    source: str
    idempotency_key: str
    submitted_ticker: str
    canonical_ticker: str | None = None
    symbol_id: int | None = None
    market: str
    locale: str
    signal_type: str
    direction: str | None = None
    score: float | None = None
    confidence: float | None = None
    horizon: str | None = None
    reason: str
    tags: list[str]
    metadata: dict[str, Any]
    status: str
    rejection_reason: str | None = None
    received_at: datetime
    processed_at: datetime | None = None
    watchlist_entry_id: str | None = None


class WatchlistEntryResponse(BaseModel):
    watchlist_entry_id: str
    source: str
    signal_type: str
    submitted_ticker: str
    canonical_ticker: str | None = None
    symbol_id: int | None = None
    market: str
    locale: str
    status: str
    direction: str | None = None
    score: float | None = None
    confidence: float | None = None
    horizon: str | None = None
    reason: str
    tags: list[str]
    metadata: dict[str, Any]
    latest_signal_cache_id: str | None = None
    first_seen_signal_cache_id: str | None = None
    last_seen_signal_cache_id: str | None = None
    seen_count: int = 0
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None


class WatchlistListResponse(BaseModel):
    items: list[WatchlistEntryResponse]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    redis: str
    maintenance_heartbeat: str | None = None


class CacheStatsResponse(BaseModel):
    accepted: int = 0
    duplicate: int = 0
    rejected: int = 0
    unresolved: int = 0
    failed: int = 0
    expired: int = 0
    watchlist_upserts: int = 0
    active_watchlist: int = 0
    last_maintenance: str | None = None
