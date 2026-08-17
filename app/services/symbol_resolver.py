"""Symbol resolution against a normalized symbol master.

This module provides a pluggable resolver.  The production implementation is
``HttpSymbolBackend``, which calls ``GET /symbols/by-ticker/<TICKER>`` on the
symbol master API.  A stub backend is used in tests.

When the symbol service is unavailable the signal is kept with status
``unresolved`` so operators can inspect it.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from app.config import settings

log = logging.getLogger("quant_signals.symbol_resolver")


@dataclass
class ResolvedSymbol:
    symbol_id: int
    canonical_ticker: str
    name: str | None = None
    market: str = "stocks"
    locale: str = "us"
    active: bool = True
    primary_exchange: str | None = None


class SymbolBackend(Protocol):
    def resolve(self, ticker: str, market: str, locale: str) -> ResolvedSymbol | None: ...


class _StubBackend:
    """In-memory stub used in tests and when no database is configured."""

    def __init__(self) -> None:
        self._data: dict[str, ResolvedSymbol] = {}

    def seed(self, ticker: str, symbol: ResolvedSymbol) -> None:
        self._data[ticker.upper()] = symbol

    def resolve(self, ticker: str, market: str, locale: str) -> ResolvedSymbol | None:
        return self._data.get(ticker.upper())


class SymbolNotFound(Exception):
    """The symbol API returned 404 – the ticker definitively does not exist."""


class SymbolLookupUnavailable(Exception):
    """The symbol API could not be reached or returned an unexpected response."""


class HttpSymbolBackend:
    """Resolves tickers via ``GET {base_url}/symbols/by-ticker/<TICKER>``.

    Results (including 404s) are cached in-process for ``cache_ttl`` seconds to
    keep the ingest path from hammering the symbol service.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float | None = None,
        cache_ttl: int | None = None,
    ) -> None:
        self.base_url = (base_url or settings.symbol_api_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.symbol_api_timeout
        self.cache_ttl = cache_ttl if cache_ttl is not None else settings.symbol_api_cache_ttl
        self._cache: dict[tuple[str, str, str], tuple[float, ResolvedSymbol | None]] = {}
        self._lock = Lock()

    def _build_url(self, ticker: str, market: str, locale: str) -> str:
        query = urllib.parse.urlencode({"market": market, "locale": locale, "active": "true"})
        return f"{self.base_url}/symbols/by-ticker/{urllib.parse.quote(ticker, safe='')}?{query}"

    def lookup(self, ticker: str, market: str, locale: str) -> ResolvedSymbol:
        """Return the resolved symbol, or raise SymbolNotFound / SymbolLookupUnavailable."""
        url = self._build_url(ticker.upper(), market, locale)
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - fixed https base
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise SymbolNotFound(ticker) from exc
            raise SymbolLookupUnavailable(f"HTTP {exc.code} for {ticker}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise SymbolLookupUnavailable(str(exc)) from exc

        if not isinstance(payload, dict) or payload.get("status") == "not_found":
            raise SymbolNotFound(ticker)
        return _parse_symbol(payload, ticker, market, locale)

    def resolve(self, ticker: str, market: str, locale: str) -> ResolvedSymbol | None:
        key = (ticker.upper(), market, locale)
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(key)
            if cached and cached[0] > now:
                return cached[1]

        try:
            result: ResolvedSymbol | None = self.lookup(ticker, market, locale)
        except SymbolNotFound:
            result = None
        except SymbolLookupUnavailable as exc:
            log.warning("Symbol lookup unavailable for %s: %s", ticker, exc)
            return None  # not cached – transient failures should be retried

        with self._lock:
            self._cache[key] = (now + self.cache_ttl, result)
        return result


def _parse_symbol(payload: dict, ticker: str, market: str, locale: str) -> ResolvedSymbol:
    symbol = payload.get("symbol") if isinstance(payload.get("symbol"), dict) else payload
    raw_id = symbol.get("symbol_id", symbol.get("id"))
    try:
        symbol_id = int(raw_id)
    except (TypeError, ValueError):
        symbol_id = 0
    return ResolvedSymbol(
        symbol_id=symbol_id,
        canonical_ticker=str(symbol.get("ticker") or symbol.get("canonical_ticker") or ticker).upper(),
        name=symbol.get("name"),
        market=symbol.get("market") or market,
        locale=symbol.get("locale") or locale,
        active=bool(symbol.get("active", True)),
        primary_exchange=symbol.get("primary_exchange"),
    )


# Singleton resolver
_backend: SymbolBackend = _StubBackend()


class SymbolResolver:
    @staticmethod
    def set_backend(backend: SymbolBackend) -> None:
        global _backend
        _backend = backend

    @staticmethod
    def get_backend() -> SymbolBackend:
        return _backend

    @staticmethod
    def use_symbol_api() -> None:
        """Install the HTTP backend if a symbol API base URL is configured."""
        if settings.symbol_api_base_url:
            SymbolResolver.set_backend(HttpSymbolBackend())
            log.info("Symbol resolution via %s", settings.symbol_api_base_url)

    @staticmethod
    def resolve(ticker: str, market: str = "stocks", locale: str = "us") -> ResolvedSymbol | None:
        try:
            return _backend.resolve(ticker, market, locale)
        except Exception:
            return None
