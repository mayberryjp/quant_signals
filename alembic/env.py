import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

SCHEMA = "signals"
VERSION_TABLE = "alembic_version"
LEGACY_SCHEMA = "signal_cache"
LEGACY_VERSION_TABLE = "alembic_version_signal_cache"


def _prepare_signals_schema(connection) -> None:
    """Ensure the `signals` schema exists and migrate any legacy `signal_cache`
    objects into it before Alembic reads its version table.

    Idempotent and safe on fresh databases and on databases created by the older
    signal_cache layout. Moving a table with ALTER TABLE ... SET SCHEMA is a
    metadata-only operation that preserves all rows, indexes and constraints
    (including the sequence owned by the SERIAL id column)."""
    connection.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    # Relocate the archive table out of the legacy schema (data preserved), then
    # drop the legacy schema only once it no longer holds the table. The second
    # guard prevents dropping un-migrated data if both copies somehow coexist.
    connection.exec_driver_sql(f"""
        DO $$
        BEGIN
            IF to_regclass('{LEGACY_SCHEMA}.signal_archive') IS NOT NULL
               AND to_regclass('{SCHEMA}.signal_archive') IS NULL THEN
                ALTER TABLE {LEGACY_SCHEMA}.signal_archive SET SCHEMA "{SCHEMA}";
            END IF;

            IF to_regclass('{LEGACY_SCHEMA}.signal_archive') IS NULL THEN
                DROP SCHEMA IF EXISTS "{LEGACY_SCHEMA}" CASCADE;
            END IF;
        END $$;
    """)

    # Drop the legacy version table (in whatever schema it lives) so revision
    # tracking restarts cleanly in {SCHEMA}.{VERSION_TABLE}. Version tables hold
    # no business data, so this is safe.
    connection.exec_driver_sql(f"""
        DO $$
        DECLARE
            v_schema text;
        BEGIN
            FOR v_schema IN
                SELECT table_schema FROM information_schema.tables
                WHERE table_name = '{LEGACY_VERSION_TABLE}'
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS %I.%I', v_schema, '{LEGACY_VERSION_TABLE}');
            END LOOP;
        END $$;
    """)


def run_migrations_offline() -> None:
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        version_table=VERSION_TABLE,
        version_table_schema=SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    connectable = create_engine(url, pool_pre_ping=True)
    with connectable.connect() as connection:
        with connection.begin():
            _prepare_signals_schema(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=VERSION_TABLE,
            version_table_schema=SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
