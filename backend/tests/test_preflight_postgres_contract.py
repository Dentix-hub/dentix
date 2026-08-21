import os
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import pytest
from psycopg2 import sql

from backend.scripts import preflight_migrations as preflight


def _postgres_base_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://")):
        pytest.skip("Production migration contract requires PostgreSQL")
    return url


def _url_for_database(url: str, database: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{database}", parts.query, parts.fragment))


def _create_database(base_url: str) -> tuple[str, str]:
    database = f"dentix_contract_{uuid.uuid4().hex[:10]}"
    admin_url = _url_for_database(base_url, "postgres")
    with psycopg2.connect(admin_url) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    return database, _url_for_database(base_url, database)


def _drop_database(base_url: str, database: str) -> None:
    admin_url = _url_for_database(base_url, "postgres")
    with psycopg2.connect(admin_url) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
                """,
                (database,),
            )
            cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database)))


def test_preflight_bootstraps_fresh_database_then_upgrades_existing(monkeypatch):
    base_url = _postgres_base_url()
    database, database_url = _create_database(base_url)
    try:
        monkeypatch.setenv("DATABASE_URL", database_url)

        assert preflight.run_alembic_upgrade() is True
        assert preflight.run_migration_health_check() is True

        # The second pass must take the existing Alembic-versioned path and be
        # idempotent. This is the path production takes on normal deployments.
        assert preflight.run_alembic_upgrade() is True
        assert preflight.run_migration_health_check() is True
    finally:
        _drop_database(base_url, database)


def test_preflight_resumes_interrupted_fresh_bootstrap(monkeypatch):
    base_url = _postgres_base_url()
    database, database_url = _create_database(base_url)
    try:
        with psycopg2.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f'''CREATE TABLE "{preflight.BOOTSTRAP_MARKER}" (
                        id INTEGER PRIMARY KEY,
                        started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )'''
                )
                cursor.execute(
                    f'INSERT INTO "{preflight.BOOTSTRAP_MARKER}" (id) VALUES (1)'
                )

        monkeypatch.setenv("DATABASE_URL", database_url)
        assert preflight.run_alembic_upgrade() is True
        assert preflight.run_migration_health_check() is True

        with psycopg2.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT to_regclass(%s)", (preflight.BOOTSTRAP_MARKER,))
                assert cursor.fetchone()[0] is None
    finally:
        _drop_database(base_url, database)
