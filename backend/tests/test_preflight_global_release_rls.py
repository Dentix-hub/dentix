"""Reproduce a table-owning runtime login blocked by forced RLS at release."""

from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg2
from psycopg2 import sql
import pytest

from backend.scripts import preflight_migrations as preflight
from backend.tests.test_preflight_postgres_contract import (
    _create_database,
    _drop_database,
    _postgres_base_url,
    _url_for_database,
)


@pytest.mark.parametrize("system_configuration", ["privileged", "missing", "wrong_database", "insufficient", "explicit_owner"])
def test_global_release_uses_separate_rls_login_without_escalating_app(monkeypatch, system_configuration):
    system_available = system_configuration == "privileged"
    base_url = _postgres_base_url()
    database, admin_url = _create_database(base_url)
    uid = uuid4().hex[:10]
    app_role, system_role = f"release_app_{uid}", f"release_system_{uid}"
    password = "synthetic-role-test-only"
    for key in ("MIGRATION_DATABASE_URL", "OWNER_DATABASE_URL", "SYSTEM_DATABASE_URL", "BACKUP_SOURCE_DATABASE_URL", "DENTIX_MIGRATION_SET_ROLE"):
        monkeypatch.delenv(key, raising=False)
    try:
        monkeypatch.setenv("DATABASE_URL", admin_url)
        assert preflight.run_alembic_upgrade() is True
        with psycopg2.connect(admin_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("CREATE ROLE {} LOGIN NOBYPASSRLS PASSWORD %s").format(sql.Identifier(app_role)), (password,))
                cur.execute(sql.SQL("CREATE ROLE {} LOGIN BYPASSRLS PASSWORD %s").format(sql.Identifier(system_role)), (password,))
                cur.execute("UPDATE alembic_version SET version_num = 'c2d3e4f5a6b7'")
                cur.execute("UPDATE feature_flags SET is_global_enabled = false, rollout_percentage = 0 WHERE key = 'clinical_vnext_native_writes'")
                cur.execute("INSERT INTO tenants (id, name, subscription_status, plan, is_active, created_at, total_revenue, backup_frequency, payment_failed_count, is_deleted) VALUES (101, 'Synthetic Alpha', 'trial', 'trial', true, NOW(), 0, 'off', 0, false), (102, 'Synthetic Beta', 'trial', 'trial', true, NOW(), 0, 'off', 0, false)")
                cur.execute("INSERT INTO tenant_features (tenant_id, feature_key, is_enabled) VALUES (101, 'clinical_vnext_native_writes', false), (102, 'clinical_vnext_native_writes', false)")
                cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                for (table,) in cur.fetchall():
                    cur.execute(sql.SQL("ALTER TABLE public.{} OWNER TO {}").format(sql.Identifier(table), sql.Identifier(app_role)))
                cur.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(sql.Identifier(app_role)))
                cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(system_role)))
                cur.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE ON feature_flags TO {}").format(sql.Identifier(system_role)))
                cur.execute(sql.SQL("GRANT SELECT, UPDATE ON tenant_features, alembic_version TO {}").format(sql.Identifier(system_role)))
                if system_configuration == "insufficient":
                    cur.execute(sql.SQL("REVOKE UPDATE ON tenant_features FROM {}").format(sql.Identifier(system_role)))
                cur.execute(sql.SQL("GRANT USAGE ON SEQUENCE feature_flags_id_seq TO {}").format(sql.Identifier(system_role)))

        parts = urlsplit(admin_url)
        def login_url(role):
            return urlunsplit((parts.scheme, f"{role}:{password}@{parts.hostname}:{parts.port or 5432}", parts.path, parts.query, parts.fragment))
        monkeypatch.setenv("DATABASE_URL", login_url(app_role))
        if system_configuration != "missing":
            monkeypatch.setenv("SYSTEM_DATABASE_URL", login_url(system_role))
        if system_configuration == "wrong_database":
            monkeypatch.setenv("SYSTEM_DATABASE_URL", _url_for_database(login_url(system_role), "postgres"))
        if system_configuration == "explicit_owner":
            monkeypatch.setenv("OWNER_DATABASE_URL", login_url(app_role))
        assert preflight.run_alembic_upgrade() is system_available

        with psycopg2.connect(admin_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version_num FROM alembic_version")
                assert cur.fetchone()[0] == ("3b4c5d6e7f8a" if system_available else "c2d3e4f5a6b7")
                cur.execute("SELECT is_global_enabled FROM feature_flags WHERE key = 'clinical_vnext_native_writes'")
                assert cur.fetchone()[0] is system_available
                cur.execute("SELECT is_enabled FROM tenant_features ORDER BY tenant_id")
                assert cur.fetchall() == [(system_available,), (system_available,)]
                cur.execute("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid = 'tenant_features'::regclass")
                assert cur.fetchone() == (True, True)
                cur.execute("SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname = %s", (app_role,))
                assert cur.fetchone() == (False, False)
                cur.execute("SELECT pg_has_role(%s, %s, 'MEMBER')", (app_role, system_role))
                assert cur.fetchone() == (False,)
                cur.execute("SELECT tableowner FROM pg_tables WHERE schemaname = 'public' AND tablename = 'tenant_features'")
                assert cur.fetchone()[0] == app_role
        with psycopg2.connect(login_url(app_role)) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM tenant_features")
                assert cur.fetchone()[0] == 0
                cur.execute("SET LOCAL rls.tenant_id = '101'")
                cur.execute("SELECT tenant_id FROM tenant_features")
                assert cur.fetchall() == [(101,)]
                cur.execute("UPDATE tenant_features SET is_enabled = false WHERE tenant_id = 102")
                assert cur.rowcount == 0
    finally:
        _drop_database(base_url, database)
        with psycopg2.connect(_url_for_database(base_url, "postgres")) as conn:
            with conn.cursor() as cur:
                for role in (system_role, app_role):
                    cur.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))
