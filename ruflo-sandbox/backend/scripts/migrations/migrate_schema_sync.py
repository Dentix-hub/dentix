from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Logic to load correct .env (copied from database.py fix)
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
env_path = os.path.join(BACKEND_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(env_path)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Production mode enforced.")
print(f"Migrating DB: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)


def run_migration():
    print("Starting Schema Sync...")
    with engine.connect() as conn:
        try:
            # 1. Check/Add Tenant Backup/Login columns
            columns_to_check = [
                ("last_login", "TIMESTAMP"),
                ("backup_frequency", "VARCHAR DEFAULT 'off'"),
                ("google_refresh_token", "VARCHAR"),
                ("last_backup_at", "TIMESTAMP"),
            ]

            from sqlalchemy import inspect

            inspector = inspect(engine)
            existing_columns = [c["name"] for c in inspector.get_columns("tenants")]

            for col_name, col_type in columns_to_check:
                if col_name in existing_columns:
                    print(f" - Tenant column '{col_name}' exists.")
                else:
                    print(f" - Adding missing column '{col_name}' to tenants...")
                    try:
                        # For some dialects, we might need to commit differently or use strict execution
                        # But since we are inside a block, let's try direct execution
                        with engine.begin() as trans_conn:
                            trans_conn.execute(
                                text(
                                    f"ALTER TABLE tenants ADD COLUMN {col_name} {col_type}"
                                )
                            )
                        print("   > Done.")
                    except Exception as e:
                        print(f"   > Error adding {col_name}: {e}")

            conn.commit()
            print("Schema Sync completed.")
        except Exception as e:
            print(f"Migration error: {e}")


if __name__ == "__main__":
    run_migration()
