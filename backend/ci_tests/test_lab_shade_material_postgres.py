"""Real PostgreSQL test for Lab Order shade/material sync with joined FDI tooth numbers (F-13).

Proves:
1. Lab order with joined tooth numbers (e.g. "16, 17") splits into valid FDI keys and does NOT violate ck_co_tooth_key_fdi on commit.
2. Each valid tooth receives its own observation for shade and material.
3. Invalid tooth keys are skipped and do NOT cause a 500 error or check constraint violation.
"""

import pytest
from sqlalchemy import select

from backend import models
from backend.clinical.shade_material_sync import (
    sync_lab_order_to_active_care_session_observations,
)
from backend.database import AsyncSessionLocal, RlsContext

TENANT_ID = 99710
USER_ID = 997101
PATIENT_ID = 997102
LAB_ID = 997103


async def _seed() -> None:
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            if await db.get(models.Tenant, TENANT_ID) is not None:
                return

            tenant = models.Tenant(id=TENANT_ID, name="Shade Sync Postgres Tenant")
            db.add(tenant)
            await db.flush()

            doctor = models.User(
                id=USER_ID,
                tenant_id=TENANT_ID,
                username="shade_sync_doctor",
                email="shade_sync_doctor@example.com",
                hashed_password="fakepassword",
                role="doctor",
                is_active=True,
            )
            db.add(doctor)
            await db.flush()

            patient = models.Patient(
                id=PATIENT_ID,
                tenant_id=TENANT_ID,
                name="Shade Sync Patient",
                age=35,
                phone="01099710001",
                medical_history="",
                notes="",
            )
            db.add(patient)

            lab = models.Laboratory(
                id=LAB_ID,
                tenant_id=TENANT_ID,
                name="Postgres Lab",
                phone="01099710002",
            )
            db.add(lab)
            await db.commit()


@pytest.mark.asyncio
async def test_lab_order_joined_tooth_numbers_shade_sync_postgres():
    await _seed()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
        # Create active care session and work item
        care_session = models.CareSession(
            tenant_id=TENANT_ID,
            patient_id=PATIENT_ID,
            provider_user_id=USER_ID,
            status="in_progress",
        )
        session.add(care_session)

        work_item = models.ClinicalWorkItem(
            tenant_id=TENANT_ID,
            patient_id=PATIENT_ID,
            kind="procedure",
            code="CROWN_BRIDGE",
            status="active",
            created_by_user_id=USER_ID,
        )
        session.add(work_item)
        await session.flush()

        order = models.LabOrder(
            tenant_id=TENANT_ID,
            patient_id=PATIENT_ID,
            doctor_id=USER_ID,
            laboratory_id=LAB_ID,
            work_item_id=work_item.id,
            work_type="Bridge",
            tooth_number="16, 17",
            shade="A2",
            material="Zirconia",
            status="pending",
        )
        session.add(order)
        await session.flush()

        # Call shade/material sync
        synced_obs = await sync_lab_order_to_active_care_session_observations(
            db=session,
            tenant_id=TENANT_ID,
            order=order,
            actor_user_id=USER_ID,
        )
        assert len(synced_obs) == 4

        # On current unpatched code, tooth_key is set to "16, 17" on the observation.
        # When committing to PostgreSQL, this violates ck_co_tooth_key_fdi.
        await session.commit()

        # Assert observations were created per tooth key
        obs_stmt = (
            select(models.CareObservation)
            .where(
                models.CareObservation.tenant_id == TENANT_ID,
                models.CareObservation.work_item_id == work_item.id,
            )
            .order_by(models.CareObservation.tooth_key, models.CareObservation.observation_code)
        )
        obs_rows = (await session.execute(obs_stmt)).scalars().all()
        assert len(obs_rows) == 4

        teeth = {obs.tooth_key for obs in obs_rows}
        assert teeth == {"16", "17"}


@pytest.mark.asyncio
async def test_lab_order_invalid_and_mixed_tooth_numbers_postgres():
    await _seed()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
        care_session = models.CareSession(
            tenant_id=TENANT_ID,
            patient_id=PATIENT_ID,
            provider_user_id=USER_ID,
            status="in_progress",
        )
        session.add(care_session)

        work_item = models.ClinicalWorkItem(
            tenant_id=TENANT_ID,
            patient_id=PATIENT_ID,
            kind="procedure",
            code="CROWN_BRIDGE",
            status="active",
            created_by_user_id=USER_ID,
        )
        session.add(work_item)
        await session.flush()

        # Mixed valid and invalid tooth keys ("21, invalid, 22")
        order = models.LabOrder(
            tenant_id=TENANT_ID,
            patient_id=PATIENT_ID,
            doctor_id=USER_ID,
            laboratory_id=LAB_ID,
            work_item_id=work_item.id,
            work_type="Crown",
            tooth_number="21, invalid, 22",
            shade="B1",
            material="Porcelain",
            status="pending",
        )
        session.add(order)
        await session.flush()

        synced_obs = await sync_lab_order_to_active_care_session_observations(
            db=session,
            tenant_id=TENANT_ID,
            order=order,
            actor_user_id=USER_ID,
        )
        await session.commit()

        teeth = {obs.tooth_key for obs in synced_obs}
        assert teeth == {"21", "22"}
