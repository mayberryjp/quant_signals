# quant_signals

Redis-backed signal cache and watchlist service for quantitative trading signals.

## Quick Start

```bash
pip install -r requirements.txt

# Run API server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run maintenance worker (separate process)
python -m app.services.maintenance_worker

# Run tests
pip install -e ".[dev]"
pytest -v
```

## Architecture

Multiple signal producers submit ticker-level signals via `POST /signals`.
Each signal is validated, deduplicated by idempotency key, resolved against a
symbol master when available, and persisted in Redis. Accepted signals create
or update watchlist entries queryable through the read API.

Redis is the sole runtime cache – no Postgres pipeline or fanout system.

## Documentation

- [Redis Key Contracts](docs/redis_contracts.md) – key patterns, TTLs, schemas
- [Producer Guide](docs/producer_guide.md) – integration contract and examples
- [Runbook](docs/runbook.md) – operational commands and troubleshooting

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/signal-cache/health` | Liveness (no Redis dependency) |
| GET | `/signal-cache/ready` | Readiness (Redis + maintenance) |
| GET | `/signal-cache/stats` | Operational counters |
| POST | `/signals` | Submit a signal |
| GET | `/signals/recent` | Recent signals |
| GET | `/signals/{id}` | Signal detail |
| GET | `/watchlist` | List watchlist (filters, pagination) |
| GET | `/watchlist/{id}` | Watchlist entry detail |
| GET | `/watchlist/by-ticker/{ticker}` | Lookup by ticker |
| POST | `/watchlist` | Manual watchlist add |
| PATCH | `/watchlist/{id}` | Update/deactivate entry |
