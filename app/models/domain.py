"""Domain models for the signal cache and watchlist service.

All models use Pydantic v2.  Fields intentionally mirror the Redis value
schemas documented in docs/redis_contracts.md so that serialization is a
straight ``model.model_dump(mode="json")`` call.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SignalStatus(str, enum.Enum):
    accepted = "accepted"
    duplicate = "duplicate"
    rejected = "rejected"
    unresolved = "unresolved"
    failed = "failed"
    expired = "expired"
    superseded = "superseded"


class WatchlistStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    expired = "expired"


class SignalDirection(str, enum.Enum):
    long = "long"
    short = "short"
    neutral = "neutral"


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------

class SignalSource(BaseModel):
    """A registered signal producer."""
    name: str
    source_type: str = "strategy"
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: int = 1


# ---------------------------------------------------------------------------
# Signal cache record
# ---------------------------------------------------------------------------

class SignalCacheRecord(BaseModel):
    """Immutable-ish record of a signal submission stored in Redis."""
    signal_cache_id: str
    source: str
    idempotency_key: str
    submitted_ticker: str
    market: str = "stocks"
    locale: str = "us"
    signal_type: str = "watchlist_candidate"
    direction: SignalDirection | None = None
    score: float | None = None
    confidence: float | None = None
    horizon: str | None = None
    reason: str = ""
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Resolution / enrichment
    symbol_id: int | None = None
    canonical_ticker: str | None = None
    status: SignalStatus = SignalStatus.accepted
    rejection_reason: str | None = None

    # Timestamps
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: datetime | None = None

    # Linked watchlist entry
    watchlist_entry_id: str | None = None

    schema_version: int = 1


# ---------------------------------------------------------------------------
# Idempotency record
# ---------------------------------------------------------------------------

class IdempotencyRecord(BaseModel):
    """Short-lived dedup guard keyed by source + idempotency_key."""
    idempotency_key: str
    source: str
    signal_cache_id: str
    status: SignalStatus
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: int = 1


# ---------------------------------------------------------------------------
# Watchlist entry
# ---------------------------------------------------------------------------

class WatchlistEntry(BaseModel):
    """API-visible watchlist state for one source+signal_type+ticker combo."""
    watchlist_entry_id: str
    source: str
    signal_type: str = "watchlist_candidate"
    submitted_ticker: str
    canonical_ticker: str | None = None
    symbol_id: int | None = None
    market: str = "stocks"
    locale: str = "us"

    status: WatchlistStatus = WatchlistStatus.active
    direction: SignalDirection | None = None
    score: float | None = None
    confidence: float | None = None
    horizon: str | None = None
    reason: str = ""
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Lineage
    latest_signal_cache_id: str | None = None
    first_seen_signal_cache_id: str | None = None
    last_seen_signal_cache_id: str | None = None
    seen_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str | None = None

    schema_version: int = 1
