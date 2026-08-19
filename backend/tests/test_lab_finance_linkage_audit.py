"""Finance regressions for LabOrder -> Treatment linkage."""

from datetime import datetime

import pytest
from sqlalchemy import select

from backend import models, schemas
from backend.services.lab_service import LabService, TREATMENT_LINK_PREFIX


@pytest.mark.asyncio
async def test_lab_order_creates_exact_tenant_owned_billable_treatment(async_db_session):
    tenant_id = 166
    doctor = models.User(
        id=1661,
        username="lab_link_doctor",
        email="lab-link-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=tenant_id,
    )
    patient = models.Patient(
        id=1662,
        name="Lab Link Patient",
        age=37,
        phone="01016601660",
        medical_history="None",
        notes="Lab linkage audit fixture",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    laboratory = models.Laboratory(
        id=1663,
        name="Lab Link Audit",
        tenant_id=tenant_id,
    )
    async_db_session.add_all([doctor, patient, laboratory])
    await async_db_session.commit()

    service = LabService(async_db_session, tenant_id)
    order = await service.create_lab_order(
        schemas.LabOrderCreate(
            patient_id=patient.id,
            laboratory_id=laboratory.id,
            work_type="Crown",
            cost=350.0,
            price_to_patient=900.0,
        ),
        doctor_id=doctor.id,
    )

    treatment = (
        await async_db_session.execute(
            select(models.Treatment).where(
                models.Treatment.notes == f"{TREATMENT_LINK_PREFIX}{order.id}"
            )
        )
    ).scalar_one()
    assert treatment.tenant_id == tenant_id
    assert treatment.patient_id == patient.id
    assert treatment.doctor_id == doctor.id
    assert treatment.cost == 900.0


@pytest.mark.asyncio
async def test_lab_delete_never_matches_another_orders_link_marker(async_db_session):
    tenant_id = 167
    patient = models.Patient(
        id=1671,
        name="Exact Link Patient",
        age=41,
        phone="01016701670",
        medical_history="None",
        notes="Exact lab link deletion fixture",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    laboratory = models.Laboratory(id=1672, name="Exact Link Lab", tenant_id=tenant_id)
    order_one = models.LabOrder(
        id=1,
        patient_id=patient.id,
        laboratory_id=laboratory.id,
        work_type="Crown",
        cost=100.0,
        order_date=datetime(2026, 8, 18, 10, 0),
        tenant_id=tenant_id,
    )
    order_ten = models.LabOrder(
        id=10,
        patient_id=patient.id,
        laboratory_id=laboratory.id,
        work_type="Bridge",
        cost=200.0,
        order_date=datetime(2026, 8, 18, 11, 0),
        tenant_id=tenant_id,
    )
    treatment_one = models.Treatment(
        id=1673,
        patient_id=patient.id,
        diagnosis="A",
        procedure="Order 1",
        cost=100.0,
        date=datetime(2026, 8, 18, 10, 0),
        notes=f"{TREATMENT_LINK_PREFIX}1",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    treatment_ten = models.Treatment(
        id=1674,
        patient_id=patient.id,
        diagnosis="B",
        procedure="Order 10",
        cost=200.0,
        date=datetime(2026, 8, 18, 11, 0),
        notes=f"{TREATMENT_LINK_PREFIX}10",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    async_db_session.add_all(
        [patient, laboratory, order_one, order_ten, treatment_one, treatment_ten]
    )
    await async_db_session.commit()

    await LabService(async_db_session, tenant_id).delete_lab_order(order_one.id)

    remaining = (
        await async_db_session.execute(
            select(models.Treatment).where(models.Treatment.id == treatment_ten.id)
        )
    ).scalar_one_or_none()
    assert remaining is not None
    assert remaining.notes == f"{TREATMENT_LINK_PREFIX}10"
