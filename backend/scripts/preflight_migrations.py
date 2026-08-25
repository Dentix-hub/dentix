#!/usr/bin/env python3
"""
Preflight Migrations Script — Run BEFORE starting the application.

This script is the ONLY way database migrations should be applied in
production.

Legacy note
-----------
The historical Alembic chain starts after Dentix already had a core schema;
its first revision is intentionally a no-op and later revisions assume tables
such as ``tenants`` and ``users`` already exist. Rewriting those applied
historical revisions would be unsafe for existing deployments.

Therefore preflight has two explicit paths:

* Existing versioned schema: run ``alembic upgrade head`` normally.
* Truly empty schema: create the *current* SQLAlchemy model baseline, install
  the PostgreSQL RLS invariants that ``metadata.create_all`` cannot guarantee,
  then stamp Alembic at head. No historical/data migration is skipped for an
  existing versioned database.

Fresh bootstrap is resumable. A private marker table is committed before any
model DDL. If model/RLS/stamp work is interrupted, the next preflight run sees
that marker and resumes the fresh-baseline path instead of mistaking a partial
bootstrap for a legacy production schema.

Usage:
    python -m backend.scripts.preflight_migrations

Exit codes:
    0 — Migrations/bootstrap applied successfully
    1 — Migration/bootstrap/health check failed (deployment should abort)
"""

import logging
import os
import sys
from typing import Iterable

from sqlalchemy import create_engine, inspect, text

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("preflight_migrations")

# Internal marker used only while creating a brand-new current-schema baseline.
# It is intentionally not part of SQLAlchemy metadata or Alembic history.
BOOTSTRAP_MARKER = "_dentix_fresh_bootstrap"

# Canonical current PostgreSQL tenant-isolation contract. It extends the
# historical bf6c75e1c3d3 migration when later/current tenant-owned models need
# the same ENABLE + FORCE + tenant-policy invariants. Fresh databases cannot
# replay the historical chain from base, so this tuple is authoritative for
# the explicit post-create_all RLS installation and health verification.
#
# `notifications` is intentionally outside this generic tuple. It is still a
# FORCE-RLS table, but its valid visibility contract includes current-tenant
# rows plus deliberately global rows (`is_global = true` or tenant_id NULL).
# `_install_postgresql_rls()` installs that custom policy immediately after the
# generic loop, and `run_migration_health_check()` verifies it explicitly.
RLS_TABLES = (
    "users",
    "patients",
    "tooth_status",
    "prescriptions",
    "attachments",
    "saved_medications",
    "appointments",
    "treatments",
    "treatment_sessions",
    "laboratories",
    "lab_orders",
    "procedures",
    "payments",
    "expenses",
    "salary_payments",
    "lab_payments",
    "subscription_payments",
    "subscription_checkouts",
    "subscription_renewal_requests",
    "insurance_providers",
    "price_lists",
    "warehouses",
    "materials",
    "batches",
    "stock_items",
    "material_sessions",
    "stock_movements",
    "procedure_material_weights",
    "material_learning_logs",
    "treatment_material_usages",
    "audit_logs",
    "support_messages",
    "tenant_features",
    "background_jobs",
    "system_errors",
    "ai_logs",
    "security_events",
    "domain_events",
    "push_subscriptions",
)

CHILD_TENANT_RELATIONSHIPS = (
    ("tooth_status", "patient_id", "patients", False),
    ("prescriptions", "patient_id", "patients", False),
    ("attachments", "patient_id", "patients", False),
    ("material_sessions", "stock_item_id", "stock_items", False),
    ("stock_movements", "stock_item_id", "stock_items", False),
    ("material_sessions", "patient_id", "patients", True),
)


def _database_url() -> str | None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    db_url = db_url.strip().strip("'").strip('"')
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    # Preflight is synchronous. Normalize an async SQLAlchemy URL if an
    # operator supplied one explicitly.
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return db_url


def _alembic_config():
    from alembic.config import Config

    ini_candidates = [
        os.path.join(PROJECT_ROOT, "backend", "alembic.ini"),
        os.path.join(PROJECT_ROOT, "alembic.ini"),
        os.path.join(os.getcwd(), "alembic.ini"),
    ]
    ini_path = next((path for path in ini_candidates if os.path.exists(path)), None)
    if not ini_path:
        raise RuntimeError(f"alembic.ini not found; searched: {ini_candidates}")

    logger.info("[PREFLIGHT] Using alembic.ini: %s", ini_path)
    cfg = Config(ini_path)
    db_url = _database_url()
    if db_url:
        cfg.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))
    return cfg


def _table_names(engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _user_tables(engine) -> set[str]:
    """Return application tables, excluding migration/bootstrap bookkeeping."""
    return _table_names(engine) - {"alembic_version", BOOTSTRAP_MARKER}


def _ensure_bootstrap_marker(engine) -> None:
    """Persist a resumable marker before any fresh-schema model DDL."""
    with engine.begin() as connection:
        connection.execute(
            text(
                f'''CREATE TABLE IF NOT EXISTS "{BOOTSTRAP_MARKER}" (
                    id INTEGER PRIMARY KEY,
                    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )'''
            )
        )
        if connection.dialect.name == "postgresql":
            connection.execute(
                text(
                    f'''INSERT INTO "{BOOTSTRAP_MARKER}" (id)
                        VALUES (1)
                        ON CONFLICT (id) DO NOTHING'''
                )
            )
        else:
            connection.execute(
                text(
                    f'''INSERT OR IGNORE INTO "{BOOTSTRAP_MARKER}" (id)
                        VALUES (1)'''
                )
            )


def _drop_bootstrap_marker(engine) -> None:
    with engine.begin() as connection:
        connection.execute(text(f'DROP TABLE IF EXISTS "{BOOTSTRAP_MARKER}"'))


def _install_postgresql_rls(connection) -> None:
    """Install the same strict RLS contract used by the historical migration."""
    if connection.dialect.name != "postgresql":
        return

    existing_tables = set(inspect(connection).get_table_names())
    missing = sorted(set(RLS_TABLES + ("notifications",)) - existing_tables)
    if missing:
        raise RuntimeError(
            "Fresh schema is missing tables required for RLS: " + ", ".join(missing)
        )

    tenant_expr = (
        "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
    )
    for table in RLS_TABLES:
        connection.execute(text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
        connection.execute(text(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY'))
        connection.execute(text(f'DROP POLICY IF EXISTS "{table}_tenant_policy" ON "{table}"'))
        connection.execute(
            text(
                f'''CREATE POLICY "{table}_tenant_policy" ON "{table}"
                    FOR ALL
                    USING ({tenant_expr})
                    WITH CHECK ({tenant_expr})'''
            )
        )

    # Notifications are FORCE-RLS too, but their intentional global-announcement
    # behavior requires this broader policy instead of the generic tenant-only one.
    notif_expr = (
        "(tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer) "
        "OR (is_global = true) OR (tenant_id IS NULL)"
    )
    connection.execute(text('ALTER TABLE "notifications" ENABLE ROW LEVEL SECURITY'))
    connection.execute(text('ALTER TABLE "notifications" FORCE ROW LEVEL SECURITY'))
    connection.execute(
        text('DROP POLICY IF EXISTS "notifications_tenant_policy" ON "notifications"')
    )
    connection.execute(
        text(
            f'''CREATE POLICY "notifications_tenant_policy" ON "notifications"
                FOR ALL
                USING ({notif_expr})
                WITH CHECK ({notif_expr})'''
        )
    )

    connection.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION dentix_assert_parent_tenant()
            RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE
                child_parent_id integer;
                parent_tenant_id integer;
                allow_null boolean := COALESCE(TG_ARGV[2], 'false')::boolean;
            BEGIN
                child_parent_id := NULLIF(to_jsonb(NEW) ->> TG_ARGV[1], '')::integer;
                IF child_parent_id IS NULL AND allow_null THEN RETURN NEW; END IF;
                IF child_parent_id IS NULL THEN
                    RAISE EXCEPTION 'Missing required parent on %', TG_TABLE_NAME;
                END IF;
                EXECUTE format('SELECT tenant_id FROM %I WHERE id = $1', TG_ARGV[0])
                   INTO parent_tenant_id USING child_parent_id;
                IF parent_tenant_id IS NULL OR NEW.tenant_id IS DISTINCT FROM parent_tenant_id THEN
                    RAISE EXCEPTION 'Tenant mismatch on %', TG_TABLE_NAME;
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
    )
    for table, child_key, parent, allow_null in CHILD_TENANT_RELATIONSHIPS:
        suffix = "patient_tenant" if table == "material_sessions" and child_key == "patient_id" else "parent_tenant"
        trigger = f"trg_{table}_{suffix}"
        connection.execute(text(f'DROP TRIGGER IF EXISTS "{trigger}" ON "{table}"'))
        connection.execute(
            text(
                f'''CREATE TRIGGER "{trigger}"
                    BEFORE INSERT OR UPDATE OF tenant_id, "{child_key}" ON "{table}"
                    FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                        '{parent}', '{child_key}', '{str(allow_null).lower()}'
                    )'''
            )
        )


def _bootstrap_fresh_database(engine, alembic_cfg) -> None:
    """Create/resume the current canonical schema for a brand-new database."""
    from alembic import command
    from backend import models

    logger.warning(
        "[PREFLIGHT] Fresh/resumable bootstrap detected. Building current model baseline."
    )
    _ensure_bootstrap_marker(engine)

    # register_rls(Base) installs SQLAlchemy DDL hooks. Some of those hooks may
    # commit/close the transaction used by create_all, so never assume a single
    # engine.begin() can safely contain both create_all and our explicit RLS
    # verification/replacement phase. create_all itself is idempotent.
    models.Base.metadata.create_all(bind=engine)

    # Use a completely fresh transaction for explicit RLS installation. This
    # phase is also idempotent because policies are dropped/recreated safely.
    with engine.begin() as connection:
        _install_postgresql_rls(connection)

    # The model baseline is current by definition. Historical revisions are
    # legacy deltas for pre-existing schemas and cannot safely be replayed from
    # an empty DB. Stamp only after schema + RLS invariants both succeeded.
    command.stamp(alembic_cfg, "head")

    # Drop the marker last. If stamp or any prior phase fails, the next preflight
    # invocation resumes this path instead of attempting legacy migrations.
    _drop_bootstrap_marker(engine)
    logger.info("[PREFLIGHT] Fresh database baseline created and stamped at head.")


def _verify_alembic_heads(engine, alembic_cfg) -> bool:
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    expected = set(ScriptDirectory.from_config(alembic_cfg).get_heads())
    with engine.connect() as connection:
        current = set(MigrationContext.configure(connection).get_current_heads())
    if current != expected:
        logger.error(
            "[PREFLIGHT] Alembic revision mismatch. current=%s expected=%s",
            sorted(current),
            sorted(expected),
        )
        return False
    logger.info("[PREFLIGHT] Alembic heads verified: %s", sorted(current))
    return True


def run_alembic_upgrade():
    """Bootstrap an empty DB or upgrade an existing versioned DB to head."""
    from alembic import command

    db_url = _database_url()
    if not db_url:
        logger.error("[PREFLIGHT] DATABASE_URL is not set.")
        return False

    try:
        alembic_cfg = _alembic_config()
        engine = create_engine(db_url)
    except Exception as exc:
        logger.error("[PREFLIGHT] Failed to initialize migration engine: %s", exc)
        return False

    try:
        all_tables = _table_names(engine)
        tables = all_tables - {"alembic_version", BOOTSTRAP_MARKER}
        bootstrap_in_progress = BOOTSTRAP_MARKER in all_tables

        if bootstrap_in_progress:
            logger.warning(
                "[PREFLIGHT] Incomplete fresh bootstrap marker found; resuming safely."
            )
            _bootstrap_fresh_database(engine, alembic_cfg)
        elif not tables:
            _bootstrap_fresh_database(engine, alembic_cfg)
        else:
            # Never disguise a partial/corrupt or unknown unversioned database
            # as a fresh one. Existing Dentix schemas must have both the core
            # tenant table and Alembic bookkeeping before historical deltas run.
            if "tenants" not in tables:
                logger.error(
                    "[PREFLIGHT] Non-empty database has no tenants table; refusing "
                    "automatic bootstrap. Existing tables: %s",
                    sorted(tables),
                )
                return False
            if "alembic_version" not in all_tables:
                logger.error(
                    "[PREFLIGHT] Existing Dentix schema is not Alembic-versioned and "
                    "has no fresh-bootstrap marker. Refusing to guess its migration "
                    "state; manual migration review is required."
                )
                return False

            logger.info("[PREFLIGHT] Existing versioned schema detected; running alembic upgrade head ...")
            command.upgrade(alembic_cfg, "head")
            logger.info("[PREFLIGHT] Alembic upgrade completed successfully.")

        return _verify_alembic_heads(engine, alembic_cfg)
    except BaseException as exc:
        logger.error(
            "[PREFLIGHT] Migration/bootstrap FAILED with base exception: %s",
            exc,
            exc_info=True,
        )
        return False
    finally:
        engine.dispose()


def _verify_postgresql_rls(engine, tables: Iterable[str]) -> list[str]:
    """Return RLS invariant failures for the requested PostgreSQL tables."""
    if engine.name != "postgresql":
        return []

    failures: list[str] = []
    with engine.connect() as connection:
        for table in tables:
            row = connection.execute(
                text(
                    """
                    SELECT c.relrowsecurity, c.relforcerowsecurity,
                           EXISTS (
                               SELECT 1 FROM pg_policies p
                               WHERE p.schemaname = current_schema()
                                 AND p.tablename = :table
                           ) AS has_policy,
                           NOT EXISTS (
                               SELECT 1 FROM pg_policies p
                               WHERE p.schemaname = current_schema()
                                 AND p.tablename = :table
                                 AND (
                                     COALESCE(p.qual, '') LIKE '%rls.bypass_rls%'
                                     OR COALESCE(p.with_check, '') LIKE '%rls.bypass_rls%'
                                 )
                           ) AS no_application_bypass
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = current_schema()
                      AND c.relname = :table
                    """
                ),
                {"table": table},
            ).first()
            if not row:
                failures.append(f"{table}:missing")
            elif not (bool(row[0]) and bool(row[1]) and bool(row[2]) and bool(row[3])):
                failures.append(
                    f"{table}:enabled={bool(row[0])},forced={bool(row[1])},"
                    f"policy={bool(row[2])},no_application_bypass={bool(row[3])}"
                )
    return failures


def _verify_postgresql_child_tenant_triggers(engine) -> list[str]:
    if engine.name != "postgresql":
        return []
    expected = {
        f"trg_{table}_{'patient_tenant' if table == 'material_sessions' and key == 'patient_id' else 'parent_tenant'}"
        for table, key, _, _ in CHILD_TENANT_RELATIONSHIPS
    }
    with engine.connect() as connection:
        present = set(
            connection.execute(
                text(
                    """SELECT tgname FROM pg_trigger
                       WHERE NOT tgisinternal AND tgname = ANY(:names)"""
                ),
                {"names": list(expected)},
            ).scalars()
        )
    return sorted(expected - present)


def run_migration_health_check():
    """Verify critical schema and PostgreSQL tenant-isolation invariants."""
    logger.info("[PREFLIGHT] Running migration health check ...")

    db_url = _database_url()
    if not db_url:
        logger.error("[PREFLIGHT] DATABASE_URL is not set.")
        return False

    try:
        engine = create_engine(db_url)
    except Exception as exc:
        logger.error("[PREFLIGHT] Failed to create sync engine: %s", exc)
        return False

    checks = [
        ("users", "tenant_id"),
        ("patients", "tenant_id"),
        ("appointments", "tenant_id"),
        ("treatments", "tenant_id"),
        ("payments", "tenant_id"),
        ("lab_orders", "tenant_id"),
        ("salary_payments", "tenant_id"),
        ("subscription_payments", "tenant_id"),
        ("tooth_status", "tenant_id"),
        ("prescriptions", "tenant_id"),
        ("attachments", "tenant_id"),
        ("material_sessions", "tenant_id"),
        ("stock_movements", "tenant_id"),
        ("subscription_renewal_requests", "tenant_id"),
    ]

    missing: list[str] = []
    try:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        if BOOTSTRAP_MARKER in table_names:
            logger.error(
                "[PREFLIGHT] CRITICAL: fresh-bootstrap marker still present after migration."
            )
            return False

        for table, column in checks:
            if table not in table_names:
                missing.append(f"{table}.{column}")
                continue
            columns = {item["name"] for item in inspector.get_columns(table)}
            if column not in columns:
                missing.append(f"{table}.{column}")

        if missing:
            logger.error("[PREFLIGHT] CRITICAL: Missing schema components: %s", missing)
            return False

        required_nonnull = {
            "tooth_status",
            "prescriptions",
            "attachments",
            "material_sessions",
            "stock_movements",
            "subscription_renewal_requests",
        }
        nullable = [
            table
            for table in required_nonnull
            if next(
                column
                for column in inspector.get_columns(table)
                if column["name"] == "tenant_id"
            ).get("nullable", True)
        ]
        if nullable:
            logger.error("[PREFLIGHT] CRITICAL: nullable tenant ownership: %s", nullable)
            return False

        rls_failures = _verify_postgresql_rls(
            engine, tuple(RLS_TABLES) + ("notifications",)
        )
        if rls_failures:
            logger.error("[PREFLIGHT] CRITICAL: RLS invariant failures: %s", rls_failures)
            return False

        trigger_failures = _verify_postgresql_child_tenant_triggers(engine)
        if trigger_failures:
            logger.error(
                "[PREFLIGHT] CRITICAL: child tenant triggers missing: %s",
                trigger_failures,
            )
            return False

        logger.info("[PREFLIGHT] All critical schema and RLS checks passed.")
        return True
    finally:
        engine.dispose()


def main():
    logger.info("=" * 60)
    logger.info("[PREFLIGHT] Starting Dentix Migration Preflight Check")
    logger.info("=" * 60)

    if not run_alembic_upgrade():
        logger.critical("[PREFLIGHT] MIGRATION FAILED — ABORTING DEPLOYMENT")
        sys.exit(1)

    if not run_migration_health_check():
        logger.critical("[PREFLIGHT] HEALTH CHECK FAILED — ABORTING DEPLOYMENT")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("[PREFLIGHT] ALL CHECKS PASSED — Safe to start application")
    logger.info("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    import traceback

    try:
        main()
    except SystemExit as exc:
        if exc.code == 0 or exc.code is None:
            sys.exit(0)
        print(
            f"CRITICAL: Captured non-zero SystemExit ({exc.code}) at top level in preflight!",
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
        sys.exit(exc.code)
    except BaseException:
        print("CRITICAL: Captured BaseException at top level in preflight!", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(2)
