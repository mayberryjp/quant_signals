"""Postgres repository – archive signal records for historical persistence."""

from __future__ import annotations

import json
import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.models.domain import SignalCacheRecord

log = logging.getLogger("quant_signals.archive")


def archive_signal(engine: Engine, record: SignalCacheRecord) -> None:
    """Write a signal record to the Postgres signal_archive table.

    Duplicate idempotency keys are silently ignored (ON CONFLICT DO NOTHING)
    so this is safe to call on every ingest.
    """
    sql = text("""
        INSERT INTO signal_cache.signal_archive (
            signal_cache_id, source, idempotency_key,
            submitted_ticker, canonical_ticker, symbol_id,
            market, locale, signal_type,
            direction, score, confidence, horizon,
            reason, tags, metadata,
            status, rejection_reason,
            received_at, processed_at,
            watchlist_entry_id, schema_version
        ) VALUES (
            :signal_cache_id, :source, :idempotency_key,
            :submitted_ticker, :canonical_ticker, :symbol_id,
            :market, :locale, :signal_type,
            :direction, :score, :confidence, :horizon,
            :reason, :tags::jsonb, :metadata::jsonb,
            :status, :rejection_reason,
            :received_at, :processed_at,
            :watchlist_entry_id, :schema_version
        )
        ON CONFLICT (source, idempotency_key) DO NOTHING
    """)

    params = {
        "signal_cache_id": record.signal_cache_id,
        "source": record.source,
        "idempotency_key": record.idempotency_key,
        "submitted_ticker": record.submitted_ticker,
        "canonical_ticker": record.canonical_ticker,
        "symbol_id": record.symbol_id,
        "market": record.market,
        "locale": record.locale,
        "signal_type": record.signal_type,
        "direction": record.direction.value if record.direction else None,
        "score": record.score,
        "confidence": record.confidence,
        "horizon": record.horizon,
        "reason": record.reason,
        "tags": json.dumps(record.tags),
        "metadata": json.dumps(record.metadata),
        "status": record.status.value,
        "rejection_reason": record.rejection_reason,
        "received_at": record.received_at,
        "processed_at": record.processed_at,
        "watchlist_entry_id": record.watchlist_entry_id,
        "schema_version": record.schema_version,
    }

    try:
        with engine.connect() as conn:
            conn.execute(sql, params)
            conn.commit()
    except Exception:
        log.exception("Failed to archive signal %s to Postgres", record.signal_cache_id)
