"""Bottle application entry point."""

from __future__ import annotations

import atexit
import logging
import os
import sys

from bottle import Bottle

from app.redis.client import close_redis
from app.routes import health, signals, watchlist

SERVICE_NAME = "quant-signals-api"
log = logging.getLogger(SERVICE_NAME)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
    force=True,
)

app = Bottle()

app.merge(health.sub)
app.merge(signals.sub)
app.merge(watchlist.sub)

atexit.register(close_redis)

if __name__ == "__main__":
    from waitress import serve

    host = os.environ.get("API_LISTEN_ADDRESS", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8016"))
    log.info("Starting signals API server on %s:%d...", host, port)
    serve(app, host=host, port=port, threads=20)
