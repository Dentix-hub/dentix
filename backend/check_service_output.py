def check_api_response():
    # Login to get token (assuming I need auth or using debug bypass if exists)
    # Actually, verify_schema.py used schemas directly, but here I need API response.
    # I'll rely on the existing backend running on port 8000.
    # I'll try to fetch without auth first (if permitted) or assume I need a token.
    # For speed, I will use the debug script approach or just inspect the service output directly.
    # Actually, I can use the existing `backend/debug_root.py` style to fetch data via service directly.

    from backend.database import SessionLocal
    from backend.services.inventory_service import InventoryService
    from backend.models.inventory import Material

    db = SessionLocal()
    try:
        # Check materials first
        mat_count = db.query(Material).filter(Material.tenant_id == 1).count()
        print(f"Materials for tenant 1: {mat_count}")

        # If 0, check what tenant IDs exist
        if mat_count == 0:
            tenants = [t[0] for t in db.query(Material.tenant_id).distinct().all()]
            print(f"Available Tenant IDs in Materials: {tenants}")
            if tenants:
                tenant_id = tenants[0]
                print(f"Switching to tenant {tenant_id}")
                service = InventoryService(db, tenant_id=tenant_id)
                summary = service.get_material_stock_summary(tenant_id=tenant_id)

        else:
            summary = service.get_material_stock_summary(tenant_id=1)

        if summary:
            print(f"\n{'ID':<5} {'Name':<30} {'Price':<10}")
            print("-" * 50)
            for item in summary:
                # Access attributes directly as it is a Pydantic model (MaterialStockSummary)
                print(
                    f"{item.material_id:<5} {item.material_name[:28]:<30} {item.standard_price}"
                )
        else:
            print("No Stock Items found")
    finally:
        db.close()


if __name__ == "__main__":
    check_api_response()
