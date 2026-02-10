"""
Startup patches and schema fixes for Smart Clinic.

This module contains all the inline schema patches that were previously
in main.py lifespan. They are extracted here for cleanliness.
All patches are idempotent and safe to run on every startup.
"""

from backend import database
import logging

logger = logging.getLogger(__name__)


def run_startup_patches():
    """Run all startup schema patches. Idempotent and safe."""
    _patch_subscription_plans_schema()
    _patch_patients_missing_columns()


def _patch_subscription_plans_schema():
    """Add 'is_default' column to subscription_plans if missing."""
    from sqlalchemy import text

    db = database.SessionLocal()
    try:
        logger.info("[STARTUP] Checking Subscription Plans Schema...")
        try:
            db.execute(
                text(
                    "ALTER TABLE subscription_plans ADD COLUMN is_default BOOLEAN DEFAULT FALSE;"
                )
            )
            logger.info(
                "[STARTUP] SUCCESS: Added 'is_default' column to subscription_plans"
            )
            db.commit()
        except Exception as e:
            db.rollback()
            err_str = str(e).lower()
            if "duplicate" in err_str or "exists" in err_str:
                logger.info("[STARTUP] Schema check passed (Column likely exists).")
            else:
                logger.info(f"[STARTUP] Schema patch note: {e}")
    finally:
        db.close()


def _patch_patients_missing_columns():
    """Add missing 'email' and 'address' columns to patients table."""
    from sqlalchemy import text

    db = database.SessionLocal()
    try:
        logger.info("[STARTUP] Checking for missing columns in 'patients'...")
        for column_name, column_type in [("email", "VARCHAR"), ("address", "VARCHAR")]:
            try:
                db.execute(
                    text(
                        f"ALTER TABLE patients ADD COLUMN {column_name} {column_type};"
                    )
                )
                logger.info(
                    f"[STARTUP] Added missing column '{column_name}' to 'patients'"
                )
                db.commit()
            except Exception as e:
                db.rollback()
                err_str = str(e).lower()
                if "duplicate" in err_str or "exists" in err_str:
                    pass  # Column already exists
                else:
                    logger.warning(f"[STARTUP] Failed to add '{column_name}': {e}")
    finally:
        db.close()
