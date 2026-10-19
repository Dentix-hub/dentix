"""Real PostgreSQL concurrency and tenant isolation gate for clinical commands and treatment plans.

Proves:
1. Same idempotency key + same payload across 8 concurrent workers -> exactly 1 work item & 1 event, same work_item.id returned, no unhandled exceptions.
2. Same idempotency key + different payloads concurrently -> exactly 1 winner, others raise HTTP 409, exactly 1 work item in DB.
3. Tenant isolation of idempotency keys -> same key used in tenant B is independent and isolated from tenant A.
4. Treatment plans concurrency -> 4 concurrent add_phase yield distinct contiguous phase_orders (0..N); 2 concurrent add_work_item_to_phase for same item yield 1 success and 1 HTTP 409.
"""

import asyncio
from typing import List

from fastapi import HTTPException
import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend import models, schemas
from backend.database import AsyncSessionLocal, RlsContext
from backend.services.clinical_command_service import ClinicalCommandService
from backend.services.clinical_workspace_service import (
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
)
from backend.services.feature_service import FeatureFlagService
from backend.services.treatment_plan_service import (
    FEATURE_KEY_TREATMENT_PLANS,
    TreatmentPlanService,
)

TENANT_A = 99591
TENANT_B = 99592
USER_A_ID = 995910
USER_B_ID = 995920
PATIENT_A_ID = 995911
PATIENT_B_ID = 995921


async def _seed() -> None:
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            if await db.get(models.Tenant, TENANT_A) is not None:
                return

            tenant_a = models.Tenant(id=TENANT_A, name="Concurrency Postgres Tenant A")
            tenant_b = models.Tenant(id=TENANT_B, name="Concurrency Postgres Tenant B")
            db.add_all([tenant_a, tenant_b])
            await db.flush()

            user_a = models.User(
                id=USER_A_ID,
                tenant_id=TENANT_A,
                username="concurrency_user_a",
                email="concurrency_a_9959@example.com",
                hashed_password="fakepassword",
                role="admin",
                is_active=True,
            )
            user_b = models.User(
                id=USER_B_ID,
                tenant_id=TENANT_B,
                username="concurrency_user_b",
                email="concurrency_b_9959@example.com",
                hashed_password="fakepassword",
                role="admin",
                is_active=True,
            )
            db.add_all([user_a, user_b])
            await db.flush()

            patient_a = models.Patient(
                id=PATIENT_A_ID,
                tenant_id=TENANT_A,
                name="Patient Concurrency A",
                age=30,
                phone="01099591001",
                medical_history="",
                notes="",
            )
            patient_b = models.Patient(
                id=PATIENT_B_ID,
                tenant_id=TENANT_B,
                name="Patient Concurrency B",
                age=32,
                phone="01099592001",
                medical_history="",
                notes="",
            )
            db.add_all([patient_a, patient_b])
            await db.flush()

            # Ensure native writes feature flag exists and is globally enabled
            stmt_nw = select(models.FeatureFlag).where(
                models.FeatureFlag.key == FEATURE_FLAG_CLINICAL_NATIVE_WRITES
            )
            flag_nw = (await db.execute(stmt_nw)).scalar_one_or_none()
            if not flag_nw:
                flag_nw = models.FeatureFlag(
                    key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
                    description="Clinical native writes",
                    is_global_enabled=True,
                    rollout_percentage=100,
                )
                db.add(flag_nw)
                await db.flush()
            else:
                flag_nw.is_global_enabled = True
                flag_nw.rollout_percentage = 100

            await FeatureFlagService.set_tenant_override(
                db, TENANT_A, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True
            )
            await FeatureFlagService.set_tenant_override(
                db, TENANT_B, FEATURE_FLAG_CLINICAL_NATIVE_WRITES, True
            )

            # Ensure treatment plans feature flag exists and is globally enabled
            stmt_tp = select(models.FeatureFlag).where(
                models.FeatureFlag.key == FEATURE_KEY_TREATMENT_PLANS
            )
            flag_tp = (await db.execute(stmt_tp)).scalar_one_or_none()
            if not flag_tp:
                flag_tp = models.FeatureFlag(
                    key=FEATURE_KEY_TREATMENT_PLANS,
                    description="Treatment plans",
                    is_global_enabled=True,
                    rollout_percentage=100,
                )
                db.add(flag_tp)
                await db.flush()
            else:
                flag_tp.is_global_enabled = True
                flag_tp.rollout_percentage = 100

            await FeatureFlagService.set_tenant_override(
                db, TENANT_A, FEATURE_KEY_TREATMENT_PLANS, True
            )
            await FeatureFlagService.set_tenant_override(
                db, TENANT_B, FEATURE_KEY_TREATMENT_PLANS, True
            )

            await db.commit()


@pytest.mark.asyncio
async def test_idempotency_same_key_same_payload_concurrent_gather(monkeypatch):
    """Scenario 1: Same key, same payload, N=8 workers -> exactly 1 work item & 1 event, same id, no errors."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    await _seed()
    user_a = models.User(id=USER_A_ID, tenant_id=TENANT_A, role="admin", is_active=True)
    key = "idem-same-payload-key-1"
    payload = schemas.ClinicalWorkItemCreate(
        kind="procedure",
        code="REST_COMPOSITE",
        status="planned",
        notes="Same payload concurrent test",
    )

    async def worker():
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
            service = ClinicalCommandService(session, TENANT_A, user_a)
            return await service.create_work_item(PATIENT_A_ID, payload, idempotency_key=key)

    results = await asyncio.gather(*[worker() for _ in range(8)])
    work_item_ids = [wi.id for wi in results]
    assert len(set(work_item_ids)) == 1, f"Expected all workers to return identical work_item.id, got {work_item_ids}"
    single_id = work_item_ids[0]

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
        items = (
            await session.execute(
                select(models.ClinicalWorkItem).where(
                    models.ClinicalWorkItem.tenant_id == TENANT_A,
                    models.ClinicalWorkItem.patient_id == PATIENT_A_ID,
                    models.ClinicalWorkItem.id == single_id,
                )
            )
        ).scalars().all()
        assert len(items) == 1

        events = (
            await session.execute(
                select(models.ClinicalEvent).where(
                    models.ClinicalEvent.tenant_id == TENANT_A,
                    models.ClinicalEvent.patient_id == PATIENT_A_ID,
                )
            )
        ).scalars().all()
        matching_events = [
            e for e in events
            if isinstance(e.payload, dict) and e.payload.get("idempotency_key") == key
        ]
        assert len(matching_events) == 1
        assert matching_events[0].work_item_id == single_id


@pytest.mark.asyncio
async def test_idempotency_same_key_different_payload_concurrent_gather(monkeypatch):
    """Scenario 2: Same key, different payload, concurrently -> exactly one wins, others raise 409, 1 work item in DB."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    await _seed()
    user_a = models.User(id=USER_A_ID, tenant_id=TENANT_A, role="admin", is_active=True)
    key = "idem-diff-payload-key-2"

    async def worker(idx: int):
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
            service = ClinicalCommandService(session, TENANT_A, user_a)
            payload = schemas.ClinicalWorkItemCreate(
                kind="procedure",
                code="REST_COMPOSITE" if idx % 2 == 0 else "ENDO_RCT",
                status="planned",
                notes=f"Variant payload {idx}",
            )
            return await service.create_work_item(PATIENT_A_ID, payload, idempotency_key=key)

    results = await asyncio.gather(*[worker(i) for i in range(4)], return_exceptions=True)

    successes = [r for r in results if isinstance(r, models.ClinicalWorkItem)]
    conflicts = [
        r for r in results
        if isinstance(r, HTTPException) and r.status_code == 409
    ]

    assert len(successes) == 1, f"Expected exactly 1 winner, got {len(successes)}: {results}"
    assert len(conflicts) == 3, f"Expected 3 conflicts (409), got {len(conflicts)}: {results}"

    other_exceptions = [
        r for r in results
        if isinstance(r, Exception) and not (isinstance(r, HTTPException) and r.status_code == 409)
    ]
    assert len(other_exceptions) == 0, f"Unexpected exceptions: {other_exceptions}"

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
        events = (
            await session.execute(
                select(models.ClinicalEvent).where(
                    models.ClinicalEvent.tenant_id == TENANT_A,
                    models.ClinicalEvent.patient_id == PATIENT_A_ID,
                )
            )
        ).scalars().all()
        matching_events = [
            e for e in events
            if isinstance(e.payload, dict) and e.payload.get("idempotency_key") == key
        ]
        assert len(matching_events) == 1
        assert matching_events[0].work_item_id == successes[0].id


@pytest.mark.asyncio
async def test_idempotency_tenant_isolation_same_key(monkeypatch):
    """Scenario 3: Tenant isolation of keys -> same key K used by tenant B is independent; tenant A never sees B's item/event."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    await _seed()
    user_a = models.User(id=USER_A_ID, tenant_id=TENANT_A, role="admin", is_active=True)
    user_b = models.User(id=USER_B_ID, tenant_id=TENANT_B, role="admin", is_active=True)
    key = "shared-isolated-key-3"

    async def worker_a():
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
            service = ClinicalCommandService(session, TENANT_A, user_a)
            payload = schemas.ClinicalWorkItemCreate(
                kind="procedure",
                code="REST_COMPOSITE",
                status="planned",
                notes="Tenant A item",
            )
            return await service.create_work_item(PATIENT_A_ID, payload, idempotency_key=key)

    async def worker_b():
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_B)) as session:
            service = ClinicalCommandService(session, TENANT_B, user_b)
            payload = schemas.ClinicalWorkItemCreate(
                kind="procedure",
                code="REST_COMPOSITE",
                status="planned",
                notes="Tenant B item",
            )
            return await service.create_work_item(PATIENT_B_ID, payload, idempotency_key=key)

    item_a, item_b = await asyncio.gather(worker_a(), worker_b())
    assert item_a.id != item_b.id
    assert item_a.tenant_id == TENANT_A
    assert item_b.tenant_id == TENANT_B

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
        assert await session.get(models.ClinicalWorkItem, item_a.id) is not None
        assert await session.get(models.ClinicalWorkItem, item_b.id) is None

        evs = (await session.execute(select(models.ClinicalEvent))).scalars().all()
        for e in evs:
            assert e.tenant_id == TENANT_A
            assert e.patient_id != PATIENT_B_ID

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_B)) as session:
        assert await session.get(models.ClinicalWorkItem, item_b.id) is not None
        assert await session.get(models.ClinicalWorkItem, item_a.id) is None

        evs = (await session.execute(select(models.ClinicalEvent))).scalars().all()
        for e in evs:
            assert e.tenant_id == TENANT_B
            assert e.patient_id != PATIENT_A_ID


@pytest.mark.asyncio
async def test_treatment_plans_postgres_concurrency_ordering_and_attachment(monkeypatch):
    """Scenario 4: 4 concurrent add_phase -> distinct contiguous orders; 2 concurrent add_work_item_to_phase -> 1 win, 1 409."""
    monkeypatch.setenv("CLINICAL_TREATMENT_PLANS_ENABLED", "true")
    await _seed()
    user_a = models.User(id=USER_A_ID, tenant_id=TENANT_A, role="admin", is_active=True)

    # 1. Create a treatment plan
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
        plan_service = TreatmentPlanService(session, TENANT_A, user_a)
        plan = await plan_service.create_plan(
            PATIENT_A_ID,
            schemas.ClinicalTreatmentPlanCreate(title="Concurrency Plan Test"),
        )
        plan_id = plan.id
        initial_phase_id = plan.phases[0].id

    # 2. 4 concurrent add_phase on one plan
    async def add_phase_worker(idx: int):
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
            service = TreatmentPlanService(session, TENANT_A, user_a)
            return await service.add_phase(
                PATIENT_A_ID,
                plan_id,
                schemas.ClinicalTreatmentPlanPhaseCreate(name=f"Concurrent Phase {idx}"),
            )

    phase_results = await asyncio.gather(
        *[add_phase_worker(i) for i in range(4)], return_exceptions=True
    )
    for res in phase_results:
        if isinstance(res, Exception):
            assert not isinstance(res, (IntegrityError, DBAPIError)), f"Unhandled DB integrity error: {res}"
            assert isinstance(res, HTTPException), f"Unexpected exception: {res}"

    # Verify phase_order values in DB are distinct and contiguous (0..N)
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
        phases = (
            await session.execute(
                select(models.ClinicalTreatmentPlanPhase)
                .where(
                    models.ClinicalTreatmentPlanPhase.tenant_id == TENANT_A,
                    models.ClinicalTreatmentPlanPhase.plan_id == plan_id,
                )
                .order_by(models.ClinicalTreatmentPlanPhase.phase_order.asc())
            )
        ).scalars().all()

        orders = [p.phase_order for p in phases]
        assert len(orders) == len(set(orders)), f"Phase orders must be distinct, got {orders}"
        assert orders == list(range(len(orders))), f"Phase orders must be contiguous 0..N, got {orders}"

    # 3. Create a procedure work item for attachment test
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
        cmd_service = ClinicalCommandService(session, TENANT_A, user_a)
        work_item = await cmd_service.create_work_item(
            PATIENT_A_ID,
            schemas.ClinicalWorkItemCreate(
                kind="procedure",
                code="REST_COMPOSITE",
                status="planned",
                notes="Attachment test proc",
            ),
            idempotency_key="plan-attachment-proc-key",
        )
        work_item_id = work_item.id

    # 4. 2 concurrent add_work_item_to_phase of the same work item into the same phase
    async def attach_worker():
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
            service = TreatmentPlanService(session, TENANT_A, user_a)
            return await service.add_work_item_to_phase(
                PATIENT_A_ID,
                plan_id,
                initial_phase_id,
                schemas.ClinicalTreatmentPlanItemCreate(work_item_id=work_item_id),
            )

    attach_results = await asyncio.gather(
        attach_worker(), attach_worker(), return_exceptions=True
    )

    attach_successes = [r for r in attach_results if isinstance(r, models.ClinicalTreatmentPlanItem)]
    attach_conflicts = [
        r for r in attach_results
        if isinstance(r, HTTPException) and r.status_code == 409
    ]

    assert len(attach_successes) == 1, f"Expected exactly 1 attach success, got {len(attach_successes)}: {attach_results}"
    assert len(attach_conflicts) == 1, f"Expected exactly 1 attach 409 conflict, got {len(attach_conflicts)}: {attach_results}"

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as session:
        items = (
            await session.execute(
                select(models.ClinicalTreatmentPlanItem).where(
                    models.ClinicalTreatmentPlanItem.tenant_id == TENANT_A,
                    models.ClinicalTreatmentPlanItem.phase_id == initial_phase_id,
                    models.ClinicalTreatmentPlanItem.work_item_id == work_item_id,
                )
            )
        ).scalars().all()
        assert len(items) == 1
