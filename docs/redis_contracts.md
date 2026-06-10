# Redis Key Contracts

All keys are prefixed with `qs:` (quant-signals).

## Primary Keys

| Pattern | Value Type | TTL | Description |
|---|---|---|---|
| `qs:source:<name>` | JSON (SignalSource) | 90 days | Registered signal producer |
| `qs:idem:<source>:<idempotency_key>` | JSON (IdempotencyRecord) | 24 hours | Dedup guard |
| `qs:signal:<source>:<idempotency_key>` | JSON (SignalCacheRecord) | 7 days | Immutable signal record |
| `qs:watchlist:<source>:<signal_type>:<TICKER>` | JSON (WatchlistEntry) | 30 days | Active watchlist entry |

## Index Sets

| Key | Type | Members |
|---|---|---|
| `qs:idx:signals:recent` | Sorted Set (score=epoch) | signal_cache_id values |
| `qs:idx:watchlist:active` | Set | watchlist_entry_id values |
| `qs:idx:watchlist:source:<source>` | Set | watchlist_entry_id values |
| `qs:idx:watchlist:ticker:<TICKER>` | Set | watchlist_entry_id values |
| `qs:idx:watchlist:market:<market>` | Set | watchlist_entry_id values |
| `qs:idx:watchlist:locale:<locale>` | Set | watchlist_entry_id values |
| `qs:idx:watchlist:tag:<tag>` | Set | watchlist_entry_id values |
| `qs:idx:watchlist:signal_type:<type>` | Set | watchlist_entry_id values |

## Counters

| Key | Type | Description |
|---|---|---|
| `qs:counter:accepted` | Integer | Signals accepted |
| `qs:counter:duplicate` | Integer | Duplicate submissions caught |
| `qs:counter:rejected` | Integer | Signals rejected |
| `qs:counter:unresolved` | Integer | Unresolved tickers |
| `qs:counter:failed` | Integer | Processing failures |
| `qs:counter:expired` | Integer | Expired entries |

## Maintenance

| Key | Type | TTL | Description |
|---|---|---|---|
| `qs:maintenance:heartbeat` | ISO timestamp string | 5 min | Worker liveness |
| `qs:maintenance:last_cleanup` | ISO timestamp string | none | Last successful prune |

## Idempotency Behavior

- Keyed by `source` + `idempotency_key`
- If the idempotency record exists, the submission is returned as `duplicate`
- TTL is 24 hours – the same key can be reused after expiry
- The producer is responsible for generating unique idempotency keys

## Watchlist Uniqueness

- Keyed by `source` + `signal_type` + `TICKER` (uppercased)
- Upsert behavior: if the entry already exists, fields are overwritten with latest values
- `created_at` is preserved from the original entry on upsert
- Deactivation sets status to `inactive` but retains the record until TTL expires

## Value Schema Versioning

Every JSON value includes a `schema_version` field (currently `1`). Future code
should check this field before deserializing to support rolling upgrades.

## Identity Model

A ticker string alone is insufficient for reliable identity once aliases,
delistings, and vendor differences are considered. The system stores both:

- `submitted_ticker`: exactly what the producer sent
- `symbol_id` + `canonical_ticker`: the normalized identity from the symbol master

When symbol resolution is unavailable, `symbol_id` is `null` and the entry has
status `unresolved`. This lets operators see and manually resolve unmatched tickers.
