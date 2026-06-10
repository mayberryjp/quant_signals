"""Watchlist service – manual add and update logic."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.domain import WatchlistEntry, WatchlistStatus
from app.models.requests import ManualWatchlistAdd
from app.redis import keys
from app.redis.repository import SignalCacheRepository
from app.services.symbol_resolver import SymbolResolver


def manual_add(
    body: ManualWatchlistAdd,
    repo: SignalCacheRepository,
) -> WatchlistEntry:
    now = datetime.now(timezone.utc)
    signal_type = "manual"

    resolved = SymbolResolver.resolve(body.ticker, body.market, body.locale)
    symbol_id = resolved.symbol_id if resolved else None
    canonical_ticker = resolved.canonical_ticker if resolved else None

    weid = keys.watchlist_entry_id(body.source, signal_type, body.ticker)
    existing = repo.get_watchlist_entry_by_id(weid)

    entry = WatchlistEntry(
        watchlist_entry_id=weid,
        source=body.source,
        signal_type=signal_type,
        submitted_ticker=body.ticker,
        canonical_ticker=canonical_ticker,
        symbol_id=symbol_id,
        market=body.market,
        locale=body.locale,
        status=WatchlistStatus.active,
        reason=body.reason,
        tags=body.tags,
        metadata=body.metadata,
        created_at=existing.created_at if existing else now,
        updated_at=now,
        created_by=body.source,
    )
    repo.upsert_watchlist_entry(entry)
    return entry
