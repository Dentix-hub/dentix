import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sqlalchemy import text
from backend.database import engine, SessionLocal

db = SessionLocal()

try:
    result = db.execute(text("SELECT id, name, packaging_ratio FROM materials WHERE name LIKE '%Lidocaine%' OR name LIKE '%Septanest%'"))
    print("\n--- Material Ratios ---")
    for row in result:
        print(f"ID: {row.id} | Name: {row.name} | Ratio: {row.packaging_ratio}")
finally:
    db.close()
