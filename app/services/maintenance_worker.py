"""Cache maintenance worker – runs as a supervised long-lived process."""

from __future__ import annotations

import asyncio
import logging

from app.redis.client import get_redis
from app.redis.repository import SignalCacheRepository

logger = logging.getLogger("quant_signals.maintenance")

CYCLE_SECONDS = 60


async def maintenance_loop() -> None:
    """Continuously prune expired indexes and write heartbeat."""
    logger.info("Cache maintenance worker starting")
    while True:
        try:
            r = await get_redis()
            repo = SignalCacheRepository(r)
            removed = await repo.prune_recent_signals()
            await repo.set_heartbeat()
            if removed:
                logger.info("Pruned %d expired signal index entries", removed)
        except Exception:
            logger.exception("Maintenance cycle failed – will retry next cycle")
        await asyncio.sleep(CYCLE_SECONDS)


def run_worker() -> None:
    """Entry point for the maintenance worker process."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    asyncio.run(maintenance_loop())


if __name__ == "__main__":
    run_worker()
