import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from backend.database import SessionLocal
from backend import models

def update_prices():
    db = SessionLocal()
    try:
        print("Updating Procedure Prices...")
        
        updates = {
            "Composite Filling Class I": 600.0,
            "Composite Filling Class II": 800.0,
            "Composite Filling Class III": 700.0,
            "Composite Filling Class IV": 900.0,
            "Composite Filling Class V": 500.0,
            "Amalgam Filling Class I": 400.0,
            "Amalgam Filling Class II": 500.0,
            "Temporary Filling": 150.0,
            "Re-filling": 300.0,
            "Anterior Aesthetic Filling": 100.0,
            "Root Canal Treatment": 1500.0,
            "Retreatment Root Canal": 2000.0,
            "Simple Extraction": 200.0,
            "Surgical Extraction": 800.0,
            "Wisdom Tooth Extraction": 1000.0,
            "Partially Impacted Wisdom Tooth Extraction": 1500.0,
            "Fully Impacted Wisdom Tooth Extraction": 2000.0,
            "Primary Tooth Extraction": 150.0,
            "Root Remnants Extraction": 300.0,
            "Porcelain Crown": 1200.0,
            "Zirconia Crown": 2500.0,
            "E-max Crown": 3000.0,
            "Metal Crown": 800.0,
            "Temporary Crown": 200.0,
            "Fixed Bridge": 3000.0,
            "Crown Recementation": 100.0,
            "Complete Acrylic Denture": 4000.0,
            "Partial Acrylic Denture": 2000.0,
            "Partial Metal Denture": 3500.0,
            "Flexible Denture": 2500.0,
            "Scaling": 300.0,
            "Examination": 100.0,
            "Follow-up Session": 50.0
        }
        
        procedures = db.query(models.Procedure).all()
        count = 0
        for p in procedures:
            # Match partial name if possible or exact
            found_price = None
            for key, price in updates.items():
                if key in p.name:
                    found_price = price
                    break
            
            if found_price is not None and (p.price == 0.0 or p.price is None):
                p.price = found_price
                count += 1
                
        db.commit()
        print(f"Updated {count} procedures with new prices.")
        
    finally:
         db.close()

if __name__ == "__main__":
    update_prices()
