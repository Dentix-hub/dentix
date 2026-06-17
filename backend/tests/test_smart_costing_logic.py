import sys
import os
import pytest
from sqlalchemy import create_engine, select
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

@pytest.mark.asyncio
async def test_smart_costing_flow(async_db_session):
    db = async_db_session
    import uuid
    uid = str(uuid.uuid4())[:8]
    mat_name = f"Gold Amalgam {uid}"
    proc_name = f"Gold Filling {uid}"

    try:
        tenant_id = 1
        print(f"\n--- Starting Smart Costing Verification ({uid}) ---")

        # 1. Setup Material & Stock with Cost
        from backend.models.inventory import Material
        mat = await inventory_service.create_material(
            schemas.inventory.MaterialCreate(
                name=mat_name, type="DIVISIBLE", base_unit="g"
            ),
            tenant_id,
            db,
        )

        from backend.models.inventory import Warehouse
        stmt = select(Warehouse).where(Warehouse.tenant_id == tenant_id)
        wh = (await db.execute(stmt)).scalars().first()
        if not wh:
            wh = Warehouse(name=f"Main Warehouse {uid}", tenant_id=tenant_id)
            db.add(wh)
            await db.commit()
            await db.refresh(wh)

        await inventory_service.add_stock(
            material_id=mat.id,
            warehouse_id=wh.id,
            batch_data=schemas.inventory.BatchBase(
                batch_number=f"BATCH-{uid}",
                expiry_date="2030-01-01",
                cost_per_unit=500.0,
            ),
            quantity=10,
            tenant_id=tenant_id,
            user_id=1,
            db=db,
        )

        # 2. Setup Procedure
        proc = Procedure(name=proc_name, price=1200.0, tenant_id=tenant_id)
        db.add(proc)
        await db.commit()
        await db.refresh(proc)

        # 3. Link them (BOM)
        bom = ProcedureMaterialWeight(
            procedure_id=proc.id,
            material_id=mat.id,
            tenant_id=tenant_id,
            weight=2.0,
            current_average_usage=2.0  # Crucial: Set learned usage to 2g
        )
        db.add(bom)
        await db.commit()

        # 4. Run Cost Engine
        cost_engine = CostEngine(db, tenant_id)
        analysis = await cost_engine.calculate_procedure_cost(proc.id)

        assert analysis["total_estimated_cost"] == 1000.0
        assert analysis["profit_margin"] == 200.0

        print("✅ SUCCESS: Cost Calculated Correctly!")

        # Cleanup: Only what we created
        await db.delete(bom)
        await db.delete(proc)
        await db.commit()

    except Exception as e:
        print(f"❌ FAILED: {e}")
        await db.rollback()
        raise e

