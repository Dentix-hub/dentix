"""
Migration: Add Doctor Visibility Fields

This migration adds the necessary columns for multi-doctor patient visibility:
- User: patient_visibility_mode, can_view_other_doctors_history
- Patient: assigned_doctor_id
- Appointment: doctor_id

Run with: python backend/migrations/add_doctor_visibility.py
"""

from sqlalchemy import text
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


MIGRATIONS = [
    # User table - visibility settings
    {
        "table": "users",
        "column": "patient_visibility_mode",
        "sql": "ALTER TABLE users ADD COLUMN IF NOT EXISTS patient_visibility_mode VARCHAR(50) DEFAULT 'all_assigned'",
    },
    {
        "table": "users",
        "column": "can_view_other_doctors_history",
        "sql": "ALTER TABLE users ADD COLUMN IF NOT EXISTS can_view_other_doctors_history BOOLEAN DEFAULT FALSE",
    },
    # Patient table - doctor assignment
    {
        "table": "patients",
        "column": "assigned_doctor_id",
        "sql": "ALTER TABLE patients ADD COLUMN IF NOT EXISTS assigned_doctor_id INTEGER REFERENCES users(id)",
    },
    # Appointment table - doctor reference
    {
        "table": "appointments",
        "column": "doctor_id",
        "sql": "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS doctor_id INTEGER REFERENCES users(id)",
    },
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_patient_assigned_doctor ON patients(assigned_doctor_id)",
    "CREATE INDEX IF NOT EXISTS idx_appointment_doctor ON appointments(doctor_id)",
    "CREATE INDEX IF NOT EXISTS idx_user_visibility_mode ON users(patient_visibility_mode)",
]


def check_column_exists(conn, table: str, column: str) -> bool:
    """Check if column already exists in table."""
    try:
        result = conn.execute(
            text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table AND column_name = :column
        """),
            {"table": table, "column": column},
        )
        return result.fetchone() is not None
    except Exception:
        return False


def run_migration():
    """Run all migrations."""
    logger.info("Starting Doctor Visibility Migration...")

    with engine.connect() as conn:
        # Run column migrations
        for migration in MIGRATIONS:
            try:
                if check_column_exists(conn, migration["table"], migration["column"]):
                    logger.info(
                        f"Column {migration['column']} already exists in {migration['table']}"
                    )
                    continue

                conn.execute(text(migration["sql"]))
                conn.commit()
                logger.info(f"Added column: {migration['table']}.{migration['column']}")

            except Exception as e:
                logger.warning(f"Could not add {migration['column']}: {e}")

        # Run index creation
        for index_sql in INDEXES:
            try:
                conn.execute(text(index_sql))
                conn.commit()
                logger.info(f"Created index: {index_sql.split(' ')[5]}")
            except Exception as e:
                logger.warning(f"Could not create index: {e}")

    logger.info("Migration complete!")


def rollback():
    """Rollback migration (for development only)."""
    logger.warning("Rolling back Doctor Visibility Migration...")

    rollback_sql = [
        "ALTER TABLE users DROP COLUMN IF EXISTS patient_visibility_mode",
        "ALTER TABLE users DROP COLUMN IF EXISTS can_view_other_doctors_history",
        "ALTER TABLE patients DROP COLUMN IF EXISTS assigned_doctor_id",
        "ALTER TABLE appointments DROP COLUMN IF EXISTS doctor_id",
    ]

    with engine.connect() as conn:
        for sql in rollback_sql:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.info(f"Executed: {sql}")
            except Exception as e:
                logger.warning(f"Rollback failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback()
    else:
        run_migration()
