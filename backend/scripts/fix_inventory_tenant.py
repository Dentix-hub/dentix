import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database import SessionLocal
from backend.models.inventory import Material, Warehouse, Batch, StockItem, MaterialSession, StockMovement

def fix_inventory_tenant():
    db = SessionLocal()
    target_tenant_id = 10
    source_tenant_id = 1
    
    # 1. Warehouses
    whs = db.query(Warehouse).filter(Warehouse.tenant_id == source_tenant_id).all()
    print(f"Updating {len(whs)} Warehouses to Tenant {target_tenant_id}...")
    for w in whs:
        w.tenant_id = target_tenant_id
    
    # 2. Materials
    mats = db.query(Material).filter(Material.tenant_id == source_tenant_id).all()
    print(f"Updating {len(mats)} Materials to Tenant {target_tenant_id}...")
    for m in mats:
        m.tenant_id = target_tenant_id

    # 3. Batches
    batches = db.query(Batch).filter(Batch.tenant_id == source_tenant_id).all()
    print(f"Updating {len(batches)} Batches to Tenant {target_tenant_id}...")
    for b in batches:
        b.tenant_id = target_tenant_id

    # 4. StockItems
    items = db.query(StockItem).filter(StockItem.tenant_id == source_tenant_id).all()
    print(f"Updating {len(items)} StockItems to Tenant {target_tenant_id}...")
    for i in items:
        i.tenant_id = target_tenant_id

    db.commit()
    print("✅ Migration Complete!")
    db.close()

if __name__ == "__main__":
    fix_inventory_tenant()
