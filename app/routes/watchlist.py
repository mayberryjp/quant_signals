"""Watchlist routes (Slices 4 & 5)."""

from __future__ import annotations

import json

from bottle import Bottle, HTTPResponse, request, response
from pydantic import ValidationError

from app.config import settings
from app.dependencies import get_repo
from app.models.requests import ManualWatchlistAdd, WatchlistPatch
from app.models.responses import WatchlistEntryResponse, WatchlistListResponse
from app.services.watchlist_service import manual_add

sub = Bottle()


@sub.get('/watchlist')
def list_watchlist():
    active = request.params.get('active', 'true').lower() == 'true'
    source = request.params.get('source')
    ticker = request.params.get('ticker')
    market = request.params.get('market')
    locale = request.params.get('locale')
    tag = request.params.get('tag')
    signal_type = request.params.get('signal_type')
    page = int(request.params.get('page', 1))
    page_size_param = request.params.get('page_size')
    # By default, return the full filtered result set.
    if page_size_param is None:
        page_size = None
    else:
        page_size_int = int(page_size_param)
        # page_size=0 (or negative) is treated as "all".
        page_size = None if page_size_int <= 0 else min(page_size_int, settings.max_page_size)

    repo = get_repo()
    entries, total = repo.list_watchlist(
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
    resp = WatchlistListResponse(
        items=[WatchlistEntryResponse(**e.model_dump()) for e in entries],
        total=total,
        page=page,
        page_size=total if page_size is None else page_size,
    )
    return resp.model_dump(mode="json")


@sub.get('/watchlist/by-ticker/<ticker>')
def watchlist_by_ticker(ticker):
    repo = get_repo()
    entries = repo.get_watchlist_entries_by_ticker(ticker)
    data = [WatchlistEntryResponse(**e.model_dump()).model_dump(mode="json") for e in entries]
    response.content_type = 'application/json'
    return json.dumps(data)


@sub.get('/watchlist/<watchlist_entry_id:path>')
def get_watchlist_entry(watchlist_entry_id):
    repo = get_repo()
    entry = repo.get_watchlist_entry_by_id(watchlist_entry_id)
    if entry is None:
        raise HTTPResponse(
            status=404,
            body=json.dumps({"detail": "Watchlist entry not found"}),
            content_type="application/json",
        )
    return WatchlistEntryResponse(**entry.model_dump()).model_dump(mode="json")


@sub.post('/watchlist')
def add_to_watchlist():
    try:
        body = ManualWatchlistAdd(**(request.json or {}))
    except ValidationError as e:
        raise HTTPResponse(
            status=422,
            body=json.dumps({"detail": json.loads(e.json())}),
            content_type="application/json",
        )
    repo = get_repo()
    entry = manual_add(body, repo)
    response.status = 201
    return WatchlistEntryResponse(**entry.model_dump()).model_dump(mode="json")


@sub.route('/watchlist/<watchlist_entry_id:path>', method='PATCH')
def patch_watchlist_entry(watchlist_entry_id):
    try:
        body = WatchlistPatch(**(request.json or {}))
    except ValidationError as e:
        raise HTTPResponse(
            status=422,
            body=json.dumps({"detail": json.loads(e.json())}),
            content_type="application/json",
        )
    repo = get_repo()
    entry = repo.patch_watchlist_entry(
        watchlist_entry_id,
        status=body.status,
        reason=body.reason,
        tags=body.tags,
        metadata=body.metadata,
    )
    if entry is None:
        raise HTTPResponse(
            status=404,
            body=json.dumps({"detail": "Watchlist entry not found"}),
            content_type="application/json",
        )
    return WatchlistEntryResponse(**entry.model_dump()).model_dump(mode="json")
