"""
Cost Calculation Unit Tests (Refactored to Async)
Tests for CostEngine calculations using the async database session.
"""

import pytest
from backend.services.cost_engine import CostEngine
from backend.models.inventory import StockItem, Batch, Material, ProcedureMaterialWeight
from backend.models.clinical import Procedure
from backend import models
from backend.database import Base


@pytest.mark.asyncio
async def test_calculate_bom_cost(async_db_session, async_engine_fixture):
    # Ensure tables are created in the async test database
    async with async_engine_fixture.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Clean up any existing rows to avoid UNIQUE constraint conflicts due to shared SQLite cache
    from sqlalchemy import delete
    await async_db_session.execute(delete(ProcedureMaterialWeight))
    await async_db_session.execute(delete(StockItem))
    await async_db_session.execute(delete(Batch))
    await async_db_session.execute(delete(Material))
    await async_db_session.execute(delete(Procedure))
    await async_db_session.execute(delete(models.Warehouse))
    await async_db_session.commit()

    # Ensure Tenant exists
    stmt_tenant = await async_db_session.execute(
        models.Tenant.__table__.select().where(models.Tenant.id == 1)
    )
    if not stmt_tenant.first():
        tenant = models.Tenant(id=1, name="Test Clinic", plan="Pro")
        async_db_session.add(tenant)
        await async_db_session.commit()

    # Seed Warehouse
    warehouse = models.Warehouse(id=1, name="Main Warehouse", type="MAIN", tenant_id=1)
    async_db_session.add(warehouse)
    await async_db_session.commit()

    # Seed Materials
    mat1 = Material(id=1, name="Resin", base_unit="g", type="DIVISIBLE", tenant_id=1)
    mat2 = Material(id=2, name="Bond", base_unit="ml", type="DIVISIBLE", tenant_id=1)
    async_db_session.add_all([mat1, mat2])
    await async_db_session.commit()

    # Seed Batches
    from datetime import date
    batch1 = Batch(id=101, material_id=1, cost_per_unit=10.0, tenant_id=1, batch_number="B1", expiry_date=date(2026, 12, 31))
    batch2 = Batch(id=102, material_id=2, cost_per_unit=50.0, tenant_id=1, batch_number="B2", expiry_date=date(2026, 12, 31))
    async_db_session.add_all([batch1, batch2])
    await async_db_session.commit()

    # Seed StockItems
    stock1 = StockItem(id=1, batch_id=101, warehouse_id=1, quantity=100, tenant_id=1)
    stock2 = StockItem(id=2, batch_id=102, warehouse_id=1, quantity=10, tenant_id=1)
    async_db_session.add_all([stock1, stock2])
    await async_db_session.commit()

    # Seed Procedure Definition (BOM)
    # Uses 2g of Resin and 0.5ml of Bond
    bom1 = ProcedureMaterialWeight(
        id=1,
        material_id=1,
        weight=2.0,
        tenant_id=1,
        procedure_id=1,
        current_average_usage=2.0,
        sample_size=10,
    )
    bom2 = ProcedureMaterialWeight(
        id=2,
        material_id=2,
        weight=0.5,
        tenant_id=1,
        procedure_id=1,
        current_average_usage=0.5,
        sample_size=10,
    )
    async_db_session.add_all([bom1, bom2])
    await async_db_session.commit()

    # Seed Procedure
    proc = Procedure(id=1, name="Composite Filling", price=100.0, tenant_id=1)
    async_db_session.add(proc)
    await async_db_session.commit()

    # Execution
    engine = CostEngine(async_db_session, tenant_id=1)
    result = await engine.calculate_procedure_cost(procedure_id=1)

    if "error" in result:
        raise ValueError(f"Calculation Error: {result['error']}")

    cost = result["total_estimated_cost"]

    # Verification
    print(f"Calculated Cost: ${cost}")
    assert cost == 45.0, f"Expected 45.0, got {cost}"
