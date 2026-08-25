import pytest
from sqlalchemy import select
from datetime import datetime, timezone
from backend.services.patient_service import PatientService
from backend import models
from backend.database import Base


@pytest.fixture(autouse=True)
async def setup_tables(async_engine_fixture):
    async with async_engine_fixture.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.anyio
async def test_service_fixes(async_db_session):
    tenant_id = 1

    # Ensure Tenant exists
    tenant_stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
    tenant = (await async_db_session.execute(tenant_stmt)).scalar_one_or_none()
    if not tenant:
        tenant = models.Tenant(id=tenant_id, name="Test Tenant", plan="trial")
        async_db_session.add(tenant)
        await async_db_session.commit()

    # Doctor needed for treatment
    doctor_stmt = select(models.User).where(models.User.role == "doctor")
    doctor = (await async_db_session.execute(doctor_stmt)).scalars().first()
    if not doctor:
        doctor = models.User(
            username="test_svc_doc",
            email="test_svc_doc@example.com",
            role="doctor",
            tenant_id=tenant_id,
            hashed_password="pw"
        )
        async_db_session.add(doctor)
        await async_db_session.commit()
        await async_db_session.refresh(doctor)

    # Patient
    patient_stmt = select(models.Patient).where(models.Patient.name == "ServiceTest Patient")
    p = (await async_db_session.execute(patient_stmt)).scalar_one_or_none()
    if not p:
        p = models.Patient(
            tenant_id=tenant_id,
            name="ServiceTest Patient",
            phone="0123456789",
            age=30,
            medical_history="",
            notes=""
        )
        async_db_session.add(p)
        await async_db_session.commit()
        await async_db_session.refresh(p)

        # Treatment for balance
        t = models.Treatment(
            patient_id=p.id,
            procedure="Test Procedure",
            cost=500.0,
            date=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            doctor_id=doctor.id
        )
        async_db_session.add(t)
        await async_db_session.commit()

    service = PatientService(async_db_session, tenant_id=tenant_id)

    # 1. File Details
    details = await service.get_patient_file_details("ServiceTest Patient")
    assert details["found"] is True
    assert details["patient"].name == "ServiceTest Patient"

    # 2. Search
    results = await service.search_patients_by_name("ServiceTest")
    assert len(results) >= 1

    # 3. Balance
    debtors = await service.get_patients_with_balance()
    names = [d["name"] for d in debtors]
    assert "ServiceTest Patient" in names

    # 4. Summary
    summary = await service.get_patient_summary_data("ServiceTest Patient")
    assert summary["found"] is True
    assert "summary_data" in summary
