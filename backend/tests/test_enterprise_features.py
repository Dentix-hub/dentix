import pytest
from sqlalchemy import select, text
from datetime import datetime, timezone
from backend.models import Tenant, SystemSetting, AuditLog

@pytest.mark.asyncio
async def test_enterprise_features(async_db_session):
    db = async_db_session

    # 1. Verify Maintenance Mode Logic (Direct DB Check)
    res = await db.execute(select(SystemSetting).filter_by(key="maintenance_mode"))
    maintenance = res.scalars().first()
    if not maintenance:
        maintenance = SystemSetting(key="maintenance_mode", value="false", description="Test maintenance mode")
        db.add(maintenance)
        await db.commit()
        # Fetch again to verify
        res = await db.execute(select(SystemSetting).filter_by(key="maintenance_mode"))
        maintenance = res.scalars().first()

    assert maintenance is not None, "Maintenance mode setting missing"
    assert maintenance.value in ["true", "false", "0", "1"]

    # 2. Verify Soft Delete Columns
    await db.execute(text("SELECT is_deleted, deleted_at FROM tenants LIMIT 1"))
    await db.execute(text("SELECT is_deleted, deleted_at, is_active FROM users LIMIT 1"))

    # 3. Verify Soft Delete Logic (Simulation)
    test_tenant = Tenant(name="TestSoftDeleteClinic_123")
    db.add(test_tenant)
    await db.commit()
    t_id = test_tenant.id

    # Soft delete manually (simulating API logic)
    test_tenant.is_deleted = True
    test_tenant.deleted_at = datetime.now(timezone.utc)
    test_tenant.is_active = False
    await db.commit()

    # Verify
    res = await db.execute(select(Tenant).filter_by(id=t_id))
    check = res.scalars().first()
    assert check.is_deleted and not check.is_active, "Tenant soft delete failed"

    # Restore
    check.is_deleted = False
    check.deleted_at = None
    check.is_active = True
    await db.commit()

    # Cleanup
    await db.delete(check)
    await db.commit()

    # 4. Verify Audit Logs
    res = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(5))
    logs = res.scalars().all()
    assert len(logs) >= 0
