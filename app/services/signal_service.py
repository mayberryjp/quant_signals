"""Signal intake service – orchestrates POST /signals logic."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from app.models.domain import (
    IdempotencyRecord,
    SignalCacheRecord,
    SignalDirection,
    SignalStatus,
    WatchlistEntry,
    WatchlistStatus,
)
from app.models.requests import SignalSubmission
from app.redis import keys
from app.redis.repository import SignalCacheRepository
from app.services.symbol_resolver import SymbolResolver

log = logging.getLogger("quant_signals.signal_service")


def ingest_signal(
    submission: SignalSubmission,
    repo: SignalCacheRepository,
) -> tuple[SignalCacheRecord, WatchlistEntry | None]:
    """Process a signal submission: validate, dedup, resolve, persist."""
    now = datetime.now(timezone.utc)

    # 1. Idempotency check
    existing = repo.check_idempotency(submission.source, submission.idempotency_key)
    if existing is not None:
        rec = repo.get_signal_by_id(existing.signal_cache_id)
        if rec is not None:
            rec.status = SignalStatus.duplicate
            return rec, None
        # Idempotency record exists but signal is gone – treat as duplicate
        dup = SignalCacheRecord(
            signal_cache_id=existing.signal_cache_id,
            source=submission.source,
            idempotency_key=submission.idempotency_key,
            submitted_ticker=submission.ticker,
            status=SignalStatus.duplicate,
            received_at=now,
        )
        return dup, None

    # 2. Ensure source exists
    repo.get_or_create_source(submission.source)

    # 3. Build signal cache id
    scid = keys.signal_cache_id(submission.source, submission.idempotency_key)

    # 4. Resolve symbol
    resolved = SymbolResolver.resolve(submission.ticker, submission.market, submission.locale)
    symbol_id = resolved.symbol_id if resolved else None
    canonical_ticker = resolved.canonical_ticker if resolved else None
    status = SignalStatus.accepted if resolved else SignalStatus.unresolved
    rejection_reason = None if resolved else "Ticker could not be resolved to a known symbol"

    # 5. Build signal record
    direction = SignalDirection(submission.direction) if submission.direction else None
    signal = SignalCacheRecord(
        signal_cache_id=scid,
        source=submission.source,
        idempotency_key=submission.idempotency_key,
        submitted_ticker=submission.ticker,
        market=submission.market,
        locale=submission.locale,
        signal_type=submission.signal_type,
        direction=direction,
        score=submission.score,
        confidence=submission.confidence,
        horizon=submission.horizon,
        reason=submission.reason,
        tags=submission.tags,
        metadata=submission.metadata,
        symbol_id=symbol_id,
        canonical_ticker=canonical_ticker,
        status=status,
        rejection_reason=rejection_reason,
        received_at=now,
        processed_at=now,
    )

    # 6. Persist signal
    repo.store_signal(signal)

    # 7. Idempotency record
    idem = IdempotencyRecord(
        idempotency_key=submission.idempotency_key,
        source=submission.source,
        signal_cache_id=scid,
        status=status,
        received_at=now,
    )
    repo.set_idempotency(idem)

    # 8. Upsert watchlist entry (even for unresolved – operator can see it)
    weid = keys.watchlist_entry_id(submission.source, submission.signal_type, submission.ticker)
    existing_entry = repo.get_watchlist_entry_by_id(weid)

    watchlist_entry = WatchlistEntry(
        watchlist_entry_id=weid,
        source=submission.source,
        signal_type=submission.signal_type,
        submitted_ticker=submission.ticker,
        canonical_ticker=canonical_ticker,
        symbol_id=symbol_id,
        market=submission.market,
        locale=submission.locale,
        status=WatchlistStatus.active,
        direction=direction,
        score=submission.score,
        confidence=submission.confidence,
        horizon=submission.horizon,
        reason=submission.reason,
        tags=submission.tags,
        metadata=submission.metadata,
        latest_signal_cache_id=scid,
        created_at=existing_entry.created_at if existing_entry else now,
        updated_at=now,
        created_by=submission.source,
    )
    repo.upsert_watchlist_entry(watchlist_entry)

    signal.watchlist_entry_id = weid

    # 9. Archive to Postgres (best-effort, never blocks Redis flow)
    if os.environ.get("DATABASE_URL"):
        try:
            from app.db import get_engine
            from app.repository.signal_archive import archive_signal
            archive_signal(get_engine(), signal)
        except Exception:
            log.exception("Postgres archive failed for %s – Redis write succeeded", scid)

    return signal, watchlist_entry
