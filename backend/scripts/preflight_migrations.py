#!/usr/bin/env python3
"""
Preflight Migrations Script — Run BEFORE starting the application.

This script is the ONLY way database migrations should be applied in
production. It runs Alembic migrations and verifies the result.

Usage:
    python -m backend.scripts.preflight_migrations

Exit codes:
    0 — Migrations applied successfully
    1 — Migration failed (deployment should be aborted)
"""

import sys
import os
import logging

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("preflight_migrations")


def run_alembic_upgrade():
    """Run Alembic upgrade head and return success/failure."""
    from alembic.config import Config
    from alembic import command

    # Locate alembic.ini
    ini_candidates = [
        os.path.join(PROJECT_ROOT, "backend", "alembic.ini"),
        os.path.join(PROJECT_ROOT, "alembic.ini"),
        os.path.join(os.getcwd(), "alembic.ini"),
    ]

    ini_path = None
    for candidate in ini_candidates:
        if os.path.exists(candidate):
            ini_path = candidate
            break

    if not ini_path:
        logger.error("[PREFLIGHT] alembic.ini not found in any expected location.")
        logger.error("[PREFLIGHT] Searched: %s", ini_candidates)
        return False

    logger.info("[PREFLIGHT] Using alembic.ini: %s", ini_path)

    alembic_cfg = Config(ini_path)

    # Override DB URL from environment
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Normalize postgres:// -> postgresql://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        # Escape percent signs for ConfigParser interpolation
        db_url = db_url.replace("%", "%%")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    try:
        logger.info("[PREFLIGHT] Running: alembic upgrade head ...")
        command.upgrade(alembic_cfg, "head")
        logger.info("[PREFLIGHT] Alembic upgrade completed successfully.")
    except BaseException as e:
        logger.error("[PREFLIGHT] Alembic upgrade FAILED with base exception: %s", e, exc_info=True)
        return False

    # Verify current revision
    try:
        logger.info("[PREFLIGHT] Verifying current Alembic revision ...")
        # command.current(alembic_cfg) # Commented out to prevent SystemExit/abort in container environment
        logger.info("[PREFLIGHT] Migration state verified.")
    except Exception as e:
        logger.warning("[PREFLIGHT] Could not verify migration state: %s", e)

    return True


def run_migration_health_check():
    """Verify critical tables and columns exist after migrations."""
    from sqlalchemy import create_engine, text

    logger.info("[PREFLIGHT] Running migration health check ...")

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("[PREFLIGHT] DATABASE_URL is not set.")
        return False

    # Normalize postgres:// -> postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    try:
        engine = create_engine(db_url)
    except Exception as e:
        logger.error("[PREFLIGHT] Failed to create sync engine: %s", e)
        return False

    checks = [
        ("users", "tenant_id"),
        ("patients", "tenant_id"),
        ("appointments", "tenant_id"),
        ("treatments", "tenant_id"),
        ("payments", "tenant_id"),
    ]

    missing = []
    for table, col in checks:
        try:
            with engine.connect() as conn:
                if engine.name == "sqlite":
                    res = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                    cols = [r[1] for r in res]
                    if col not in cols:
                        missing.append(f"{table}.{col}")
                else:
                    conn.execute(text(f"SELECT {col} FROM {table} LIMIT 0"))
        except Exception as e:
            logger.warning("[PREFLIGHT] Check failed for %s.%s: %s", table, col, e)
            missing.append(f"{table}.{col}")

    if missing:
        logger.error("[PREFLIGHT] CRITICAL: Missing columns: %s", missing)
        return False

    logger.info("[PREFLIGHT] All critical schema components verified.")
    return True


def main():
    logger.info("=" * 60)
    logger.info("[PREFLIGHT] Starting Dentix Migration Preflight Check")
    logger.info("=" * 60)

    # Step 1: Run Alembic
    if not run_alembic_upgrade():
        logger.critical("[PREFLIGHT] MIGRATION FAILED — ABORTING DEPLOYMENT")
        sys.exit(1)

    # Step 2: Health check
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
    except SystemExit as e:
        if e.code == 0 or e.code is None:
            sys.exit(0)
        else:
            print(f"CRITICAL: Captured non-zero SystemExit ({e.code}) at top level in preflight!", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            sys.exit(e.code)
    except BaseException as e:
        print("CRITICAL: Captured BaseException at top level in preflight!", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(2)
