"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.redis.client import close_redis
from app.routes import health, signals, watchlist


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="Quant Signals – Signal Cache & Watchlist Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(signals.router)
app.include_router(watchlist.router)
