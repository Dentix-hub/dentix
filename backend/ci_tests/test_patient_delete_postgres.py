"""Real PostgreSQL test for patient and tenant clinical deletion with chairside TreatmentMaterialUsage (F-08).

Proves:
1. Deleting a patient with chairside TreatmentMaterialUsage (treatment_id IS NULL, care_session_id / work_item_id set)
   does NOT violate ck_tmu_treatment_or_care_session_required check constraint on PostgreSQL.
2. Deleting tenant clinical rows with chairside TreatmentMaterialUsage succeeds without constraint violation.
"""

import pytest
from sqlalchemy import select

from backend import models
from backend.crud.patient import delete_patient_permanently, delete_tenant_clinical_rows
from backend.database import AsyncSessionLocal, RlsContext

TENANT_ID = 99720
USER_ID = 997201
PATIENT_ID = 997202
WAREHOUSE_ID = 997203
MATERIAL_ID = 997204


async def _seed() -> None:
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            if await db.get(models.Tenant, TENANT_ID) is not None:
                return

            tenant = models.Tenant(id=TENANT_ID, name="Patient Delete Postgres Tenant")
            db.add(tenant)
            await db.flush()

            doctor = models.User(
                id=USER_ID,
                tenant_id=TENANT_ID,
                username="patient_delete_doctor",
                email="patient_delete_doctor@example.com",
                hashed_password="fakepassword",
                role="admin",
                is_active=True,
            )
            db.add(doctor)
            await db.flush()

            patient = models.Patient(
                id=PATIENT_ID,
                tenant_id=TENANT_ID,
                name="Patient Delete Patient",
                age=40,
                phone="01099720001",
                medical_history="",
                notes="",
            )
            db.add(patient)

            wh = models.Warehouse(
                id=WAREHOUSE_ID,
                tenant_id=TENANT_ID,
                name="Main Clinic Storage",
            )
            db.add(wh)
            await db.flush()

            mat = models.Material(
                id=MATERIAL_ID,
                tenant_id=TENANT_ID,
                name="Composite Resin",
                type="DIVISIBLE",
                base_unit="g",
                standard_price=150.0,
            )
            db.add(mat)
            await db.commit()


@pytest.mark.asyncio
async def test_patient_permanent_delete_with_chairside_material_usage_postgres():
    await _seed()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
        care_session = models.CareSession(
            tenant_id=TENANT_ID,
            patient_id=PATIENT_ID,
            provider_user_id=USER_ID,
            status="completed",
        )
        session.add(care_session)

        work_item = models.ClinicalWorkItem(
            tenant_id=TENANT_ID,
            patient_id=PATIENT_ID,
            kind="procedure",
            code="COMPOSITE_RESTORATION",
            status="completed",
            created_by_user_id=USER_ID,
        )
        session.add(work_item)
        await session.flush()

        # Chairside material usage: treatment_id is NULL, care_session_id is set
        tmu = models.TreatmentMaterialUsage(
            tenant_id=TENANT_ID,
            treatment_id=None,
            care_session_id=care_session.id,
            work_item_id=work_item.id,
            material_id=MATERIAL_ID,
            quantity_used=1.0,
        )
        session.add(tmu)
        await session.commit()

        # On unpatched code, delete_patient_permanently deletes CareSession.
        # Postgres SET NULL fires on care_session_id, leaving both treatment_id
        # and care_session_id NULL, violating ck_tmu_treatment_or_care_session_required.
        await delete_patient_permanently(session, patient_id=PATIENT_ID, tenant_id=TENANT_ID)

        # Verify patient and chairside usage are deleted
        patient_row = (
            await session.execute(
                select(models.Patient).where(
                    models.Patient.id == PATIENT_ID,
                    models.Patient.tenant_id == TENANT_ID,
                )
            )
        ).scalar_one_or_none()
        assert patient_row is None

        usage_row = (
            await session.execute(
                select(models.TreatmentMaterialUsage).where(
                    models.TreatmentMaterialUsage.id == tmu.id
                )
            )
        ).scalar_one_or_none()
        assert usage_row is None


@pytest.mark.asyncio
async def test_tenant_clinical_rows_delete_with_chairside_material_usage_postgres():
    await _seed()

    TENANT_CLEAN = 99725
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            tenant = models.Tenant(id=TENANT_CLEAN, name="Tenant Clean Delete")
            db.add(tenant)
            await db.flush()

            patient = models.Patient(
                id=997251,
                tenant_id=TENANT_CLEAN,
                name="Patient Clean",
                age=25,
                phone="01099725001",
                medical_history="",
                notes="",
            )
            db.add(patient)
            wh = models.Warehouse(
                id=997252,
                tenant_id=TENANT_CLEAN,
                name="Clean Storage",
            )
            db.add(wh)
            await db.flush()
            mat = models.Material(
                id=997253,
                tenant_id=TENANT_CLEAN,
                name="Clean Mat",
                type="DIVISIBLE",
                base_unit="g",
                standard_price=50.0,
            )
            db.add(mat)
            await db.commit()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_CLEAN)) as session:
        care_session = models.CareSession(
            tenant_id=TENANT_CLEAN,
            patient_id=997251,
            status="completed",
        )
        session.add(care_session)
        work_item = models.ClinicalWorkItem(
            tenant_id=TENANT_CLEAN,
            patient_id=997251,
            kind="procedure",
            code="CLEAN_PROC",
            status="completed",
        )
        session.add(work_item)
        await session.flush()

        tmu = models.TreatmentMaterialUsage(
            tenant_id=TENANT_CLEAN,
            treatment_id=None,
            care_session_id=care_session.id,
            work_item_id=work_item.id,
            material_id=997253,
            quantity_used=1.0,
        )
        session.add(tmu)
        await session.commit()

        counts = await delete_tenant_clinical_rows(session, tenant_id=TENANT_CLEAN)
        await session.commit()
        assert counts.get("treatment_material_usages", 0) >= 1
