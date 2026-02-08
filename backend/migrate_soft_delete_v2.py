import sys
import os
from sqlalchemy import text, inspect

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, engine

def migrate_soft_delete():
    print("🚀 Starting Soft Delete Migration...")
    db = SessionLocal()
    try:
        inspector = inspect(engine)
        
        # Detect Dialect
        dialect = engine.dialect.name
        is_sqlite = dialect == "sqlite"
        print(f"🔧 Detected Dialect: {dialect}")

        # Define Type-Specific SQL
        bool_default = "0" if is_sqlite else "FALSE"
        datetime_type = "DATETIME" if is_sqlite else "TIMESTAMP"

        # 1. Update Patients Table
        columns = [c['name'] for c in inspector.get_columns('patients')]
        if 'is_deleted' not in columns:
            print("Adding is_deleted to patients...")
            db.execute(text(f"ALTER TABLE patients ADD COLUMN is_deleted BOOLEAN DEFAULT {bool_default}"))
        
        if 'deleted_at' not in columns:
            print("Adding deleted_at to patients...")
            db.execute(text(f"ALTER TABLE patients ADD COLUMN deleted_at {datetime_type}"))
            
        # 2. Update Appointments Table
        columns = [c['name'] for c in inspector.get_columns('appointments')]
        if 'is_deleted' not in columns:
            print("Adding is_deleted to appointments...")
            db.execute(text(f"ALTER TABLE appointments ADD COLUMN is_deleted BOOLEAN DEFAULT {bool_default}"))
            
        if 'deleted_at' not in columns:
            print("Adding deleted_at to appointments...")
            db.execute(text(f"ALTER TABLE appointments ADD COLUMN deleted_at {datetime_type}"))

        print("💾 Committing changes...")
        db.commit()

        print("✅ Migration Validating...")
        # Verify
        inspector = inspect(engine)
        p_cols = [c['name'] for c in inspector.get_columns('patients')]
        a_cols = [c['name'] for c in inspector.get_columns('appointments')]
        
        if 'is_deleted' in p_cols and 'is_deleted' in a_cols:
             print("✅ Success: Columns added successfully.")
        else:
             print("❌ Error: Columns verification failed.")

    except Exception as e:
        print(f"❌ Migration Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_soft_delete()
