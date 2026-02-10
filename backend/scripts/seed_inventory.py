import sys
import os
from datetime import date

# Add project root to sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from backend.database import SessionLocal
from backend.services.inventory_service import inventory_service
from backend.schemas.inventory import (
    MaterialCreate,
    WarehouseCreate,
    BatchBase,
    MaterialType,
)
from backend.models.inventory import Material, Warehouse, Batch, StockItem


def seed_inventory():
    db = SessionLocal()
    tenant_id = 1  # Default Admin Tenant
    user_id = 1  # Default Admin User

    print("🌱 Seeding Inventory...")

    # 1. Create Warehouses
    warehouses = [
        {"name": "Main Warehouse", "type": "MAIN"},
        {"name": "Clinic Cabinet 1", "type": "CLINIC"},
    ]

    for wh_data in warehouses:
        existing = (
            db.query(Warehouse)
            .filter(Warehouse.name == wh_data["name"], Warehouse.tenant_id == tenant_id)
            .first()
        )
        if not existing:
            print(f"   Creating Warehouse: {wh_data['name']}")
            inventory_service.create_warehouse(
                WarehouseCreate(**wh_data), tenant_id, db
            )
        else:
            print(f"   Warehouse exists: {wh_data['name']}")

    # Get IDs
    wh_main = db.query(Warehouse).filter(Warehouse.name == "Main Warehouse").first()
    wh_clinic = db.query(Warehouse).filter(Warehouse.name == "Clinic Cabinet 1").first()

    # 2. Define Materials
    materials = [
        # Composites (Divisible)
        {
            "name": "3M Filtek Z250 A2",
            "type": MaterialType.DIVISIBLE,
            "base_unit": "g",
            "packaging_ratio": 4.0,
            "threshold": 5,
        },
        {
            "name": "3M Filtek Z250 A3",
            "type": MaterialType.DIVISIBLE,
            "base_unit": "g",
            "packaging_ratio": 4.0,
            "threshold": 5,
        },
        {
            "name": "3M Filtek Z350 Enamel A2",
            "type": MaterialType.DIVISIBLE,
            "base_unit": "g",
            "packaging_ratio": 4.0,
            "threshold": 5,
        },
        # Bonding & Etch
        {
            "name": "Ivoclar Tetric N-Bond",
            "type": MaterialType.DIVISIBLE,
            "base_unit": "ml",
            "packaging_ratio": 6.0,
            "threshold": 2,
        },
        {
            "name": "Etchant Gel 37%",
            "type": MaterialType.DIVISIBLE,
            "base_unit": "ml",
            "packaging_ratio": 50.0,
            "threshold": 5,
        },
        # Anesthesia
        {
            "name": "Lidocaine 2%",
            "type": MaterialType.NON_DIVISIBLE,
            "base_unit": "Carpule",
            "packaging_ratio": 50.0,
            "threshold": 50,
        },
        {
            "name": "Septanest 4%",
            "type": MaterialType.NON_DIVISIBLE,
            "base_unit": "Carpule",
            "packaging_ratio": 50.0,
            "threshold": 50,
        },
        # Consumables
        {
            "name": "Dental Needles Short",
            "type": MaterialType.NON_DIVISIBLE,
            "base_unit": "Needle",
            "packaging_ratio": 100.0,
            "threshold": 100,
        },
        {
            "name": "Dental Needles Long",
            "type": MaterialType.NON_DIVISIBLE,
            "base_unit": "Needle",
            "packaging_ratio": 100.0,
            "threshold": 100,
        },
        {
            "name": "Cotton Rolls",
            "type": MaterialType.NON_DIVISIBLE,
            "base_unit": "Roll",
            "packaging_ratio": 500.0,
            "threshold": 200,
        },
        {
            "name": "Saliva Ejector Tips",
            "type": MaterialType.NON_DIVISIBLE,
            "base_unit": "Tip",
            "packaging_ratio": 100.0,
            "threshold": 50,
        },
        {
            "name": "Gloves Medium",
            "type": MaterialType.NON_DIVISIBLE,
            "base_unit": "Pair",
            "packaging_ratio": 100.0,
            "threshold": 20,
        },
        {
            "name": "Face Masks",
            "type": MaterialType.NON_DIVISIBLE,
            "base_unit": "Mask",
            "packaging_ratio": 50.0,
            "threshold": 20,
        },
    ]

    for mat_data in materials:
        # Check if material exists
        mat = (
            db.query(Material)
            .filter(Material.name == mat_data["name"], Material.tenant_id == tenant_id)
            .first()
        )
        if not mat:
            print(f"   Creating Material: {mat_data['name']}")
            mat = inventory_service.create_material(
                MaterialCreate(**mat_data), tenant_id, db
            )
        else:
            print(f"   Material exists: {mat_data['name']}")
            # Update ratio if needed (optional logic, skipping for safety)

        # 3. Add Initial Stock (If 0)
        # Check if any stock exists
        total_stock = (
            db.query(StockItem).join(Batch).filter(Batch.material_id == mat.id).count()
        )
        if total_stock == 0:
            print(f"   ➕ Adding Initial Stock for {mat.name}...")

            # Create 2 Batches for realism
            batches = [
                {
                    "number": f"B-{mat.id}-001",
                    "expiry": date(2026, 12, 31),
                    "qty": 5,
                },  # 5 Packs
                {
                    "number": f"B-{mat.id}-002",
                    "expiry": date(2027, 6, 30),
                    "qty": 3,
                },  # 3 Packs
            ]

            for b_info in batches:
                inventory_service.add_stock(
                    material_id=mat.id,
                    warehouse_id=wh_main.id,  # Add to Main Warehouse
                    batch_data=BatchBase(
                        batch_number=b_info["number"],
                        expiry_date=b_info["expiry"],
                        cost_per_unit=150.0,  # Dummy cost
                    ),
                    quantity=float(b_info["qty"]),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    db=db,
                )

    print("✅ Seed Complete!")
    db.close()


if __name__ == "__main__":
    seed_inventory()
