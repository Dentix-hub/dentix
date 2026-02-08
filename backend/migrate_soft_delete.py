
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

# Backend dir
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
# Project root
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Production mode enforced.")

print(f"Using Connection URL: {SQLALCHEMY_DATABASE_URL}")

engine = create_engine(SQLALCHEMY_DATABASE_URL)

def run_migration():
    print("Starting Soft Delete migration...")
    with engine.connect() as conn:
        try:
            # Tenants
            print("Migrating tenants...")
            try:
                conn.execute(text("ALTER TABLE tenants ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
                print(" - Added is_deleted to tenants")
            except Exception as e:
                print(f" - tenants.is_deleted: {e}")

            try:
                conn.execute(text("ALTER TABLE tenants ADD COLUMN deleted_at TIMESTAMP"))
                print(" - Added deleted_at to tenants")
            except Exception as e:
                print(f" - tenants.deleted_at: {e}")

            # Users
            print("Migrating users...")
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
                print(" - Added is_deleted to users")
            except Exception as e:
                print(f" - users.is_deleted: {e}")

            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP"))
                print(" - Added deleted_at to users")
            except Exception as e:
                print(f" - users.deleted_at: {e}")

            conn.commit()
            print("Migration completed.")
        except Exception as e:
            print(f"Migration error: {e}")

if __name__ == "__main__":
    run_migration()
