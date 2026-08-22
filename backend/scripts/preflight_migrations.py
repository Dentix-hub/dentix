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
# `notifications` is intentionally NOT in this generic tuple. It is still a
# FORCE-RLS table, but its visibility contract differs: rows may be private to
# the current tenant OR deliberately global (`is_global = true` / tenant NULL).
# `_install_postgresql_rls()` installs that custom policy immediately after the
# generic loop and the health verifier includes it explicitly. Keeping it out
# of `RLS_TABLES` prevents the generic tenant-only policy from shadowing/breaking
# valid cross-tenant global announcements.
RLS_TABLES = (
    "users",
    "patients",
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
    "insurance_providers",
    "price_lists",
    "warehouses",
    "materials",
    "batches",
    "stock_items",
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
    bypass_expr = (
        "CAST(NULLIF(current_setting('rls.bypass_rls', true), '') AS BOOLEAN) = true"
    )

    for table in RLS_TABLES:
        connection.execute(text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
        connection.execute(text(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY'))
        connection.execute(text(f'DROP POLICY IF EXISTS "{table}_tenant_policy" ON "{table}"'))
        connection.execute(
            text(
                f'''CREATE POLICY "{table}_tenant_policy" ON "{table}"
                    FOR ALL
                    USING (({tenant_expr}) OR {bypass_expr})
                    WITH CHECK (({tenant_expr}) OR {bypass_expr})'''
            )
        )

    # Notifications deliberately use a broader visibility policy than the
    # generic tenant-owned tables: tenant-private rows plus platform-global
    # announcements are valid. The table is still ENABLE + FORCE RLS.
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
                USING (({notif_expr}) OR {bypass_expr})
                WITH CHECK (({notif_expr}) OR {bypass_expr})'''
        )
    )


def _verify_postgresql_rls(engine, tables: Iterable[str] = RLS_TABLES) -> None:
    if engine.dialect.name != "postgresql":
        return

    required_tables = tuple(tables) + ("notifications",)
    with engine.begin() as connection:
        table_rows = connection.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = current_schema()
                  AND c.relname = ANY(:tables)
                """
            ),
            {"tables": list(required_tables)},
        ).mappings().all()
        state = {row["relname"]: row for row in table_rows}

        missing_tables = sorted(set(required_tables) - set(state))
        if missing_tables:
            raise RuntimeError(
                "RLS verification missing tables: " + ", ".join(missing_tables)
            )

        insecure = sorted(
            name
            for name, row in state.items()
            if not row["relrowsecurity"] or not row["relforcerowsecurity"]
        )
        if insecure:
            raise RuntimeError(
                "RLS is not ENABLE + FORCE for tables: " + ", ".join(insecure)
            )

        policy_rows = connection.execute(
            text(
                """
                SELECT tablename, policyname
                FROM pg_policies
                WHERE schemaname = current_schema()
                  AND tablename = ANY(:tables)
                """
            ),
            {"tables": list(required_tables)},
        ).mappings().all()
        policies = {(row["tablename"], row["policyname"]) for row in policy_rows}

        missing_policies = []
        for table in tables:
            expected = f"{table}_tenant_policy"
            if (table, expected) not in policies:
                missing_policies.append(f"{table}.{expected}")
        if ("notifications", "notifications_tenant_policy") not in policies:
            missing_policies.append("notifications.notifications_tenant_policy")
        if missing_policies:
            raise RuntimeError(
                "RLS verification missing policies: " + ", ".join(missing_policies)
            )


def _bootstrap_current_schema(engine, cfg) -> None:
    """Create/stamp the current model baseline for a truly empty database."""
    from alembic import command
    from backend.database import Base
    import backend.models  # noqa: F401 - populate Base.metadata

    logger.info("[PREFLIGHT] Starting/resuming fresh current-schema bootstrap")
    _ensure_bootstrap_marker(engine)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        _install_postgresql_rls(connection)
    _verify_postgresql_rls(engine)
    command.stamp(cfg, "head")
    _drop_bootstrap_marker(engine)
    logger.info("[PREFLIGHT] Fresh current-schema bootstrap completed")


def run_preflight_migrations() -> bool:
    db_url = _database_url()
    if not db_url:
        logger.error("[PREFLIGHT] DATABASE_URL is required")
        return False

    engine = None
    try:
        from alembic import command

        cfg = _alembic_config()
        engine = create_engine(db_url)
        tables = _table_names(engine)
        user_tables = _user_tables(engine)
        has_version = "alembic_version" in tables
        has_marker = BOOTSTRAP_MARKER in tables

        if has_marker:
            logger.warning("[PREFLIGHT] Resuming interrupted fresh bootstrap")
            _bootstrap_current_schema(engine, cfg)
        elif not user_tables and not has_version:
            logger.info("[PREFLIGHT] Empty database detected; bootstrapping current schema")
            _bootstrap_current_schema(engine, cfg)
        else:
            if not has_version:
                raise RuntimeError(
                    "Existing application tables found without alembic_version; "
                    "refusing to guess migration history"
                )
            logger.info("[PREFLIGHT] Existing versioned schema detected; running Alembic")
            command.upgrade(cfg, "head")
            # Existing databases may predate current post-migration RLS additions.
            # Re-assert the canonical idempotent RLS contract after Alembic.
            with engine.begin() as connection:
                _install_postgresql_rls(connection)
            _verify_postgresql_rls(engine)

        # Final basic connectivity/version-table check.
        tables = _table_names(engine)
        if "alembic_version" not in tables:
            raise RuntimeError("alembic_version missing after preflight")
        logger.info("[PREFLIGHT] Migration/bootstrap health check passed")
        return True
    except Exception:
        logger.exception("[PREFLIGHT] Migration/bootstrap failed")
        return False
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    sys.exit(0 if run_preflight_migrations() else 1)
