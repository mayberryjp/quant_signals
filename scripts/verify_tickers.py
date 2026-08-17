#!/usr/bin/env python3
"""One-off audit: verify every watchlist ticker against the symbol master API.

Each distinct (ticker, market, locale) is looked up once via
``GET {symbol-api}/symbols/by-ticker/<TICKER>``.  Entries whose ticker returns
404 are removed (or deactivated with ``--deactivate``).  Tickers whose lookup
failed for transient reasons are reported and left untouched.

Usage
-----
    python -m scripts.verify_tickers --dry-run
    python -m scripts.verify_tickers
    python -m scripts.verify_tickers --deactivate
    python -m scripts.verify_tickers --include-inactive --api-base https://signals.quant.mayberry.farm
"""

from __future__ import annotations

import argparse
import sys

from app.redis.client import get_redis
from app.redis.repository import SignalCacheRepository
from app.services.symbol_resolver import (
    HttpSymbolBackend,
    SymbolLookupUnavailable,
    SymbolNotFound,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verify watchlist tickers against the symbol API.")
    p.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    p.add_argument(
        "--deactivate",
        action="store_true",
        help="mark unknown entries inactive instead of deleting them",
    )
    p.add_argument(
        "--include-inactive",
        action="store_true",
        help="also audit entries that are already inactive",
    )
    p.add_argument("--api-base", default=None, help="override the symbol API base URL")
    p.add_argument("--timeout", type=float, default=None, help="per-request timeout in seconds")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    backend = HttpSymbolBackend(args.api_base, timeout=args.timeout, cache_ttl=3600)
    repo = SignalCacheRepository(get_redis())

    entries, total = repo.list_watchlist(active_only=not args.include_inactive, page_size=None)
    print(f"Auditing {total} watchlist entries against {backend.base_url}\n")

    verdicts: dict[tuple[str, str, str], str] = {}
    kept = removed = unavailable = 0
    failed_tickers: set[str] = set()

    for entry in entries:
        ticker = (entry.canonical_ticker or entry.submitted_ticker).upper()
        cache_key = (ticker, entry.market, entry.locale)

        if cache_key not in verdicts:
            try:
                backend.lookup(ticker, entry.market, entry.locale)
                verdicts[cache_key] = "ok"
            except SymbolNotFound:
                verdicts[cache_key] = "not_found"
            except SymbolLookupUnavailable as exc:
                verdicts[cache_key] = "unavailable"
                print(f"  ! {ticker}: lookup failed ({exc})")

        verdict = verdicts[cache_key]
        if verdict == "ok":
            kept += 1
            continue
        if verdict == "unavailable":
            unavailable += 1
            failed_tickers.add(ticker)
            continue

        action = "deactivate" if args.deactivate else "delete"
        if args.dry_run:
            print(f"  [dry-run] would {action} {entry.watchlist_entry_id} ({ticker} not found)")
        else:
            if args.deactivate:
                repo.deactivate_watchlist_entry(
                    entry.watchlist_entry_id, reason="Ticker not found in symbol master"
                )
            else:
                repo.delete_watchlist_entry(entry.watchlist_entry_id)
            print(f"  {action}d {entry.watchlist_entry_id} ({ticker} not found)")
        removed += 1

    print(
        f"\nDone. valid={kept} "
        f"{'would-' if args.dry_run else ''}{'deactivate' if args.deactivate else 'delete'}d={removed} "
        f"skipped-unavailable={unavailable}"
    )
    if failed_tickers:
        print("Re-run later for: " + ", ".join(sorted(failed_tickers)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
