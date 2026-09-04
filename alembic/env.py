import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

SCHEMA = "signals"
VERSION_TABLE = "alembic_version_signal_cache"


def _prepare_signals_schema(connection) -> None:
    """Ensure the signals schema exists and relocate a pre-existing alembic
    version table into it, so Alembic reads the correct current revision
    before running migrations."""
    connection.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
    connection.exec_driver_sql(f"""
        DO $$
        DECLARE
            old_schema text;
        BEGIN
            SELECT table_schema INTO old_schema
            FROM information_schema.tables
            WHERE table_name = '{VERSION_TABLE}'
              AND table_schema <> '{SCHEMA}'
            LIMIT 1;

            IF old_schema IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = '{VERSION_TABLE}'
                  AND table_schema = '{SCHEMA}'
            ) THEN
                EXECUTE format('ALTER TABLE %I.%I SET SCHEMA "{SCHEMA}"', old_schema, '{VERSION_TABLE}');
            END IF;
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
