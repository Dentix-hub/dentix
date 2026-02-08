import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, SQLALCHEMY_DATABASE_URL
DATABASE_URL = SQLALCHEMY_DATABASE_URL
from backend.services.inventory_service import inventory_service

# Setup DB
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def test_validate_stock():
    print("Testing validate_stock...")
    try:
        # Pick a material ID that likely exists (e.g. from user logs it was 5 or 7 or 8)
        # User had "3M Filtek Z250 A3" (Material ID unknown but we can try 1)
        # Or better, list materials first
        from backend.models.inventory import Material
        mat = db.query(Material).first()
        if not mat:
            print("No materials found to test.")
            return

        print(f"Testing with Material: {mat.name} (ID: {mat.id})")
        
        # Call validate_stock with warehouse_id=None (Global)
        is_valid, available, name = inventory_service.validate_stock(
            material_id=mat.id,
            quantity=0.1,
            tenant_id=mat.tenant_id,
            warehouse_id=None,
            db=db
        )
        print(f"Validate Result: Valid={is_valid}, Available={available}, Name={name}")

    except Exception as e:
        print(f"CRASH in validate_stock: {e}")
        import traceback
        traceback.print_exc()

def test_full_flow():
    print("\nTesting Full Flow (Create+Consume)...")
    try:
        from backend.models.inventory import Material, Batch, StockItem, Warehouse
        from datetime import date
        
        # 1. Get or Create Material
        mat = db.query(Material).filter(Material.name == "DebugMaterial").first()
        if not mat:
            mat = Material(name="DebugMaterial", type="DIVISIBLE", base_unit="ml", tenant_id=10)
            db.add(mat)
            db.flush()
            
        print(f"Material: {mat.name} (ID: {mat.id})")
        
        # 2. Add Stock (Directly)
        # Ensure Warehouse exists
        wh = db.query(Warehouse).filter(Warehouse.tenant_id == 10).first()
        if not wh:
            wh = Warehouse(name="DebugWH", tenant_id=10)
            db.add(wh)
            db.flush()
            
        # Create Batch
        batch = Batch(material_id=mat.id, tenant_id=10, batch_number="DEBUG001", expiry_date=date(2030, 1, 1))
        db.add(batch)
        db.flush()
        
        # Create StockItem
        si = StockItem(warehouse_id=wh.id, batch_id=batch.id, tenant_id=10, quantity=100.0)
        db.add(si)
        db.commit()
        
        print(f"Added Stock: 100.0 to Warehouse {wh.id}")
        
        # 3. Validate
        valid, avail, name = inventory_service.validate_stock(mat.id, 50.0, 10, None, db)
        print(f"Validate(50.0): Valid={valid}, Avail={avail}")
        
        # 4. Consume
        print("Consuming 10.0...")
        inventory_service.consume_stock(
            material_id=mat.id,
            quantity=10.0,
            tenant_id=10,
            user_id=1,
            warehouse_id=None,
            db=db
        )
        print("Consume Success!")
        
        # 5. Check remaining
        valid, avail, name = inventory_service.validate_stock(mat.id, 0.1, 10, None, db)
        print(f"Post-Consume Avail={avail}")
        
    except Exception as e:
        print(f"CRASH in Full Flow: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()

if __name__ == "__main__":
    test_full_flow()
