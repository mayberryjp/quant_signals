"""Redis key patterns for the signal cache and watchlist service.

Key naming convention
---------------------
All keys are prefixed with ``qs:`` (quant-signals).

Key patterns
~~~~~~~~~~~~
source:<name>                        → JSON hash of SignalSource
idem:<source>:<idempotency_key>      → JSON of IdempotencyRecord  (TTL: 24 h)
signal:<source>:<idempotency_key>    → JSON of SignalCacheRecord   (TTL: 7 d)
watchlist:<source>:<signal_type>:<ticker>  → JSON of WatchlistEntry (TTL: 30 d)

Secondary index sets
~~~~~~~~~~~~~~~~~~~~
idx:signals:recent                   → sorted set, score = received_at epoch
idx:watchlist:active                 → set of active watchlist_entry_id
idx:watchlist:source:<source>        → set of watchlist_entry_id
idx:watchlist:ticker:<TICKER>        → set of watchlist_entry_id
idx:watchlist:market:<market>        → set of watchlist_entry_id
idx:watchlist:locale:<locale>        → set of watchlist_entry_id
idx:watchlist:tag:<tag>              → set of watchlist_entry_id
idx:watchlist:signal_type:<type>     → set of watchlist_entry_id

Counters
~~~~~~~~
counter:accepted
counter:duplicate
counter:rejected
counter:unresolved
counter:failed
counter:expired

Maintenance
~~~~~~~~~~~
maintenance:heartbeat                → ISO timestamp (TTL: 5 min)
maintenance:last_cleanup             → ISO timestamp
"""

PREFIX = "qs"


def _p(*parts: str) -> str:
    return f"{PREFIX}:{':'.join(parts)}"


# ---------------------------------------------------------------------------
# Primary keys
# ---------------------------------------------------------------------------

def source_key(name: str) -> str:
    return _p("source", name)


def idempotency_key(source: str, idem_key: str) -> str:
    return _p("idem", source, idem_key)


def signal_key(source: str, idem_key: str) -> str:
    return _p("signal", source, idem_key)


def watchlist_key(source: str, signal_type: str, ticker: str) -> str:
    return _p("watchlist", source, signal_type, ticker.upper())


# ---------------------------------------------------------------------------
# Public-facing IDs (stored in models, returned in API responses)
# These intentionally match the Redis key minus the global prefix so that
# operators can mentally correlate API ids with Redis keys.
# ---------------------------------------------------------------------------

def signal_cache_id(source: str, idem_key: str) -> str:
    return f"signal:{source}:{idem_key}"


def watchlist_entry_id(source: str, signal_type: str, ticker: str) -> str:
    return f"watchlist:{source}:{signal_type}:{ticker.upper()}"


# ---------------------------------------------------------------------------
# Index / set keys
# ---------------------------------------------------------------------------

RECENT_SIGNALS_INDEX = _p("idx", "signals", "recent")
ACTIVE_WATCHLIST_INDEX = _p("idx", "watchlist", "active")


def watchlist_source_index(source: str) -> str:
    return _p("idx", "watchlist", "source", source)


def watchlist_ticker_index(ticker: str) -> str:
    return _p("idx", "watchlist", "ticker", ticker.upper())


def watchlist_market_index(market: str) -> str:
    return _p("idx", "watchlist", "market", market)


def watchlist_locale_index(locale: str) -> str:
    return _p("idx", "watchlist", "locale", locale)


def watchlist_tag_index(tag: str) -> str:
    return _p("idx", "watchlist", "tag", tag)


def watchlist_signal_type_index(signal_type: str) -> str:
    return _p("idx", "watchlist", "signal_type", signal_type)


# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

def counter_key(name: str) -> str:
    """name is one of: accepted, duplicate, rejected, unresolved, failed, expired."""
    return _p("counter", name)


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

MAINTENANCE_HEARTBEAT = _p("maintenance", "heartbeat")
MAINTENANCE_LAST_CLEANUP = _p("maintenance", "last_cleanup")
