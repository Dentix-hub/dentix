import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.models.inventory import Material, Batch, ProcedureMaterialWeight
from backend.models.clinical import Procedure

SQLALCHEMY_DATABASE_URL = "sqlite:///./clinic.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("--- Inspecting Materials (Composite) ---")
materials = db.query(Material).filter(Material.name.like("%omposite%")).all()
for m in materials:
    print(f"ID: {m.id}, Name: {m.name}, Ratio: {m.packaging_ratio}, BaseUnit: {m.base_unit}")
    
    batches = db.query(Batch).filter(Batch.material_id == m.id).all()
    for b in batches:
        print(f"  -> Batch: {b.batch_number}, Cost: {b.cost_per_unit}, Expiry: {b.expiry_date}")

print("\n--- Inspecting Procedure Weights ---")
weights = db.query(ProcedureMaterialWeight).all()
for w in weights:
    mat = db.query(Material).get(w.material_id)
    proc = db.query(Procedure).get(w.procedure_id)
    print(f"Proc: {proc.name} (ID: {proc.id}) uses {mat.name} (ID: {mat.id}) -> Weight: {w.weight}")
