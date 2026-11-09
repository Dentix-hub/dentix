"""PostgreSQL regressions for clinical retry and retrospective visit integrity."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend import models, schemas
from backend.core.tenant_scope import clear_tenant_context, set_current_tenant
from backend.services.care_session_service import CareSessionService
from backend.services.clinical_command_service import ClinicalCommandService
from backend.services.clinical_workspace_service import (
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
)
from backend.tests import test_promotion_ai_policy as postgres_fixtures

policy_database = postgres_fixtures.policy_database


@pytest.fixture
async def clinical_case(policy_database):
    case = policy_database
    engine = create_async_engine(
        case.url.replace("postgresql://", "postgresql+asyncpg://"),
        execution_options={"schema_translate_map": {None: case.schema}},
    )
    set_current_tenant(case.tenant_id)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            user = models.User(
                tenant_id=case.tenant_id,
                username="synthetic_release_owner",
                hashed_password="synthetic-only",
                role="admin",
                is_active=True,
                is_deleted=False,
            )
            db.add(user)
            await db.flush()
            patient = models.Patient(
                tenant_id=case.tenant_id,
                name="Synthetic clinical fixture",
                age=30,
                phone="",
                assigned_doctor_id=user.id,
                is_deleted=False,
            )
            db.add_all(
                [
                    patient,
                    models.FeatureFlag(
                        key=FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
                        is_global_enabled=True,
                        rollout_percentage=100,
                    ),
                ]
            )
            await db.flush()
            item = models.ClinicalWorkItem(
                tenant_id=case.tenant_id,
                patient_id=patient.id,
                kind="procedure",
                code="REST_COMPOSITE",
                status="active",
                created_by_user_id=user.id,
            )
            db.add(item)
            await db.commit()
            yield SimpleNamespace(
                db=db, tenant_id=case.tenant_id, user=user, patient=patient, item=item
            )
    finally:
        clear_tenant_context()
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("step_status", ["completed", "pending"])
async def test_completed_procedure_retry_preserves_request_key_and_event(
    clinical_case, step_status
):
    case = clinical_case
    visit = models.CareSession(
        tenant_id=case.tenant_id,
        patient_id=case.patient.id,
        provider_user_id=case.user.id,
        status="completed",
    )
    case.db.add(visit)
    await case.db.flush()
    case.db.add(
        models.CareSessionStep(
            tenant_id=case.tenant_id,
            care_session_id=visit.id,
            work_item_id=case.item.id,
            step_order=1,
            step_code="restoration",
            logical_step_code="restoration",
            occurrence_number=1,
            title="Synthetic restoration",
            status=step_status,
        )
    )
    await case.db.commit()
    original_version = case.item.version_id
    request = schemas.ClinicalWorkItemStatusUpdate(
        status="completed",
        expected_version_id=original_version,
        override_reason="Synthetic explicit completion override"
        if step_status == "pending"
        else None,
    )
    service = ClinicalCommandService(case.db, case.tenant_id, case.user)
    first = await service.update_work_item_status(
        case.patient.id,
        case.item.id,
        request,
        idempotency_key="synthetic-procedure-completion",
    )
    event = await case.db.scalar(
        select(models.ClinicalEvent).where(
            models.ClinicalEvent.tenant_id == case.tenant_id,
            models.ClinicalEvent.id == first.event_id,
        )
    )
    assert event.payload["idempotency_key"] == "synthetic-procedure-completion"
    replay = await service.update_work_item_status(
        case.patient.id,
        case.item.id,
        request,
        idempotency_key="synthetic-procedure-completion",
    )
    assert replay.event_id == first.event_id
    assert replay.version_id == first.version_id == original_version + 1
    assert (
        await case.db.scalar(
            select(func.count(models.ClinicalEvent.id)).where(
                models.ClinicalEvent.tenant_id == case.tenant_id,
                models.ClinicalEvent.work_item_id == case.item.id,
            )
        )
        == 1
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("historical", [True, False])
async def test_retrospective_visit_uses_only_explicit_facts_live_visit_keeps_references(
    clinical_case, historical
):
    case = clinical_case
    later_date = datetime.now(timezone.utc) - timedelta(days=5)
    previous = models.CareSession(
        tenant_id=case.tenant_id,
        patient_id=case.patient.id,
        provider_user_id=case.user.id,
        status="completed",
        actual_visit_date=later_date,
        started_at=later_date,
        finished_at=later_date,
    )
    case.db.add(previous)
    await case.db.flush()
    case.db.add(
        models.CareSessionProcedure(
            tenant_id=case.tenant_id,
            care_session_id=previous.id,
            work_item_id=case.item.id,
        )
    )
    observation = models.CareObservation(
        tenant_id=case.tenant_id,
        patient_id=case.patient.id,
        care_session_id=previous.id,
        work_item_id=case.item.id,
        observation_code="working_length",
        tooth_key="16",
        structured_value={"canal_id": "MB1", "length_mm": 22},
        recorded_by_user_id=case.user.id,
    )
    case.db.add(observation)
    await case.db.commit()
    values = {"work_item_ids": [case.item.id]}
    if historical:
        values.update(
            is_historical=True,
            actual_visit_date=later_date - timedelta(days=5),
            historical_observations=[
                {
                    "work_item_id": case.item.id,
                    "observation_code": "working_length",
                    "tooth_key": "16",
                    "structured_value": {"canal_id": "MB1", "length_mm": 18},
                }
            ],
        )
    service = CareSessionService(case.db, case.tenant_id, case.user)
    created = await service.start_session(
        case.patient.id, schemas.CareSessionCreate(**values)
    )
    rows = list(
        await case.db.scalars(
            select(models.CareObservation).where(
                models.CareObservation.tenant_id == case.tenant_id,
                models.CareObservation.care_session_id == created.id,
            )
        )
    )
    assert len(rows) == 1
    assert rows[0].structured_value["length_mm"] == (18 if historical else 22)
    if historical:
        assert rows[0].reference_source_session_id is None
    else:
        assert rows[0].reference_source_session_id == previous.id
    await case.db.refresh(observation)
    assert (
        observation.structured_value["length_mm"] == 22
        and observation.reference_source_session_id is None
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_scope,historical",
    [
        ("same_patient", False),
        ("other_patient", False),
        ("other_tenant", False),
        ("other_patient", True),
        ("other_tenant", True),
    ],
)
async def test_continuation_source_is_bound_to_visible_target_patient(
    clinical_case, source_scope, historical
):
    case = clinical_case
    case.user.role = "doctor"
    source_patient = case.patient
    source_tenant_id = case.tenant_id
    source_doctor = case.user
    if source_scope != "same_patient":
        if source_scope == "other_tenant":
            other_tenant = models.Tenant(
                name="Synthetic isolated source clinic", is_active=True
            )
            case.db.add(other_tenant)
            await case.db.flush()
            source_tenant_id = other_tenant.id
        source_doctor = models.User(
            tenant_id=source_tenant_id,
            username="synthetic_other_source_doctor",
            hashed_password="synthetic-only",
            role="doctor",
            is_active=True,
            is_deleted=False,
        )
        case.db.add(source_doctor)
        await case.db.flush()
        source_patient = models.Patient(
            tenant_id=source_tenant_id,
            name="Synthetic source patient",
            age=30,
            phone="",
            assigned_doctor_id=source_doctor.id,
            is_deleted=False,
        )
        case.db.add(source_patient)
        await case.db.flush()
    source_item = models.ClinicalWorkItem(
        tenant_id=source_tenant_id,
        patient_id=source_patient.id,
        kind="procedure",
        code="REST_COMPOSITE",
        status="active",
        created_by_user_id=source_doctor.id,
    )
    source = models.CareSession(
        tenant_id=source_tenant_id,
        patient_id=source_patient.id,
        provider_user_id=source_doctor.id,
        status="completed",
    )
    case.db.add_all([source_item, source])
    await case.db.flush()
    source_step = models.CareSessionStep(
        tenant_id=source_tenant_id,
        care_session_id=source.id,
        work_item_id=source_item.id,
        step_order=1,
        step_code="source_step",
        title="Synthetic source task",
        notes="Synthetic source-only note",
        status="pending",
    )
    case.db.add(source_step)
    await case.db.commit()
    values = {"resume_from_session_id": source.id}
    if historical:
        values.update(
            is_historical=True,
            actual_visit_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
    service = CareSessionService(case.db, case.tenant_id, case.user)
    if source_scope == "same_patient":
        created = await service.start_session(
            case.patient.id, schemas.CareSessionCreate(**values)
        )
        copied = list(
            await case.db.scalars(
                select(models.CareSessionStep).where(
                    models.CareSessionStep.tenant_id == case.tenant_id,
                    models.CareSessionStep.care_session_id == created.id,
                )
            )
        )
        assert len(copied) == 1
        assert (
            copied[0].notes
            == f"[Resumed from Step #{source_step.id}] Synthetic source-only note"
        )
        assert copied[0].work_item_id == source_item.id
    else:
        before = await case.db.scalar(
            select(func.count(models.CareSession.id)).where(
                models.CareSession.tenant_id == case.tenant_id,
                models.CareSession.patient_id == case.patient.id,
            )
        )
        with pytest.raises(HTTPException) as error:
            await service.start_session(
                case.patient.id, schemas.CareSessionCreate(**values)
            )
        assert error.value.status_code == 404
        after = await case.db.scalar(
            select(func.count(models.CareSession.id)).where(
                models.CareSession.tenant_id == case.tenant_id,
                models.CareSession.patient_id == case.patient.id,
            )
        )
        assert after == before
