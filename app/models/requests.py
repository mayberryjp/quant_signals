"""Request schemas for the signal cache and watchlist API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.config import settings


class SignalSubmission(BaseModel):
    """Body of POST /signals."""
    source: str = Field(..., min_length=1, max_length=128)
    idempotency_key: str = Field(..., min_length=1, max_length=512)
    ticker: str = Field(..., min_length=1, max_length=20)
    market: str = Field(default="stocks", max_length=32)
    locale: str = Field(default="us", max_length=8)
    signal_type: str = Field(default="watchlist_candidate", max_length=64)
    direction: str | None = Field(default=None, pattern=r"^(long|short|neutral)$")
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    horizon: str | None = Field(default=None, max_length=32)
    reason: str = Field(default="", max_length=settings.max_reason_length)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def cap_tags(cls, v: list[str]) -> list[str]:
        if len(v) > settings.max_tags:
            raise ValueError(f"at most {settings.max_tags} tags allowed")
        return v


class ManualWatchlistAdd(BaseModel):
    """Body of POST /watchlist."""
    ticker: str = Field(..., min_length=1, max_length=20)
    market: str = Field(default="stocks", max_length=32)
    locale: str = Field(default="us", max_length=8)
    source: str = Field(default="operator", max_length=128)
    reason: str = Field(..., min_length=1, max_length=settings.max_reason_length)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def cap_tags(cls, v: list[str]) -> list[str]:
        if len(v) > settings.max_tags:
            raise ValueError(f"at most {settings.max_tags} tags allowed")
        return v


class WatchlistPatch(BaseModel):
    """Body of PATCH /watchlist/{id}."""
    status: str | None = Field(default=None, pattern=r"^(active|inactive|expired)$")
    reason: str | None = Field(default=None, max_length=settings.max_reason_length)
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
