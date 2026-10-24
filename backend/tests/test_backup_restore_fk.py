import pytest
from sqlalchemy import text, select
from backend import models
from backend.services.import_service import delete_tenant_data, restore_tenant_from_json


@pytest.mark.asyncio
async def test_material_learning_logs_deleted_before_material_sessions_fk(async_db_session):
    """
    Reproduces staging issue:
    Restoring tenant backup or deleting tenant data fails when material_learning_logs
    references material_sessions.id and foreign keys are enforced.
    Must delete material_learning_logs before material_sessions.
    """
    # Enforce foreign keys on SQLite connection
    await async_db_session.execute(text("PRAGMA foreign_keys = ON;"))

    tenant = models.Tenant(name="FK Test Clinic", subscription_status="active", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    warehouse = models.Warehouse(name="Main WH", tenant_id=tenant.id)
    async_db_session.add(warehouse)
    await async_db_session.flush()

    material = models.Material(
        name="Composite Resin",
        type="DIVISIBLE",
        base_unit="g",
        tenant_id=tenant.id,
    )
    async_db_session.add(material)
    await async_db_session.flush()

    from datetime import datetime, timezone

    batch = models.Batch(
        material_id=material.id,
        tenant_id=tenant.id,
        batch_number="B100",
        expiry_date=datetime.now(timezone.utc),
    )
    async_db_session.add(batch)
    await async_db_session.flush()

    stock_item = models.StockItem(
        tenant_id=tenant.id,
        batch_id=batch.id,
        warehouse_id=warehouse.id,
        quantity=10.0,
    )
    async_db_session.add(stock_item)
    await async_db_session.flush()

    material_session = models.MaterialSession(
        tenant_id=tenant.id,
        stock_item_id=stock_item.id,
        status="ACTIVE",
    )
    async_db_session.add(material_session)
    await async_db_session.flush()

    # Create MaterialLearningLog pointing to material_session.id
    from backend.models.inventory import MaterialLearningLog
    learning_log = MaterialLearningLog(
        tenant_id=tenant.id,
        session_id=material_session.id,
        material_id=material.id,
        total_consumed=1.5,
        calculation_data="{}",
    )
    async_db_session.add(learning_log)
    await async_db_session.commit()

    # Now attempt delete_tenant_data with FK enforcement ON
    deleted_counts = await delete_tenant_data(async_db_session, tenant.id)
    await async_db_session.commit()

    assert deleted_counts.get("material_learning_logs", 0) >= 1
    assert deleted_counts.get("material_sessions", 0) >= 1

    # Verify rows are deleted
    remaining_logs = await async_db_session.execute(
        select(MaterialLearningLog).where(MaterialLearningLog.tenant_id == tenant.id)
    )
    assert len(remaining_logs.scalars().all()) == 0


@pytest.mark.asyncio
async def test_upload_backup_sanitizes_db_errors_in_response(async_db_session, monkeypatch):
    """
    When backup restore fails due to internal errors or database exceptions,
    the endpoint must return 400 with a safe Arabic message and NOT leak raw SQL / FK constraint names.
    """
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.auth import create_access_token

    tenant = models.Tenant(name="Sanitize Test Clinic", subscription_status="active", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    admin = models.User(
        username="sanitize_admin",
        email="sanitize_admin@example.com",
        role="admin",
        tenant_id=tenant.id,
        hashed_password="hash",
    )
    async_db_session.add(admin)
    await async_db_session.commit()

    token = create_access_token(data={"sub": admin.username, "tenant_id": tenant.id, "role": admin.role})

    # Simulate an internal DB error leaking constraint details
    async def mock_restore_fail(*args, **kwargs):
        return {
            "success": False,
            "error": 'update or delete on table "material_sessions" violates foreign key constraint "material_learning_logs_session_id_fkey" on table "material_learning_logs"',
        }

    from backend.routers import settings as settings_module
    monkeypatch.setattr(settings_module, "restore_tenant_from_json", mock_restore_fail)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        files = {"file": ("backup.json", b'{"version":"1.0","tenant_id":1,"data":{}}', "application/json")}
        resp = await ac.post(
            "/api/v1/settings/backup/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 400
    data = resp.json()
    detail = data.get("detail", "")
    assert "material_learning_logs" not in detail
    assert "foreign key" not in detail.lower()
    assert "تعذرت استعادة النسخة الاحتياطية" in detail


@pytest.mark.asyncio
async def test_failed_restore_leaves_existing_data_unchanged(async_db_session, monkeypatch):
    """
    Verify that if a restore fails midway (e.g. during import_tenant_data after deletion),
    the session is cleanly rolled back and all existing tenant data remains intact.
    """
    from datetime import date
    import json
    from backend.services import import_service

    tenant = models.Tenant(name="Rollback Test Clinic", subscription_status="active", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    patient = models.Patient(
        name="Pre-existing Patient",
        phone="01099999999",
        age=30,
        medical_history="None",
        notes="Important notes",
        tenant_id=tenant.id,
    )
    async_db_session.add(patient)
    await async_db_session.commit()

    # Verify patient exists
    check_stmt = select(models.Patient).where(models.Patient.tenant_id == tenant.id)
    pts_before = (await async_db_session.execute(check_stmt)).scalars().all()
    assert len(pts_before) == 1
    assert pts_before[0].name == "Pre-existing Patient"

    # Mock import_tenant_data to simulate a failure halfway through restore
    async def mock_import_fail(*args, **kwargs):
        raise RuntimeError("Simulated corruption or DB failure during import")

    monkeypatch.setattr(import_service, "import_tenant_data", mock_import_fail)

    # Valid backup structure to pass initial validation
    backup_payload = json.dumps({
        "version": "1.0",
        "tenant_id": tenant.id,
        "exported_at": "2026-10-24T00:00:00Z",
        "data": {
            "patients": [{"name": "New Patient", "phone": "01011111111"}]
        }
    })

    result = await restore_tenant_from_json(async_db_session, tenant.id, backup_payload)
    assert result["success"] is False
    assert result["error"] == "تعذرت استعادة النسخة الاحتياطية. لم يتم تغيير بياناتك."

    # Verify existing patient was preserved by the transaction rollback
    pts_after = (await async_db_session.execute(check_stmt)).scalars().all()
    assert len(pts_after) == 1
    assert pts_after[0].name == "Pre-existing Patient"

