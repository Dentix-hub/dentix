"""
Tests for Phase P09: Multi-Tenant Direct Scoping & RLS Isolation Verification.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend import models


@pytest.mark.asyncio
async def test_sensitive_models_direct_tenant_scoping(async_db_session: AsyncSession):
    # 1. Create two separate tenants
    t1 = models.Tenant(name="Clinic Alpha", is_active=True, subscription_status="active")
    t2 = models.Tenant(name="Clinic Beta", is_active=True, subscription_status="active")
    async_db_session.add_all([t1, t2])
    await async_db_session.commit()
    await async_db_session.refresh(t1)
    await async_db_session.refresh(t2)

    # 2. Create Patients
    p1 = models.Patient(name="Patient Alpha", age=30, phone="01011111111", medical_history="", notes="", tenant_id=t1.id)
    p2 = models.Patient(name="Patient Beta", age=25, phone="01022222222", medical_history="", notes="", tenant_id=t2.id)
    async_db_session.add_all([p1, p2])
    await async_db_session.commit()
    await async_db_session.refresh(p1)
    await async_db_session.refresh(p2)

    # 3. Create ToothStatus for both
    ts1 = models.ToothStatus(patient_id=p1.id, tooth_number=11, condition="Caries", tenant_id=t1.id)
    ts2 = models.ToothStatus(patient_id=p2.id, tooth_number=21, condition="Crown", tenant_id=t2.id)

    # 4. Create Prescription for both
    rx1 = models.Prescription(patient_id=p1.id, medications="Amoxicillin 500mg", tenant_id=t1.id)
    rx2 = models.Prescription(patient_id=p2.id, medications="Ibuprofen 400mg", tenant_id=t2.id)

    # 5. Create Attachment for both
    att1 = models.Attachment(
        patient_id=p1.id,
        file_path="/uploads/t1/xray1.png",
        filename="xray1.png",
        file_type="image/png",
        tenant_id=t1.id,
    )
    att2 = models.Attachment(
        patient_id=p2.id,
        file_path="/uploads/t2/xray2.png",
        filename="xray2.png",
        file_type="image/png",
        tenant_id=t2.id,
    )

    async_db_session.add_all([ts1, ts2, rx1, rx2, att1, att2])
    await async_db_session.commit()

    # 6. Verify Tenant 1 query isolates only Tenant 1 data
    t1_tooth_res = await async_db_session.execute(
        select(models.ToothStatus).where(models.ToothStatus.tenant_id == t1.id)
    )
    t1_teeth = t1_tooth_res.scalars().all()
    assert len(t1_teeth) == 1
    assert t1_teeth[0].tooth_number == 11

    t1_rx_res = await async_db_session.execute(
        select(models.Prescription).where(models.Prescription.tenant_id == t1.id)
    )
    t1_rxs = t1_rx_res.scalars().all()
    assert len(t1_rxs) == 1
    assert "Amoxicillin" in t1_rxs[0].medications

    t1_att_res = await async_db_session.execute(
        select(models.Attachment).where(models.Attachment.tenant_id == t1.id)
    )
    t1_atts = t1_att_res.scalars().all()
    assert len(t1_atts) == 1
    assert t1_atts[0].filename == "xray1.png"

    # 7. Verify Tenant 2 query isolates only Tenant 2 data
    t2_tooth_res = await async_db_session.execute(
        select(models.ToothStatus).where(models.ToothStatus.tenant_id == t2.id)
    )
    t2_teeth = t2_tooth_res.scalars().all()
    assert len(t2_teeth) == 1
    assert t2_teeth[0].tooth_number == 21
