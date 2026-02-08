import sys
import os
sys.path.append(os.getcwd())
from backend.database import SessionLocal
from backend.services.inventory_service import inventory_service
from backend.schemas.inventory import BatchBase, StockReceiveRequest
from backend.models.inventory import Batch
from datetime import date

db = SessionLocal()

# Target: Material 8, Warehouse 2, Batch "dfsdhd"
material_id = 8
warehouse_id = 1 # Force adding to MAIN warehouse to ensure availability if fallback logic fails
# Actually, debug showed it's in Warehouse 2. Let's add to Warehouse 2 to be consistent with existing stock.
warehouse_id = 2 

# Get existing batch details
batch = db.query(Batch).filter(Batch.material_id == material_id, Batch.batch_number == "dfsdhd").first()

if not batch:
    print("Batch not found! Creating new one.")
    batch_data = BatchBase(
        batch_number="FIX001",
        expiry_date=date(2027, 1, 1),
        cost_per_unit=100.0
    )
else:
    print(f"Using existing batch: {batch.batch_number}")
    batch_data = BatchBase(
        batch_number=batch.batch_number,
        expiry_date=batch.expiry_date,
        cost_per_unit=batch.cost_per_unit or 0.0,
        supplier=batch.supplier
    )

print(f"Adding 10 units to Material {material_id} in Warehouse {warehouse_id}...")

try:
    inventory_service.add_stock(
        material_id=material_id,
        warehouse_id=warehouse_id,
        batch_data=batch_data,
        quantity=10.0,
        tenant_id=1, # Default tenant
        user_id=1,   # Admin
        db=db
    )
    print("✅ Stock added successfully!")
except Exception as e:
    print(f"❌ Failed: {e}")

db.close()
