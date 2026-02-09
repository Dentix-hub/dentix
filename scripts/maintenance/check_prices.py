import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from backend.database import SessionLocal
from backend import models

def check_prices():
    db = SessionLocal()
    try:
        print("--- Materials ---")
        mats = db.query(models.Material).all()
        for m in mats:
            print(f"ID: {m.id} | Name: {m.name} | Std Price: {m.standard_price}")
            
        print("\n--- Batches ---")
        batches = db.query(models.Batch).limit(10).all()
        for b in batches:
            print(f"ID: {b.id} | Mat ID: {b.material_id} | Cost: {b.cost_per_unit}")
            
        print("\n--- Treatments ---")
        treatments = db.query(models.Treatment).order_by(models.Treatment.id.desc()).limit(5).all()
        for t in treatments:
            print(f"ID: {t.id} | Cost: {t.cost} | Procedure: {t.procedure}")

        print("\n--- Procedures (Menu) ---")
        procedures = db.query(models.Procedure).all()
        for p in procedures:
             print(f"ID: {p.id} | Name: {p.name} | Price: {p.price}")

    finally:
        db.close()

if __name__ == "__main__":
    check_prices()
