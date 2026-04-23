import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
# Add project root to path (Two levels up from backend/tests is backend, Three is root)
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from backend.database import Base
from backend.models.inventory import ProcedureMaterialWeight
from backend.models.clinical import Procedure
from backend.services.inventory_service import inventory_service
from backend.services.cost_engine import CostEngine
from backend import schemas

def test_smart_costing_flow(db_session):
    db = db_session
    try:
        tenant_id = 1
        print("\n--- Starting Smart Costing Verification ---")

        # 1. Setup Material & Stock with Cost
        print("1. Creating Material 'Gold Amalgam'...")
        # Check if material already exists to avoid conflicts in persistent tests
        from backend.models.inventory import Material
        mat = db.query(Material).filter(Material.name == "Gold Amalgam", Material.tenant_id == tenant_id).first()
        if not mat:
            mat = inventory_service.create_material(
                schemas.inventory.MaterialCreate(
                    name="Gold Amalgam", type="DIVISIBLE", base_unit="g"
                ),
                tenant_id,
                db,
            )

        print("2. Receiving Stock (10g @ 500 EGP/g)...")
        # Ensure warehouse 1 exists or use a dynamic one
        from backend.models.inventory import Warehouse
        wh = db.query(Warehouse).filter(Warehouse.tenant_id == tenant_id).first()
        if not wh:
            wh = Warehouse(name="Main Warehouse", tenant_id=tenant_id)
            db.add(wh)
            db.commit()
            db.refresh(wh)

        inventory_service.add_stock(
            material_id=mat.id,
            warehouse_id=wh.id,
            batch_data=schemas.inventory.BatchBase(
                batch_number="BATCH-COST-TEST",
                expiry_date="2030-01-01",
                cost_per_unit=500.0,
            ),
            quantity=10,
            tenant_id=tenant_id,
            user_id=1,
            db=db,
        )

        # 2. Setup Procedure
        print("3. Creating Procedure 'Gold Filling'...")
        proc = db.query(Procedure).filter(Procedure.name == "Gold Filling", Procedure.tenant_id == tenant_id).first()
        if not proc:
            proc = Procedure(name="Gold Filling", price=1200.0, tenant_id=tenant_id)
            db.add(proc)
            db.commit()
            db.refresh(proc)

        # 3. Link them (BOM)
        print("4. Linking Material to Procedure (2g usage)...")
        # Direct DB insert for BOM to save time
        bom = db.query(ProcedureMaterialWeight).filter(
            ProcedureMaterialWeight.procedure_id == proc.id,
            ProcedureMaterialWeight.material_id == mat.id
        ).first()
        if not bom:
            bom = ProcedureMaterialWeight(
                procedure_id=proc.id, 
                material_id=mat.id, 
                tenant_id=tenant_id, 
                weight=2.0,
                current_average_usage=2.0  # Crucial: Set learned usage to 2g
            )
            db.add(bom)
            db.commit()

        # 4. Run Cost Engine
        print("5. Running Cost Engine...")
        cost_engine = CostEngine(db, tenant_id)
        analysis = cost_engine.calculate_procedure_cost(proc.id)

        print("\n--- Analysis Result ---")
        print(f"Procedure: {analysis['procedure_name']}")
        print(f"Total Cost: {analysis['total_estimated_cost']} (Expected: 1000.0)")
        print(f"Current Price: {analysis['current_price']}")
        print(f"Margin: {analysis['margin_percentage']}%")

        assert analysis["total_estimated_cost"] == 1000.0
        assert analysis["profit_margin"] == 200.0

        print("✅ SUCCESS: Cost Calculated Correctly!")

        # Cleanup
        db.delete(bom)
        db.delete(proc)
        inventory_service.delete_material(mat.id, tenant_id, db)
        print("Cleanup done.")

    except Exception as e:
        print(f"❌ FAILED: {e}")
        raise e
