import sys
import os
from sqlalchemy import text

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, engine


def fix_null_values():
    print("🔧 Starting NULL Value Fix for Soft Delete...")
    db = SessionLocal()
    try:
        # Detect Dialect
        dialect = engine.dialect.name
        is_sqlite = dialect == "sqlite"
        print(f"🔧 Detected Dialect: {dialect}")

        bool_false = "0" if is_sqlite else "FALSE"

        print("🔄 Updating NULL is_deleted in 'patients' to False...")
        db.execute(
            text(
                f"UPDATE patients SET is_deleted = {bool_false} WHERE is_deleted IS NULL"
            )
        )

        print("🔄 Updating NULL is_deleted in 'appointments' to False...")
        db.execute(
            text(
                f"UPDATE appointments SET is_deleted = {bool_false} WHERE is_deleted IS NULL"
            )
        )

        print("💾 Committing changes...")
        db.commit()
        print("✅ Data Integrity Fix Completed.")

    except Exception as e:
        print(f"❌ Fix Failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fix_null_values()
