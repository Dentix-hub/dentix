import sys
import os

sys.path.append(os.getcwd())
from backend.database import SessionLocal
from backend.models.inventory import Material, Warehouse, StockItem, Batch

db = SessionLocal()

print("--- WAREHOUSES ---")
whs = db.query(Warehouse).all()
for w in whs:
    print(f"ID: {w.id}, Name: {w.name}, Type: {w.type}")

print("\n--- MATERIALS ---")
mats = db.query(Material).all()
for m in mats:
    print(f"ID: {m.id}, Name: {m.name}, Type: {m.type}, Unit: {m.base_unit}")

print("\n--- STOCK ITEMS ---")
items = db.query(StockItem).all()
for i in items:
    # Get batch material
    batch = db.query(Batch).get(i.batch_id)
    mat = db.query(Material).get(batch.material_id)
    print(
        f"Warehouse: {i.warehouse_id}, Material: {mat.name} (ID: {mat.id}), Qty: {i.quantity}, Batch: {batch.batch_number}"
    )

db.close()
