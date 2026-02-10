from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Production mode enforced.")

engine = create_engine(SQLALCHEMY_DATABASE_URL)


def run_migration():
    print("Starting User Schema Sync...")
    from sqlalchemy import inspect

    # Fix Generic Postgres URL handling if not already done in imports

    inspector = inspect(engine)
    existing_columns = [c["name"] for c in inspector.get_columns("users")]

    columns_to_check = [
        ("is_active", "BOOLEAN DEFAULT TRUE"),
        ("is_deleted", "BOOLEAN DEFAULT FALSE"),
        ("deleted_at", "TIMESTAMP"),
    ]

    with engine.begin() as conn:
        for col_name, col_type in columns_to_check:
            if col_name in existing_columns:
                print(f" - User column '{col_name}' exists.")
            else:
                print(f" - Adding missing column '{col_name}' to users...")
                try:
                    conn.execute(
                        text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                    )
                    print("   > Done.")
                except Exception as e:
                    print(f"   > Error adding {col_name}: {e}")


if __name__ == "__main__":
    run_migration()
