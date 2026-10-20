"""
Real PostgreSQL concurrency gate for U2:
Treatment Plan Item Linking on Create and Concurrency Row Locks.

Proves:
1. Two concurrent requests attempting to link the same ClinicalWorkItem
   yield exactly one winner (success) and one HTTP 409 rejection
   (CLINICAL_LINK_ALREADY_LINKED / CLINICAL_LINK_NOT_OPEN / CLINICAL_LINK_CONFLICT).
2. No unhandled DBAPIError, IntegrityError, or deadlocks occur under PostgreSQL row-locking.
3. Database invariants hold: exactly 1 linked Treatment, exactly 1 completion ClinicalEvent,
   work item status is 'completed', and work item count is unchanged.
"""

import asyncio
from fastapi import HTTPException
import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend import models, schemas
from backend.clinical.catalog import ProcedureCode
from backend.database import AsyncSessionLocal, RlsContext
from backend.services.feature_service import FeatureFlagService
from backend.services.treatment_service import TreatmentService

TENANT_U2 = 99721
USER_U2_ID = 997210
PATIENT_U2_ID = 997211
PROC_NAME = "حشو كومبوزيت -- Composite Filling Class I"


async def _seed() -> None:
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            if await db.get(models.Tenant, TENANT_U2) is None:
                tenant = models.Tenant(
                    id=TENANT_U2,
                    name="U2 Concurrency Postgres Tenant",
                    is_active=True,
                )
                db.add(tenant)
                await db.flush()

                user = models.User(
                    id=USER_U2_ID,
                    tenant_id=TENANT_U2,
                    username="concurrency_user_u2",
                    email="concurrency_u2@example.com",
                    hashed_password="fakepassword",
                    role="admin",
                    is_active=True,
                )
                db.add(user)
                await db.flush()

                patient = models.Patient(
                    id=PATIENT_U2_ID,
                    tenant_id=TENANT_U2,
                    name="Patient Concurrency U2",
                    age=30,
                    phone="01099721001",
                    medical_history="",
                    notes="",
                )
                db.add(patient)
                await db.flush()

            # Ensure shadow feature flag exists and is enabled for tenant
            stmt_flag = select(models.FeatureFlag).where(
                models.FeatureFlag.key == "clinical_vnext_shadow"
            )
            flag = (await db.execute(stmt_flag)).scalar_one_or_none()
            if not flag:
                flag = models.FeatureFlag(
                    key="clinical_vnext_shadow",
                    description="Clinical vNext Shadow Mode",
                    is_global_enabled=True,
                    rollout_percentage=100,
                )
                db.add(flag)
                await db.flush()
            else:
                flag.is_global_enabled = True
                flag.rollout_percentage = 100

            await FeatureFlagService.set_tenant_override(
                db, TENANT_U2, "clinical_vnext_shadow", True
            )

            # Ensure tenant has procedure seeded for pricing
            stmt_proc = select(models.Procedure).where(
                models.Procedure.tenant_id == TENANT_U2,
                models.Procedure.name == PROC_NAME,
            )
            existing_proc = (await db.execute(stmt_proc)).scalar_one_or_none()
            if not existing_proc:
                db.add(
                    models.Procedure(
                        tenant_id=TENANT_U2,
                        name=PROC_NAME,
                        price=650.0,
                    )
                )
            await db.commit()


@pytest.mark.asyncio
async def test_u2_postgres_concurrent_treatment_link():
    """
    Two concurrent create_treatment calls referencing the identical clinical_work_item_id:
    - Row-level lock (with_for_update) & duplicate check serialize requests.
    - Exactly 1 succeeds.
    - Exactly 1 fails with HTTP 409.
    - No unhandled exceptions.
    - Postconditions: 1 treatment, work item completed, 1 event with linked_existing_work_item: True.
    """
    await _seed()
    user = models.User(id=USER_U2_ID, tenant_id=TENANT_U2, role="admin", is_active=True)

    # 1. Create planned work item (Tooth 16, Surface O, REST_COMPOSITE)
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_U2)) as session:
        wi = models.ClinicalWorkItem(
            tenant_id=TENANT_U2,
            patient_id=PATIENT_U2_ID,
            kind="procedure",
            code=ProcedureCode.REST_COMPOSITE.value,
            status="planned",
        )
        session.add(wi)
        await session.flush()

        target = models.ClinicalWorkItemTarget(
            tenant_id=TENANT_U2,
            work_item_id=wi.id,
            target_kind="surface",
            tooth_key="16",
            surface_code="O",
        )
        session.add(target)
        work_item_id = wi.id
        await session.commit()

        wi_count_before = (
            await session.execute(
                select(func.count(models.ClinicalWorkItem.id)).where(
                    models.ClinicalWorkItem.tenant_id == TENANT_U2
                )
            )
        ).scalar()

    # 2. Define concurrent worker
    async def worker(worker_id: int):
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_U2)) as session:
            service = TreatmentService(session, TENANT_U2, user)
            treatment_data = schemas.TreatmentCreate(
                patient_id=PATIENT_U2_ID,
                procedure=PROC_NAME,
                cost=650.0,
                discount=0.0,
                tooth_number=16,
                surface="O",
                surfaces=["O"],
                status="Done",
                clinical_work_item_id=work_item_id,
            )
            return await service.create_treatment(treatment_data)

    # 3. Fire 2 workers concurrently
    results = await asyncio.gather(worker(1), worker(2), return_exceptions=True)

    successes = [r for r in results if isinstance(r, models.Treatment)]
    failures = [r for r in results if isinstance(r, Exception)]

    # Assert exactly 1 winner and 1 failure
    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got {len(failures)}: {results}"

    failure = failures[0]
    assert not isinstance(failure, (IntegrityError, DBAPIError)), f"Unhandled DB exception: {failure}"
    assert isinstance(failure, HTTPException), f"Expected HTTPException, got {type(failure)}: {failure}"
    assert failure.status_code == 409, f"Expected 409 conflict, got {failure.status_code}: {failure.detail}"
    assert failure.detail in (
        "CLINICAL_LINK_ALREADY_LINKED",
        "CLINICAL_LINK_NOT_OPEN",
        "CLINICAL_LINK_CONFLICT",
    )

    # 4. Verify DB invariants
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_U2)) as session:
        # Work item count unchanged
        wi_count_after = (
            await session.execute(
                select(func.count(models.ClinicalWorkItem.id)).where(
                    models.ClinicalWorkItem.tenant_id == TENANT_U2
                )
            )
        ).scalar()
        assert wi_count_after == wi_count_before

        # Work item is completed
        wi_db = (
            await session.execute(
                select(models.ClinicalWorkItem).where(
                    models.ClinicalWorkItem.id == work_item_id,
                    models.ClinicalWorkItem.tenant_id == TENANT_U2,
                )
            )
        ).scalar_one()
        assert wi_db.status == "completed"

        # Exactly 1 event linked to work item
        events = (
            await session.execute(
                select(models.ClinicalEvent).where(
                    models.ClinicalEvent.work_item_id == work_item_id,
                    models.ClinicalEvent.tenant_id == TENANT_U2,
                    models.ClinicalEvent.event_type == "procedure_recorded",
                )
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].payload.get("linked_existing_work_item") is True
        assert events[0].payload.get("treatment_id") == successes[0].id
