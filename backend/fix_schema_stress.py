"""
Fix Missing Columns Script
Adds 'email' column to patients table if missing.
"""
import sys
import os
from sqlalchemy import text
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, engine

def fix_schema():
    print("🔧 Checking Schema...")
    db = SessionLocal()
    try:
        # Check patients email
        try:
            db.execute(text("ALTER TABLE patients ADD COLUMN email VARCHAR;"))
            print("✅ Added 'email' column to patients")
        except Exception as e:
            if "duplicate" in str(e).lower() or "exists" in str(e).lower():
                print("ℹ️ 'email' column already exists in patients")
            else:
                print(f"⚠️ Error adding email: {e}")

        # Check patients address
        try:
            db.execute(text("ALTER TABLE patients ADD COLUMN address VARCHAR;"))
            print("✅ Added 'address' column to patients")
        except Exception as e:
            if "duplicate" in str(e).lower() or "exists" in str(e).lower():
                print("ℹ️ 'address' column already exists in patients")
            else:
                print(f"⚠️ Error adding address: {e}")
        
        db.commit()
        print("✅ Schema Fix Complete")
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_schema()
