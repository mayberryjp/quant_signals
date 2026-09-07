"""Database engine helpers."""
from __future__ import annotations

import os
import time

from sqlalchemy import create_engine as _create_engine, Engine


def get_engine() -> Engine:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    # Pin every connection's session time zone to the container's local zone so
    # TIMESTAMPTZ values are stored and returned in local (New York) time rather
    # than UTC or the server default.
    local_tz = os.environ.get("TZ") or time.tzname[0]
    return _create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"options": f"-c timezone={local_tz}"},
    )
