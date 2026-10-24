import json
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from backend import models
from backend.main import app
from backend.auth import create_access_token
from backend.services.export_service import export_tenant_to_json, export_tenant_data
from backend.services.import_service import import_tenant_data


@pytest.mark.asyncio
async def test_backup_export_arabic_tenant_name(async_db_session):
    """
    Tenant with Arabic name requesting /backup/export must return 200 with valid ASCII/RFC5987 header.
    Current code puts raw Arabic tenant_name in Content-Disposition filename="...",
    which fails Latin-1 header encoding.
    """
    tenant = models.Tenant(name="عيادة النور لطب الأسنان", subscription_status="active", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    admin = models.User(
        username="arabic_admin",
        email="arabic_admin@example.com",
        role="admin",
        tenant_id=tenant.id,
        hashed_password="hash",
    )
    async_db_session.add(admin)
    await async_db_session.commit()

    token = create_access_token(data={"sub": admin.username, "tenant_id": tenant.id, "role": admin.role})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/settings/backup/export",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    disposition = response.headers.get("content-disposition", "")
    assert disposition != ""
    # Ensure header can be encoded to latin-1 / ascii without error
    disposition.encode("latin-1")
    assert "filename=" in disposition
    assert "filename*=" in disposition


@pytest.mark.asyncio
async def test_backup_export_clinical_charges_decimal_roundtrip(async_db_session):
    """
    Export must serialize clinical_charges (with Decimal amount and discount) to JSON
    and round-trip successfully through import_tenant_data.
    """
    tenant_src = models.Tenant(name="Source Clinic", subscription_status="active", is_active=True)
    async_db_session.add(tenant_src)
    await async_db_session.flush()

    patient = models.Patient(
        name="Test Patient",
        age=30,
        phone="01012345678",
        medical_history="",
        notes="",
        tenant_id=tenant_src.id,
    )
    async_db_session.add(patient)
    await async_db_session.flush()

    work_item = models.ClinicalWorkItem(
        tenant_id=tenant_src.id,
        patient_id=patient.id,
        kind="procedure",
        code="PROC_EXTRACT",
        status="completed",
    )
    async_db_session.add(work_item)
    await async_db_session.flush()

    charge = models.ClinicalCharge(
        tenant_id=tenant_src.id,
        patient_id=patient.id,
        work_item_id=work_item.id,
        amount=Decimal("350.50"),
        discount=Decimal("25.00"),
        status="pending",
    )
    async_db_session.add(charge)
    await async_db_session.commit()

    # Test export to JSON
    json_str = await export_tenant_to_json(async_db_session, tenant_src.id)
    assert isinstance(json_str, str)
    data = json.loads(json_str)

    # Verify serialized charges
    charges_data = data["data"]["clinical_charges"]
    assert len(charges_data) == 1
    assert float(charges_data[0]["amount"]) == 350.50
    assert float(charges_data[0]["discount"]) == 25.00

    # Test import into a new tenant
    tenant_dst = models.Tenant(name="Dest Clinic", subscription_status="active", is_active=True)
    async_db_session.add(tenant_dst)
    await async_db_session.flush()

    stats = await import_tenant_data(async_db_session, tenant_dst.id, data)
    await async_db_session.commit()
    assert stats.get("clinical_charges") == 1

    # Verify the imported charge exists for tenant_dst
    from sqlalchemy import select
    res = await async_db_session.execute(
        select(models.ClinicalCharge).filter(models.ClinicalCharge.tenant_id == tenant_dst.id)
    )
    imported_charges = res.scalars().all()
    assert len(imported_charges) == 1
    assert float(imported_charges[0].amount) == 350.50
    assert float(imported_charges[0].discount) == 25.00
    assert imported_charges[0].status == "pending"
