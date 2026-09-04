"""0001 – Signals schema.

Creates the `signals` schema and the append-only signal_archive table. Every
table owned by this project lives in the `signals` schema, including Alembic's
own version table (configured in alembic/env.py as signals.alembic_version).

Legacy `signal_cache` objects are migrated into `signals` by alembic/env.py
before this runs, so the IF NOT EXISTS guards keep this a no-op on databases
that already hold relocated data.

Revision ID: 0001_signals_schema
Create Date: 2026-06-10
"""

from alembic import op

revision = "0001_signals_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS signals")

    # -- signal archive (immutable, append-only) --
    op.execute("""
        CREATE TABLE IF NOT EXISTS signals.signal_archive (
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

    op.execute("CREATE INDEX IF NOT EXISTS idx_signal_archive_source ON signals.signal_archive (source)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_signal_archive_ticker ON signals.signal_archive (submitted_ticker)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_signal_archive_status ON signals.signal_archive (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_signal_archive_received_at ON signals.signal_archive (received_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_signal_archive_signal_type ON signals.signal_archive (signal_type)")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS signals CASCADE")
