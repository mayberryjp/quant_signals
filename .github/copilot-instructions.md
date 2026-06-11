# Copilot Instructions

## Build & Run

```bash
pip install -r requirements.txt          # runtime deps
pip install -e ".[dev]"                   # adds pytest, webtest, fakeredis

# API server (Waitress, port 8016 by default)
python -m app.main

# Maintenance worker (separate process)
python -m app.services.maintenance_worker
```

## Testing

```bash
pytest -v                                 # full suite
pytest tests/test_slice2_signal_intake.py # single file
pytest -k "test_submit_signal_accepted"   # single test by name
```

Tests use `fakeredis` (no real Redis needed) and `webtest.TestApp` for HTTP integration. See `tests/conftest.py` for shared fixtures: `fake_redis`, `repo`, `app_client`, and factory helpers `make_signal_record()`/`make_watchlist_entry()`.

## Architecture

This is a **Bottle** web application (not FastAPI/Flask) served by **Waitress** in production. Redis is the sole runtime data store — no SQL database in the hot path.

**Request flow:** Route handler → Service layer → `SignalCacheRepository` (Redis operations)

- `app/routes/` — Bottle sub-apps merged into `app/main.py`. Each route file creates `sub = Bottle()`.
- `app/services/` — Business logic. `signal_service.ingest_signal()` orchestrates validation, idempotency check, symbol resolution, and persistence.
- `app/redis/repository.py` — `SignalCacheRepository` class encapsulates all Redis reads/writes.
- `app/redis/keys.py` — All Redis key patterns. Keys use `qs:` prefix with colon-delimited segments.
- `app/models/` — Pydantic v2 models split into `domain.py` (internal), `requests.py` (input), `responses.py` (output).
- `app/config.py` — `pydantic-settings` with `QUANT_` env prefix (e.g., `QUANT_REDIS_URL`).

**Maintenance worker** runs as a separate process, writes a heartbeat key. The `/signal-cache/ready` endpoint checks this heartbeat.

## Key Conventions

- **Redis key patterns** are defined exclusively in `app/redis/keys.py`. Never construct key strings inline.
- **Public-facing IDs** (e.g., `signal:source:key`, `watchlist:source:type:TICKER`) match the Redis key minus the `qs:` prefix, so operators can correlate API responses with Redis keys.
- **Pydantic models** serialize directly to Redis via `model.model_dump_json()` and deserialize with `Model.model_validate_json()`.
- **Test organization** uses numbered "slices" (`test_slice1_...` through `test_slice8_...`) covering distinct feature areas.
- **Dependency injection** for tests: override `app.redis.client._pool` with a `fakeredis` instance (see `app_client` fixture).
- **Environment variables** use the `QUANT_` prefix (configured in `app/config.py`).
- **Tickers are uppercased** at the key/index layer (`ticker.upper()` in `keys.py`).
