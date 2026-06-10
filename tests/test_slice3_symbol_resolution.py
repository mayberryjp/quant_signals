"""Slice 3 tests: Symbol resolution and cache enrichment."""

from __future__ import annotations

import pytest

from app.models.domain import SignalStatus
from app.models.requests import SignalSubmission
from app.redis.repository import SignalCacheRepository
from app.services.signal_service import ingest_signal
from app.services.symbol_resolver import ResolvedSymbol, SymbolResolver, _StubBackend


@pytest.fixture(autouse=True)
def clean_resolver():
    SymbolResolver.set_backend(_StubBackend())
    yield
    SymbolResolver.set_backend(_StubBackend())


def _submission(**overrides) -> SignalSubmission:
    defaults = dict(
        source="test",
        idempotency_key="k1",
        ticker="AAPL",
        reason="test",
    )
    defaults.update(overrides)
    return SignalSubmission(**defaults)


class TestSymbolResolution:
    def test_resolved_ticker(self, repo: SignalCacheRepository):
        backend = _StubBackend()
        backend.seed("AAPL", ResolvedSymbol(symbol_id=1, canonical_ticker="AAPL"))
        SymbolResolver.set_backend(backend)

        signal, wl = ingest_signal(_submission(), repo)
        assert signal.status == SignalStatus.accepted
        assert signal.symbol_id == 1
        assert signal.canonical_ticker == "AAPL"
        assert wl is not None
        assert wl.symbol_id == 1

    def test_unresolved_ticker(self, repo: SignalCacheRepository):
        signal, wl = ingest_signal(_submission(ticker="ZZZZ", idempotency_key="k-z"), repo)
        assert signal.status == SignalStatus.unresolved
        assert signal.rejection_reason is not None
        assert wl is not None
        assert wl.symbol_id is None

    def test_inactive_ticker(self, repo: SignalCacheRepository):
        backend = _StubBackend()
        backend.seed("OLD", ResolvedSymbol(symbol_id=99, canonical_ticker="OLD", active=False))
        SymbolResolver.set_backend(backend)

        signal, wl = ingest_signal(_submission(ticker="OLD", idempotency_key="k-old"), repo)
        # Inactive tickers still resolve – operator can see the active flag
        assert signal.status == SignalStatus.accepted
        assert signal.symbol_id == 99

    def test_duplicate_prevention(self, repo: SignalCacheRepository):
        backend = _StubBackend()
        backend.seed("AAPL", ResolvedSymbol(symbol_id=1, canonical_ticker="AAPL"))
        SymbolResolver.set_backend(backend)

        ingest_signal(_submission(), repo)
        signal2, wl2 = ingest_signal(_submission(), repo)
        assert signal2.status == SignalStatus.duplicate
        assert wl2 is None

    def test_resolver_failure_handled(self, repo: SignalCacheRepository):
        class _FailBackend:
            def resolve(self, ticker, market, locale):
                raise RuntimeError("db down")

        SymbolResolver.set_backend(_FailBackend())
        signal, wl = ingest_signal(_submission(idempotency_key="k-fail"), repo)
        assert signal.status == SignalStatus.unresolved
