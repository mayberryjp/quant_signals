# Signal Producer Integration Guide

## Overview

Signal producers submit ticker-level signals to the watchlist service via
`POST /signals`. Each signal says: "source X believes ticker Y should be
watched because of reason Z."

## Endpoint

```
POST /signals
Content-Type: application/json
```

## Required Fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `source` | string | 1–128 chars | Producer name (e.g. `momentum-v1`) |
| `idempotency_key` | string | 1–512 chars | Unique per submission |
| `ticker` | string | 1–20 chars | Ticker symbol |
| `reason` | string | max 2000 chars | Why this ticker is a candidate |

## Optional Fields

| Field | Type | Constraints | Default |
|---|---|---|---|
| `market` | string | max 32 chars | `stocks` |
| `locale` | string | max 8 chars | `us` |
| `signal_type` | string | max 64 chars | `watchlist_candidate` |
| `direction` | string | `long`, `short`, `neutral` | `null` |
| `score` | float | 0.0–1.0 | `null` |
| `confidence` | float | 0.0–1.0 | `null` |
| `horizon` | string | max 32 chars | `null` |
| `tags` | array[string] | max 20 items | `[]` |
| `metadata` | object | max 16 KB | `{}` |

## Idempotency Rules

- The combination of `source` + `idempotency_key` must be unique within 24 hours
- Recommended format: `<source>:<date>:<ticker>` (e.g. `momentum-v1:2026-06-09:AAPL`)
- Duplicate submissions return `{"status": "duplicate"}` with the original signal_cache_id
- After the 24-hour TTL expires, the same idempotency key can be reused

## Source Naming

- Source names should be lowercase alphanumeric with hyphens
- Versions should be appended: `momentum-v1`, `mean-reversion-v2`
- Sources are auto-registered on first submission

## Example Request

```json
{
  "source": "momentum-v1",
  "idempotency_key": "momentum-v1:2026-06-09:AAPL",
  "ticker": "AAPL",
  "market": "stocks",
  "locale": "us",
  "signal_type": "watchlist_candidate",
  "direction": "long",
  "score": 0.87,
  "confidence": 0.72,
  "horizon": "5d",
  "reason": "Relative strength breakout with above-average volume",
  "tags": ["momentum", "breakout", "volume"],
  "metadata": {
    "strategy_version": "momentum-v1.0",
    "lookback_days": 20,
    "relative_volume": 2.4
  }
}
```

## Response States

| Status | Meaning |
|---|---|
| `accepted` | Signal accepted, watchlist entry created/updated |
| `duplicate` | Idempotency key already used within TTL window |
| `unresolved` | Ticker could not be resolved to a known symbol |

## Watchlist State Transitions

```
(new signal) → accepted → active watchlist entry
(new signal, unknown ticker) → unresolved → active watchlist entry (no symbol_id)
(duplicate idempotency key) → duplicate → no watchlist change
(operator PATCH) → active → inactive (deactivated)
(TTL expiry) → entry removed from Redis
```

## Second Producer Example

```json
{
  "source": "mean-reversion-v1",
  "idempotency_key": "mr-v1:2026-06-09:TSLA",
  "ticker": "TSLA",
  "market": "stocks",
  "locale": "us",
  "signal_type": "watchlist_candidate",
  "direction": "long",
  "score": 0.65,
  "confidence": 0.58,
  "horizon": "3d",
  "reason": "Price 2.1 std devs below 20-day mean with RSI oversold",
  "tags": ["mean-reversion", "oversold", "rsi"],
  "metadata": {
    "strategy_version": "mr-v1.0",
    "z_score": -2.1,
    "rsi_14": 28.3
  }
}
```
