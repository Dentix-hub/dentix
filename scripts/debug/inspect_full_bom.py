import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.inventory import Material, Batch, ProcedureMaterialWeight
from backend.models.clinical import Procedure

SQLALCHEMY_DATABASE_URL = "sqlite:///./clinic.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("--- Inspecting Materials (All) ---")
# Get all materials used in Procedure ID 2 (Class I)
proc_id = 2
weights = db.query(ProcedureMaterialWeight).filter_by(procedure_id=proc_id).all()

print(f"Procedure {proc_id} Material Usage:")
for w in weights:
    m = db.query(Material).get(w.material_id)
    if not m:
        print(f"!! Missing Material ID: {w.material_id}")
        continue
        
    print(f"\n[ID: {m.id}] {m.name}")
    print(f"  - Usage Weight: {w.weight} {m.base_unit}")
    print(f"  - Packaging Ratio: {m.packaging_ratio}")
    
    # Check Price
    batch = db.query(Batch).filter_by(material_id=m.id).order_by(Batch.created_at.desc()).first()
    cost = batch.cost_per_unit if batch else 0.0
    print(f"  - Latest Batch Cost: {cost}")
    
    # Calculate Impact
    ratio = m.packaging_ratio if m.packaging_ratio and m.packaging_ratio > 0 else 1.0
    unit_cost = cost / ratio
    total_impact = unit_cost * w.weight
    print(f"  -> CALC: {cost} / {ratio} * {w.weight} = {total_impact:.2f} EGP")
