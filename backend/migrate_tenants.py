
from sqlalchemy import create_engine, text, inspect
import os
from dotenv import load_dotenv

load_dotenv()

# Setup correct DATABASE_URL (forcing async to sync for migration)
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Production mode enforced.")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def run_migration():
    print("Starting Tenant Schema Sync...")
    
    inspector = inspect(engine)
    existing_columns = [c['name'] for c in inspector.get_columns("tenants")]
    
    columns_to_check = [
        ("last_login", "TIMESTAMP"),
        ("last_backup_at", "TIMESTAMP"),
        ("is_deleted", "BOOLEAN DEFAULT FALSE"),
        ("deleted_at", "TIMESTAMP"), 
    ]

    with engine.begin() as conn:
        for col_name, col_type in columns_to_check:
            if col_name in existing_columns:
                print(f" - Tenant column '{col_name}' exists.")
            else:
                print(f" - Adding missing column '{col_name}' to tenants...")
                try:
                    conn.execute(text(f"ALTER TABLE tenants ADD COLUMN {col_name} {col_type}"))
                    print("   > Done.")
                except Exception as e:
                    print(f"   > Error adding {col_name}: {e}")

if __name__ == "__main__":
    run_migration()
