import os
import sys
from sqlalchemy import create_engine, text

# Add backend directory to python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Production mode enforced.")


def migrate():
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # 1. Add is_deleted to notification_reads
        try:
            print("Migrating notification_reads...")
            # Postgres syntax
            conn.execute(
                text(
                    "ALTER TABLE notification_reads ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE"
                )
            )
            conn.commit()
            print("✅ notification_reads updated.")
        except Exception as e:
            print(f"⚠️ notification_reads: {e}")

        # 2. Add permissions to users
        try:
            print("Migrating users...")
            conn.execute(text("ALTER TABLE users ADD COLUMN permissions TEXT"))
            conn.commit()
            print("✅ users updated.")
        except Exception as e:
            print(f"⚠️ users: {e}")


if __name__ == "__main__":
    migrate()
