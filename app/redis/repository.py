"""Redis repository – all read/write operations for signal cache and watchlist."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis as redis_lib

from app.config import settings
from app.models.domain import (
    IdempotencyRecord,
    SignalCacheRecord,
    SignalSource,
    SignalStatus,
    WatchlistEntry,
    WatchlistStatus,
)
from app.redis import keys


class SignalCacheRepository:
    """Encapsulates every Redis interaction for the signal/watchlist domain."""

    def __init__(self, redis: redis_lib.Redis) -> None:
        self.r = redis

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    def get_or_create_source(self, name: str, source_type: str = "strategy") -> SignalSource:
        key = keys.source_key(name)
        raw = self.r.get(key)
        if raw:
            return SignalSource.model_validate_json(raw)
        source = SignalSource(name=name, source_type=source_type)
        self.r.set(key, source.model_dump_json(), ex=settings.source_record_ttl)
        return source

    def get_source(self, name: str) -> SignalSource | None:
        raw = self.r.get(keys.source_key(name))
        return SignalSource.model_validate_json(raw) if raw else None

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def check_idempotency(self, source: str, idem_key: str) -> IdempotencyRecord | None:
        raw = self.r.get(keys.idempotency_key(source, idem_key))
        return IdempotencyRecord.model_validate_json(raw) if raw else None

    def set_idempotency(self, record: IdempotencyRecord) -> None:
        key = keys.idempotency_key(record.source, record.idempotency_key)
        self.r.set(key, record.model_dump_json(), ex=settings.idempotency_key_ttl)

    # ------------------------------------------------------------------
    # Signal cache records
    # ------------------------------------------------------------------

    def store_signal(self, record: SignalCacheRecord) -> None:
        key = keys.signal_key(record.source, record.idempotency_key)
        self.r.set(key, record.model_dump_json(), ex=settings.signal_record_ttl)
        # Add to recent signals index
        score = record.received_at.timestamp()
        self.r.zadd(keys.RECENT_SIGNALS_INDEX, {record.signal_cache_id: score})
        # Bump counter
        self.r.incr(keys.counter_key(record.status.value))

    def get_signal(self, source: str, idem_key: str) -> SignalCacheRecord | None:
        raw = self.r.get(keys.signal_key(source, idem_key))
        return SignalCacheRecord.model_validate_json(raw) if raw else None

    def get_signal_by_id(self, signal_cache_id: str) -> SignalCacheRecord | None:
        """Resolve a signal_cache_id like 'signal:src:key' back to its record."""
        parts = signal_cache_id.split(":", 2)
        if len(parts) != 3 or parts[0] != "signal":
            return None
        return self.get_signal(parts[1], parts[2])

    def get_recent_signals(self, limit: int = 50) -> list[SignalCacheRecord]:
        ids: list[str] = self.r.zrevrange(keys.RECENT_SIGNALS_INDEX, 0, limit - 1)
        results: list[SignalCacheRecord] = []
        for sid in ids:
            rec = self.get_signal_by_id(sid)
            if rec:
                results.append(rec)
        return results

    # ------------------------------------------------------------------
    # Watchlist entries
    # ------------------------------------------------------------------

    def upsert_watchlist_entry(self, entry: WatchlistEntry) -> None:
        key = keys.watchlist_key(entry.source, entry.signal_type, entry.submitted_ticker)
        self.r.set(key, entry.model_dump_json(), ex=settings.watchlist_entry_ttl)
        self._update_watchlist_indexes(entry)

    def get_watchlist_entry(self, source: str, signal_type: str, ticker: str) -> WatchlistEntry | None:
        raw = self.r.get(keys.watchlist_key(source, signal_type, ticker))
        return WatchlistEntry.model_validate_json(raw) if raw else None

    def get_watchlist_entry_by_id(self, entry_id: str) -> WatchlistEntry | None:
        parts = entry_id.split(":", 3)
        if len(parts) != 4 or parts[0] != "watchlist":
            return None
        return self.get_watchlist_entry(parts[1], parts[2], parts[3])

    def deactivate_watchlist_entry(self, entry_id: str, reason: str | None = None) -> WatchlistEntry | None:
        entry = self.get_watchlist_entry_by_id(entry_id)
        if entry is None:
            return None
        entry.status = WatchlistStatus.inactive
        entry.updated_at = datetime.now(timezone.utc)
        if reason:
            entry.reason = reason
        key = keys.watchlist_key(entry.source, entry.signal_type, entry.submitted_ticker)
        self.r.set(key, entry.model_dump_json(), ex=settings.watchlist_entry_ttl)
        # Move from active index
        self.r.srem(keys.ACTIVE_WATCHLIST_INDEX, entry.watchlist_entry_id)
        return entry

    def patch_watchlist_entry(
        self, entry_id: str, *, status: str | None = None, reason: str | None = None,
        tags: list[str] | None = None, metadata: dict[str, Any] | None = None,
    ) -> WatchlistEntry | None:
        entry = self.get_watchlist_entry_by_id(entry_id)
        if entry is None:
            return None
        if status is not None:
            entry.status = WatchlistStatus(status)
        if reason is not None:
            entry.reason = reason
        if tags is not None:
            entry.tags = tags
        if metadata is not None:
            entry.metadata = metadata
        entry.updated_at = datetime.now(timezone.utc)
        key = keys.watchlist_key(entry.source, entry.signal_type, entry.submitted_ticker)
        self.r.set(key, entry.model_dump_json(), ex=settings.watchlist_entry_ttl)
        self._update_watchlist_indexes(entry)
        return entry

    def _update_watchlist_indexes(self, entry: WatchlistEntry) -> None:
        eid = entry.watchlist_entry_id
        if entry.status == WatchlistStatus.active:
            self.r.sadd(keys.ACTIVE_WATCHLIST_INDEX, eid)
        else:
            self.r.srem(keys.ACTIVE_WATCHLIST_INDEX, eid)

        self.r.sadd(keys.watchlist_source_index(entry.source), eid)
        self.r.sadd(keys.watchlist_ticker_index(entry.submitted_ticker), eid)
        self.r.sadd(keys.watchlist_market_index(entry.market), eid)
        self.r.sadd(keys.watchlist_locale_index(entry.locale), eid)
        self.r.sadd(keys.watchlist_signal_type_index(entry.signal_type), eid)
        for tag in entry.tags:
            self.r.sadd(keys.watchlist_tag_index(tag), eid)

    def list_watchlist(
        self,
        *,
        active_only: bool = True,
        source: str | None = None,
        ticker: str | None = None,
        market: str | None = None,
        locale: str | None = None,
        tag: str | None = None,
        signal_type: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[WatchlistEntry], int]:
        """Return paginated watchlist entries matching filters."""
        # Start with active or all
        sets_to_intersect: list[str] = []
        if active_only:
            sets_to_intersect.append(keys.ACTIVE_WATCHLIST_INDEX)
        if source:
            sets_to_intersect.append(keys.watchlist_source_index(source))
        if ticker:
            sets_to_intersect.append(keys.watchlist_ticker_index(ticker))
        if market:
            sets_to_intersect.append(keys.watchlist_market_index(market))
        if locale:
            sets_to_intersect.append(keys.watchlist_locale_index(locale))
        if tag:
            sets_to_intersect.append(keys.watchlist_tag_index(tag))
        if signal_type:
            sets_to_intersect.append(keys.watchlist_signal_type_index(signal_type))

        if len(sets_to_intersect) == 0:
            # No filter – scan all active
            sets_to_intersect.append(keys.ACTIVE_WATCHLIST_INDEX)

        if len(sets_to_intersect) == 1:
            ids: set[str] = self.r.smembers(sets_to_intersect[0])
        else:
            # Intersect into a temp key
            tmp = f"{keys.PREFIX}:_tmp_intersect"
            self.r.sinterstore(tmp, *sets_to_intersect)
            ids = self.r.smembers(tmp)
            self.r.delete(tmp)

        sorted_ids = sorted(ids)
        total = len(sorted_ids)
        start = (page - 1) * page_size
        page_ids = sorted_ids[start : start + page_size]

        entries: list[WatchlistEntry] = []
        for eid in page_ids:
            entry = self.get_watchlist_entry_by_id(eid)
            if entry:
                entries.append(entry)
        return entries, total

    def get_watchlist_entries_by_ticker(self, ticker: str) -> list[WatchlistEntry]:
        ids: set[str] = self.r.smembers(keys.watchlist_ticker_index(ticker))
        entries: list[WatchlistEntry] = []
        for eid in ids:
            entry = self.get_watchlist_entry_by_id(eid)
            if entry:
                entries.append(entry)
        return entries

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------

    def get_counters(self) -> dict[str, int]:
        names = ["accepted", "duplicate", "rejected", "unresolved", "failed", "expired"]
        result: dict[str, int] = {}
        for n in names:
            val = self.r.get(keys.counter_key(n))
            result[n] = int(val) if val else 0
        return result

    def get_active_watchlist_count(self) -> int:
        return self.r.scard(keys.ACTIVE_WATCHLIST_INDEX)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def set_heartbeat(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.r.set(keys.MAINTENANCE_HEARTBEAT, now, ex=settings.maintenance_heartbeat_ttl)
        self.r.set(keys.MAINTENANCE_LAST_CLEANUP, now)

    def get_heartbeat(self) -> str | None:
        return self.r.get(keys.MAINTENANCE_HEARTBEAT)

    def get_last_cleanup(self) -> str | None:
        return self.r.get(keys.MAINTENANCE_LAST_CLEANUP)

    def prune_recent_signals(self, max_age_seconds: int | None = None) -> int:
        """Remove entries from the recent-signals sorted set older than max_age."""
        if max_age_seconds is None:
            max_age_seconds = settings.signal_record_ttl
        cutoff = datetime.now(timezone.utc).timestamp() - max_age_seconds
        removed: int = self.r.zremrangebyscore(keys.RECENT_SIGNALS_INDEX, "-inf", cutoff)
        return removed
