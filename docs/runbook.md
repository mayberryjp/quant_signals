# Operational Runbook

## Health Check

```bash
curl http://localhost:8000/signal-cache/health
# {"status": "ok"}
```

Health endpoint does not depend on Redis. If this fails, the process is down.

## Readiness Check

```bash
curl http://localhost:8000/signal-cache/ready
# {"status": "ready", "redis": "ok", "maintenance_heartbeat": "2026-06-09T10:00:00+00:00"}
```

- `redis: "unavailable"` → Redis is unreachable. Signal intake will fail.
- `maintenance_heartbeat: null` → Maintenance worker is not running or stale.

## Cache Stats

```bash
curl http://localhost:8000/signal-cache/stats
```

Returns counters: `accepted`, `duplicate`, `rejected`, `unresolved`, `failed`,
`expired`, `active_watchlist`, `last_maintenance`.

## Recent Signals

```bash
curl http://localhost:8000/signals/recent?limit=10
```

Returns the most recent signal submissions (up to 200).

## Check a Specific Signal

```bash
curl http://localhost:8000/signals/signal:momentum-v1:momentum-v1:2026-06-09:AAPL
```

## Rejected/Unresolved Signals

Check recent signals and filter by status:

```bash
curl http://localhost:8000/signals/recent?limit=100 | jq '[.[] | select(.status == "unresolved")]'
```

## Watchlist

```bash
# All active entries
curl http://localhost:8000/watchlist

# Filter by source
curl "http://localhost:8000/watchlist?source=momentum-v1"

# Filter by ticker
curl "http://localhost:8000/watchlist?ticker=AAPL"

# Lookup by ticker (all entries)
curl http://localhost:8000/watchlist/by-ticker/AAPL
```

## Manual Watchlist Add

```bash
curl -X POST http://localhost:8000/watchlist \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","reason":"Manual review candidate","source":"operator"}'
```

## Deactivate a Watchlist Entry

```bash
curl -X PATCH http://localhost:8000/watchlist/watchlist:operator:manual:AAPL \
  -H "Content-Type: application/json" \
  -d '{"status":"inactive"}'
```

Deactivation preserves the entry (visible via direct ID lookup) until Redis TTL
expiry (30 days). It is removed from the active index immediately.

## Running the Service

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Start the maintenance worker (separate process)
python -m app.services.maintenance_worker
```

## Running Tests

```bash
pip install -e ".[dev]"
pytest -v
```

## Redis Inspection

```bash
# List all quant-signals keys
redis-cli KEYS "qs:*"

# Check active watchlist count
redis-cli SCARD "qs:idx:watchlist:active"

# Check counters
redis-cli GET "qs:counter:accepted"
redis-cli GET "qs:counter:duplicate"

# Check maintenance heartbeat
redis-cli GET "qs:maintenance:heartbeat"
redis-cli TTL "qs:maintenance:heartbeat"
```

## Known Limitations

- This milestone intentionally does **not** build a Postgres pipeline or fanout system
- No Kafka/NATS/Redis Streams event bus
- No broker integration or trade execution
- No auth/permissions beyond existing project patterns
- No frontend UI
- No external vendor calls during signal intake
- Symbol resolution uses a stub backend unless a real database is configured
