"""0002 – Relocate project tables into the `signals` schema.

Moves signal_cache.signal_archive into the signals schema (preserving data,
indexes and constraints via ALTER TABLE ... SET SCHEMA) and drops the legacy
signal_cache schema. The alembic version table is relocated separately by
alembic/env.py before migrations run.

Revision ID: 0002_signals_schema
Create Date: 2026-09-04
"""

from alembic import op

revision = "0002_signals_schema"
down_revision = "0001_signal_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS signals")
    op.execute("""
        DO $$
        BEGIN
            IF to_regclass('signal_cache.signal_archive') IS NOT NULL THEN
                ALTER TABLE signal_cache.signal_archive SET SCHEMA signals;
            END IF;
        END $$;
    """)
    op.execute("DROP SCHEMA IF EXISTS signal_cache CASCADE")


def downgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS signal_cache")
    op.execute("""
        DO $$
        BEGIN
            IF to_regclass('signals.signal_archive') IS NOT NULL THEN
                ALTER TABLE signals.signal_archive SET SCHEMA signal_cache;
            END IF;
        END $$;
    """)
