"""Signal intake routes (Slice 2)."""

from __future__ import annotations

import json

from bottle import Bottle, HTTPResponse, request, response
from pydantic import ValidationError

from app.dependencies import get_repo
from app.models.requests import SignalSubmission
from app.models.responses import SignalAcceptedResponse, SignalDetailResponse
from app.services.signal_service import ingest_signal

sub = Bottle()


@sub.post('/signals')
def submit_signal():
    try:
        body = SignalSubmission(**(request.json or {}))
    except ValidationError as e:
        raise HTTPResponse(
            status=422,
            body=json.dumps({"detail": json.loads(e.json())}),
            content_type="application/json",
        )
    repo = get_repo()
    signal, watchlist_entry = ingest_signal(body, repo)
    resp = SignalAcceptedResponse(
        status=signal.status.value,
        signal_cache_id=signal.signal_cache_id,
        watchlist_status=watchlist_entry.status.value if watchlist_entry else None,
        watchlist_entry_id=watchlist_entry.watchlist_entry_id if watchlist_entry else None,
    )
    response.status = 201
    return resp.model_dump(mode="json")


@sub.get('/signals/recent')
def recent_signals():
    limit = int(request.params.get('limit', 50))
    repo = get_repo()
    records = repo.get_recent_signals(limit=min(limit, 200))
    data = [SignalDetailResponse(**r.model_dump()).model_dump(mode="json") for r in records]
    response.content_type = 'application/json'
    return json.dumps(data)


@sub.get('/signals/<signal_cache_id:path>')
def get_signal(signal_cache_id):
    repo = get_repo()
    rec = repo.get_signal_by_id(signal_cache_id)
    if rec is None:
        raise HTTPResponse(
            status=404,
            body=json.dumps({"detail": "Signal not found"}),
            content_type="application/json",
        )
    return SignalDetailResponse(**rec.model_dump()).model_dump(mode="json")
