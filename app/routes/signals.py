"""Signal intake routes (Slice 2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_repo
from app.models.requests import SignalSubmission
from app.models.responses import SignalAcceptedResponse, SignalDetailResponse
from app.redis.repository import SignalCacheRepository
from app.services.signal_service import ingest_signal

router = APIRouter(tags=["signals"])


@router.post("/signals", response_model=SignalAcceptedResponse, status_code=201)
async def submit_signal(
    body: SignalSubmission,
    repo: SignalCacheRepository = Depends(get_repo),
):
    signal, watchlist_entry = await ingest_signal(body, repo)
    status_code = 201 if signal.status.value != "duplicate" else 200
    return SignalAcceptedResponse(
        status=signal.status.value,
        signal_cache_id=signal.signal_cache_id,
        watchlist_status=watchlist_entry.status.value if watchlist_entry else None,
        watchlist_entry_id=watchlist_entry.watchlist_entry_id if watchlist_entry else None,
    )


@router.get("/signals/recent", response_model=list[SignalDetailResponse])
async def recent_signals(
    limit: int = 50,
    repo: SignalCacheRepository = Depends(get_repo),
):
    records = await repo.get_recent_signals(limit=min(limit, 200))
    return [SignalDetailResponse(**r.model_dump()) for r in records]


@router.get("/signals/{signal_cache_id:path}", response_model=SignalDetailResponse)
async def get_signal(
    signal_cache_id: str,
    repo: SignalCacheRepository = Depends(get_repo),
):
    rec = await repo.get_signal_by_id(signal_cache_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return SignalDetailResponse(**rec.model_dump())
