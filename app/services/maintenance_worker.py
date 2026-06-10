"""Cache maintenance worker – runs as a supervised long-lived process."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from app.redis.client import get_redis
from app.redis.repository import SignalCacheRepository

logger = logging.getLogger("quant_signals.maintenance")


def maintenance_loop(interval: int) -> None:
    """Continuously prune expired indexes and write heartbeat."""
    logger.info("Cache maintenance worker starting (interval=%ds)", interval)
    while True:
        try:
            r = get_redis()
            repo = SignalCacheRepository(r)
            removed = repo.prune_recent_signals()
            repo.set_heartbeat()
            if removed:
                logger.info("Pruned %d expired signal index entries", removed)
        except Exception:
            logger.exception("Maintenance cycle failed – will retry next cycle")
        time.sleep(interval)


def run_worker() -> None:
    """Entry point for the maintenance worker process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", type=int,
                        default=int(os.environ.get("MAINTENANCE_INTERVAL", "60")))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.once:
        r = get_redis()
        repo = SignalCacheRepository(r)
        removed = repo.prune_recent_signals()
        repo.set_heartbeat()
        logger.info("Single pass complete – pruned %d entries", removed)
    else:
        maintenance_loop(args.schedule)


if __name__ == "__main__":
    run_worker()
