from backend.database import SessionLocal
from backend.services.inventory_service import inventory_service
from backend import models

def debug_inventory():
    db = SessionLocal()
    tenant_id = 10
    print(f"Debugging Inventory for Tenant {tenant_id}...")
    
    try:
        print("\n1. Testing get_materials...")
        materials = inventory_service.get_materials(tenant_id=tenant_id, db=db)
        print(f"✅ Found {len(materials)} materials.")
        for m in materials[:3]:
            print(f" - {m.name}: Price={m.standard_price}")
            
    except Exception as e:
        print(f"❌ get_materials FAILED: {e}")
        import traceback
        traceback.print_exc()

    try:
        print("\n2. Testing active sessions (placeholder logic in router likely)...")
        # Check if service has get_active_sessions or similar?
        # I remember seeing stock_logic in inventory_service.
        # Let's check models.MaterialSession queries manually if service method is missing.
        sessions = db.query(models.MaterialSession).filter(
            models.MaterialSession.status == "ACTIVE"
        ).all()
        print(f"✅ Found {len(sessions)} active sessions.")

    except Exception as e:
        print(f"❌ Active sessions check FAILED: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    debug_inventory()
