"""0001 – Signal cache schema.

Revision ID: 0001_signal_cache
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_signal_cache"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS signal_cache")

    # -- signal archive (immutable, append-only) --
    op.execute("""
        CREATE TABLE signal_cache.signal_archive (
            id                SERIAL PRIMARY KEY,
            signal_cache_id   TEXT NOT NULL,
            source            TEXT NOT NULL,
            idempotency_key   TEXT NOT NULL,
            submitted_ticker  TEXT NOT NULL,
            canonical_ticker  TEXT,
            symbol_id         INTEGER,
            market            TEXT NOT NULL DEFAULT 'stocks',
            locale            TEXT NOT NULL DEFAULT 'us',
            signal_type       TEXT NOT NULL DEFAULT 'watchlist_candidate',
            direction         TEXT,
            score             DOUBLE PRECISION,
            confidence        DOUBLE PRECISION,
            horizon           TEXT,
            reason            TEXT NOT NULL DEFAULT '',
            tags              JSONB NOT NULL DEFAULT '[]',
            metadata          JSONB NOT NULL DEFAULT '{}',
            status            TEXT NOT NULL DEFAULT 'accepted',
            rejection_reason  TEXT,
            received_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            processed_at      TIMESTAMPTZ,
            watchlist_entry_id TEXT,
            schema_version    INTEGER NOT NULL DEFAULT 1,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (source, idempotency_key)
        )
    """)

    op.execute("""
        CREATE INDEX idx_signal_archive_source ON signal_cache.signal_archive (source)
    """)
    op.execute("""
        CREATE INDEX idx_signal_archive_ticker ON signal_cache.signal_archive (submitted_ticker)
    """)
    op.execute("""
        CREATE INDEX idx_signal_archive_status ON signal_cache.signal_archive (status)
    """)
    op.execute("""
        CREATE INDEX idx_signal_archive_received_at ON signal_cache.signal_archive (received_at)
    """)
    op.execute("""
        CREATE INDEX idx_signal_archive_signal_type ON signal_cache.signal_archive (signal_type)
    """)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS signal_cache CASCADE")
