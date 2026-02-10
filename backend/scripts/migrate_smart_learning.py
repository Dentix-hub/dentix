import sys
import os
from sqlalchemy import create_engine, text, inspect

# Add project root to path
# Script is in backend/scripts/migrate_smart_learning.py
# 1. scripts 2. backend 3. root
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from backend.database import SQLALCHEMY_DATABASE_URL, Base


def migrate():
    print("Starting Smart Learning Migration...")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

    # 1. Create New Tables (ProcedureMaterialWeight, MaterialLearningLog)
    print("Creating new tables...")
    Base.metadata.create_all(engine)

    # 2. Alter MaterialSession
    print("Checking MaterialSession schema...")
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("material_sessions")]

    with engine.connect() as conn:
        if "closed_at" not in columns:
            print("Adding 'closed_at' to material_sessions...")
            conn.execute(
                text("ALTER TABLE material_sessions ADD COLUMN closed_at DATETIME")
            )

        if "total_amount_consumed" not in columns:
            print("Adding 'total_amount_consumed' to material_sessions...")
            conn.execute(
                text(
                    "ALTER TABLE material_sessions ADD COLUMN total_amount_consumed FLOAT"
                )
            )

        # Check tenant_id in materials (It failed earlier, ensuring it is correct)
        # We can't easily alter NOT NULL in SQLite without recreation.
        # But we fixed the Code to pass a Value, so validation should pass.

    print("Migration Complete.")


if __name__ == "__main__":
    migrate()
