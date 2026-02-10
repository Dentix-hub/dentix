from sqlalchemy import create_engine, text, inspect
import os
from dotenv import load_dotenv

# Logic to load correct .env
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
    print("Starting Unique Constraints Removal...")
    with engine.connect() as conn:
        inspector = inspect(engine)

        # 1. Tenants Name
        print("Checking tenants.name constraints...")
        unique_constraints = inspector.get_unique_constraints("tenants")
        indexes = inspector.get_indexes("tenants")

        # Drop Unique Constraints
        for uc in unique_constraints:
            if "name" in uc["column_names"]:
                print(f" - Dropping unique constraint: {uc['name']}")
                try:
                    conn.execute(
                        text(f"ALTER TABLE tenants DROP CONSTRAINT {uc['name']}")
                    )
                except Exception as e:
                    # PG/MySQL specific fallback or error
                    print(f"   (PG/MySQL style failed: {e})")

        # Drop Unique Indexes
        for idx in indexes:
            if "name" in idx["column_names"] and idx["unique"]:
                print(f" - Dropping unique index: {idx['name']}")
                try:
                    conn.execute(text(f"DROP INDEX {idx['name']}"))
                    print("   > Dropped.")
                except Exception as e:
                    print(f"   > Error dropping index {idx['name']}: {e}")

        # 2. Users Username
        print("Checking users.username constraints...")
        unique_constraints = inspector.get_unique_constraints("users")
        indexes = inspector.get_indexes("users")

        for uc in unique_constraints:
            if "username" in uc["column_names"]:
                print(f" - Dropping unique constraint: {uc['name']}")
                try:
                    conn.execute(
                        text(f"ALTER TABLE users DROP CONSTRAINT {uc['name']}")
                    )
                except Exception as e:
                    print(f"   (Error: {e})")

        for idx in indexes:
            if "username" in idx["column_names"] and idx["unique"]:
                print(f" - Dropping unique index: {idx['name']}")
                try:
                    conn.execute(text(f"DROP INDEX {idx['name']}"))
                    print("   > Dropped.")
                except Exception as e:
                    print(f"   > Error dropping index {idx['name']}: {e}")

        # Create non-unique indexes if missing (Optional, but good for performance)
        # We removed unique=True but kept index=True in models.
        # Ensure standard indexes exist
        try:
            print("Ensuring non-unique indexes exist...")
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_tenants_name ON tenants (name)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_users_username ON users (username)")
            )
            print("   > Done (or already existed).")
        except Exception as e:
            print(f"   > Index creation note: {e}")

        conn.commit()
        print("Migration completed.")


if __name__ == "__main__":
    run_migration()
