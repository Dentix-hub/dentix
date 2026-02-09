import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.inventory import ProcedureMaterialWeight

SQLALCHEMY_DATABASE_URL = "sqlite:///./clinic.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def fix_weight(proc_id, mat_id, new_weight):
    w = db.query(ProcedureMaterialWeight).filter_by(procedure_id=proc_id, material_id=mat_id).first()
    if w:
        print(f"Updating Mat {mat_id} in Proc {proc_id}: {w.weight} -> {new_weight}")
        w.weight = new_weight
    else:
        print(f"Weight not found for Mat {mat_id} in Proc {proc_id}")

# Realistic Dental Usage
# Composite: 0.25g
# Bond: 0.1 ml (approx 2 drops)
# Etch: 0.2 ml

fix_weight(2, 7, 0.25) # Composite
fix_weight(2, 8, 0.10) # Bond
fix_weight(2, 9, 0.20) # Etch

db.commit()
print("Weights updated to realistic values.")
