"""Watchlist routes (Slices 4 & 5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.dependencies import get_repo
from app.models.requests import ManualWatchlistAdd, WatchlistPatch
from app.models.responses import WatchlistEntryResponse, WatchlistListResponse
from app.redis.repository import SignalCacheRepository
from app.services.watchlist_service import manual_add

router = APIRouter(tags=["watchlist"])


@router.get("/watchlist", response_model=WatchlistListResponse)
async def list_watchlist(
    active: bool = True,
    source: str | None = None,
    ticker: str | None = None,
    market: str | None = None,
    locale: str | None = None,
    tag: str | None = None,
    signal_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    repo: SignalCacheRepository = Depends(get_repo),
):
    entries, total = await repo.list_watchlist(
        active_only=active,
        source=source,
        ticker=ticker,
        market=market,
        locale=locale,
        tag=tag,
        signal_type=signal_type,
        page=page,
        page_size=page_size,
    )
    return WatchlistListResponse(
        items=[WatchlistEntryResponse(**e.model_dump()) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/watchlist/by-ticker/{ticker}", response_model=list[WatchlistEntryResponse])
async def watchlist_by_ticker(
    ticker: str,
    repo: SignalCacheRepository = Depends(get_repo),
):
    entries = await repo.get_watchlist_entries_by_ticker(ticker)
    return [WatchlistEntryResponse(**e.model_dump()) for e in entries]


@router.get("/watchlist/{watchlist_entry_id:path}", response_model=WatchlistEntryResponse)
async def get_watchlist_entry(
    watchlist_entry_id: str,
    repo: SignalCacheRepository = Depends(get_repo),
):
    entry = await repo.get_watchlist_entry_by_id(watchlist_entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    return WatchlistEntryResponse(**entry.model_dump())


@router.post("/watchlist", response_model=WatchlistEntryResponse, status_code=201)
async def add_to_watchlist(
    body: ManualWatchlistAdd,
    repo: SignalCacheRepository = Depends(get_repo),
):
    entry = await manual_add(body, repo)
    return WatchlistEntryResponse(**entry.model_dump())


@router.patch("/watchlist/{watchlist_entry_id:path}", response_model=WatchlistEntryResponse)
async def patch_watchlist_entry(
    watchlist_entry_id: str,
    body: WatchlistPatch,
    repo: SignalCacheRepository = Depends(get_repo),
):
    entry = await repo.patch_watchlist_entry(
        watchlist_entry_id,
        status=body.status,
        reason=body.reason,
        tags=body.tags,
        metadata=body.metadata,
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    return WatchlistEntryResponse(**entry.model_dump())
