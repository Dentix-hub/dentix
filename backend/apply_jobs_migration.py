import sys
import os
from sqlalchemy import create_engine, text

sys.path.append(os.getcwd())
from backend.database import SQLALCHEMY_DATABASE_URL


def migrate_jobs_phase5():
    print(">>> Applying Phase 5 Migration (Background Jobs)...")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        try:
            print("Creating 'background_jobs' table...")
            conn.execute(
                text("""
            CREATE TABLE IF NOT EXISTS background_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name VARCHAR,
                status VARCHAR,
                started_at DATETIME,
                completed_at DATETIME,
                duration_seconds FLOAT,
                error_message TEXT,
                triggered_by VARCHAR,
                tenant_id INTEGER
            )
            """)
            )
            print("Creating Indexes...")
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_bg_jobs_name ON background_jobs (job_name)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_bg_jobs_started ON background_jobs (started_at)"
                )
            )
            print("Migration Phase 5 Successful!")
        except Exception as e:
            print(f"Migration Failed: {e}")


if __name__ == "__main__":
    migrate_jobs_phase5()
