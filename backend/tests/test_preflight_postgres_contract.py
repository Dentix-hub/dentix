import os
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import pytest
from psycopg2 import sql

from backend.scripts import preflight_migrations as preflight


def _postgres_base_url() -> str:
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://")):
        pytest.skip("Production migration contract requires PostgreSQL")
    return url


def _url_for_database(url: str, database: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{database}", parts.query, parts.fragment))


def _create_database(base_url: str) -> tuple[str, str]:
    database = f"dentix_contract_{uuid.uuid4().hex[:10]}"
    admin_url = _url_for_database(base_url, "postgres")
    connection = psycopg2.connect(admin_url)
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    finally:
        connection.close()
    return database, _url_for_database(base_url, database)


def _drop_database(base_url: str, database: str) -> None:
    admin_url = _url_for_database(base_url, "postgres")
    connection = psycopg2.connect(admin_url)
    connection.autocommit = True
    try:
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
    finally:
        connection.close()


def test_preflight_bootstraps_fresh_database_then_upgrades_existing(monkeypatch):
    base_url = _postgres_base_url()
    database, database_url = _create_database(base_url)
    try:
        monkeypatch.setenv("DATABASE_URL", database_url)

        assert preflight.run_alembic_upgrade() is True
        assert preflight.run_migration_health_check() is True

        with psycopg2.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_trigger WHERE tgname = 'clinic_write_gate' AND NOT tgisinternal")
                gate_count = cursor.fetchone()[0]
                assert gate_count > 0, "Restore write-gate triggers must be installed on fresh bootstrap"

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


def test_preflight_repairs_missing_gates_with_noinherit_migration_login(monkeypatch):
    base_url = _postgres_base_url()
    database, database_url = _create_database(base_url)
    uid = uuid.uuid4().hex[:8]
    owner_role = f"dentix_test_owner_{uid}"
    migrator_role = f"dentix_test_migrator_{uid}"
    migrator_pass = "migrator_secret_123"

    try:
        # 1. Fresh bootstrap the database under admin so it is stamped at head
        monkeypatch.setenv("DATABASE_URL", database_url)
        assert preflight.run_alembic_upgrade() is True
        assert preflight.run_migration_health_check() is True

        admin_url = _url_for_database(base_url, database)
        with psycopg2.connect(admin_url) as conn:
            conn.autocommit = True
            with conn.cursor() as cursor:
                # 2. Create synthetic owner and NOINHERIT migration roles
                cursor.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(owner_role)))
                cursor.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s NOINHERIT").format(sql.Identifier(migrator_role)),
                    (migrator_pass,),
                )
                cursor.execute(sql.SQL("GRANT {} TO {}").format(sql.Identifier(owner_role), sql.Identifier(migrator_role)))
                cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(migrator_role)))
                cursor.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(sql.Identifier(owner_role)))
                cursor.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(sql.Identifier(migrator_role)))

                # 3. Transfer all tables and dentix_% functions to owner_role
                # NOTE: We compose the DO block using psycopg2.sql so that
                # the owner_role literal is injected safely *before* the
                # statement reaches PostgreSQL.  Using cursor.execute()
                # parameters would conflict with PL/pgSQL's own format()
                # %-placeholders (%I, %L) and cause an IndexError.
                do_transfer = sql.SQL(
                    """
                    DO $$
                    DECLARE r RECORD;
                    BEGIN
                        FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                            EXECUTE format('ALTER TABLE public.%%I OWNER TO %%I', r.tablename, {role});
                        END LOOP;
                        FOR r IN SELECT p.oid::regprocedure::text AS fn_sig FROM pg_proc p
                                 JOIN pg_namespace n ON n.oid = p.pronamespace
                                 WHERE n.nspname = 'public' AND p.proname LIKE 'dentix_%%' LOOP
                            EXECUTE format('ALTER FUNCTION %%s OWNER TO %%I', r.fn_sig, {role});
                        END LOOP;
                    END $$;
                    """
                ).format(role=sql.Literal(owner_role))
                cursor.execute(do_transfer)

                # 4. Remove triggers to simulate an already-stamped database needing repair
                cursor.execute(
                    """
                    DO $$
                    DECLARE r RECORD;
                    BEGIN
                        FOR r IN SELECT c.relname AS tbl FROM pg_trigger t
                                 JOIN pg_class c ON c.oid = t.tgrelid
                                 JOIN pg_namespace n ON n.oid = c.relnamespace
                                 WHERE n.nspname = 'public' AND t.tgname = 'clinic_write_gate' AND NOT t.tgisinternal LOOP
                            EXECUTE format('DROP TRIGGER clinic_write_gate ON public.%I', r.tbl);
                        END LOOP;
                    END $$;
                    """
                )

                # Confirm triggers were removed
                cursor.execute("SELECT count(*) FROM pg_trigger WHERE tgname = 'clinic_write_gate' AND NOT tgisinternal")
                assert cursor.fetchone()[0] == 0

        # 5. Build migration URL using NOINHERIT login
        parts = urlsplit(database_url)
        netloc = f"{migrator_role}:{migrator_pass}@{parts.hostname}:{parts.port or 5432}"
        migrator_url = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))

        monkeypatch.setenv("DATABASE_URL", migrator_url)
        monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
        monkeypatch.delenv("OWNER_DATABASE_URL", raising=False)
        monkeypatch.delenv("DENTIX_MIGRATION_SET_ROLE", raising=False)

        # 6. Run preflight upgrade; it must detect NOINHERIT owner role, apply SET LOCAL ROLE in repair,
        # and succeed without InsufficientPrivilege error.
        assert preflight.run_alembic_upgrade() is True
        assert preflight.run_migration_health_check() is True

        with psycopg2.connect(admin_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_trigger WHERE tgname = 'clinic_write_gate' AND NOT tgisinternal")
                assert cursor.fetchone()[0] > 0
    finally:
        _drop_database(base_url, database)
        admin_postgres_url = _url_for_database(base_url, "postgres")
        try:
            with psycopg2.connect(admin_postgres_url) as conn:
                conn.autocommit = True
                with conn.cursor() as cursor:
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(migrator_role)))
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(owner_role)))
        except Exception:
            pass
