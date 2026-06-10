"""Symbol resolution against a normalized symbol master.

This module provides a pluggable resolver.  The default implementation is a
stub that can be replaced by injecting a real database-backed resolver via
``SymbolResolver.set_backend()``.

When the symbol database is unavailable the signal is kept with status
``unresolved`` so operators can inspect it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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
    async def resolve(self, ticker: str, market: str, locale: str) -> ResolvedSymbol | None: ...


class _StubBackend:
    """In-memory stub used in tests and when no database is configured."""

    def __init__(self) -> None:
        self._data: dict[str, ResolvedSymbol] = {}

    def seed(self, ticker: str, symbol: ResolvedSymbol) -> None:
        self._data[ticker.upper()] = symbol

    async def resolve(self, ticker: str, market: str, locale: str) -> ResolvedSymbol | None:
        return self._data.get(ticker.upper())


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
    async def resolve(ticker: str, market: str = "stocks", locale: str = "us") -> ResolvedSymbol | None:
        try:
            return await _backend.resolve(ticker, market, locale)
        except Exception:
            return None
