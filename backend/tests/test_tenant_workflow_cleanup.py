"""Workflow children obey tenant filtering and patient/tenant cleanup boundaries."""

import pytest
from sqlalchemy import delete, event, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend import models
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.crud.patient import delete_patient_permanently, delete_tenant_clinical_rows


@pytest.fixture
async def workflow_db(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'workflow.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as connection:
        await connection.run_sync(models.Base.metadata.create_all)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            tenants = [models.Tenant(name=f"Cleanup clinic {i}") for i in range(2)]
            db.add_all(tenants)
            await db.flush()
            rows = []
            # A second patient in the same clinic must survive patient cleanup.
            for index, tenant in enumerate((tenants[0], tenants[0], tenants[1])):
                user = models.User(
                    tenant_id=tenant.id,
                    username=f"cleanup_doctor_{index}",
                    email=f"cleanup_{index}@example.com",
                    hashed_password="test-hash",
                    role="doctor",
                )
                patient = models.Patient(tenant_id=tenant.id, name=f"Cleanup patient {index}")
                db.add_all([user, patient])
                await db.flush()
                session = models.CareSession(tenant_id=tenant.id, patient_id=patient.id)
                item = models.ClinicalWorkItem(
                    tenant_id=tenant.id, patient_id=patient.id, kind="procedure", code="REST_COMPOSITE"
                )
                db.add_all([session, item])
                await db.flush()
                procedure = models.CareSessionProcedure(
                    tenant_id=tenant.id, care_session_id=session.id, work_item_id=item.id,
                    procedure_notes="original",
                )
                drafts = [
                    models.CareSessionDraft(
                        tenant_id=tenant.id, patient_id=patient.id, author_user_id=user.id,
                        care_session_id=session_id, draft_payload={"notes": "original"},
                    )
                    for session_id in (None, session.id)
                ]
                db.add_all([procedure, *drafts])
                await db.flush()
                rows.append({
                    "tenant_id": tenant.id, "patient_id": patient.id,
                    "procedure_ids": {procedure.id}, "draft_ids": {draft.id for draft in drafts},
                })
            await db.commit()
            yield db, rows
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("cleanup", ["patient", "tenant"])
async def test_workflow_cleanup_preserves_other_patients_and_tenants(workflow_db, cleanup):
    db, rows = workflow_db
    target = rows[0]
    token = set_current_tenant_id(target["tenant_id"])
    try:
        if cleanup == "patient":
            await delete_patient_permanently(db, target["patient_id"], target["tenant_id"])
        else:
            await delete_tenant_clinical_rows(db, target["tenant_id"])
            await db.commit()
    finally:
        clear_tenant_context(tenant_token=token)

    survivors = rows[1:] if cleanup == "patient" else rows[2:]
    for model, key in ((models.CareSessionDraft, "draft_ids"), (models.CareSessionProcedure, "procedure_ids")):
        remaining = set((await db.execute(select(model.id))).scalars())
        assert remaining == set().union(*(row[key] for row in survivors))
    assert await db.get(models.Patient, rows[1]["patient_id"]) is not None
    assert await db.get(models.Patient, rows[2]["patient_id"]) is not None
    if cleanup == "patient":
        assert await db.get(models.Patient, target["patient_id"]) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("model,key,field,value", [
    (models.CareSessionDraft, "draft_ids", "draft_payload", {"notes": "updated"}),
    (models.CareSessionProcedure, "procedure_ids", "procedure_notes", "updated"),
])
async def test_workflow_tenant_scope_filters_reads_updates_and_deletes(workflow_db, model, key, field, value):
    # These isolated SQLite sessions need the ORM listener explicitly loaded;
    # they do not use the PostgreSQL application's RLS session factory.
    from backend.core import tenant_scope
    from sqlalchemy.orm import Session

    assert event.contains(Session, "do_orm_execute", tenant_scope._add_tenant_filter)
    db, rows = workflow_db
    token = set_current_tenant_id(rows[0]["tenant_id"])
    try:
        expected = rows[0][key] | rows[1][key]
        assert set((await db.execute(select(model.id))).scalars()) == expected
        await db.execute(update(model).values(**{field: value}))
        assert list((await db.execute(select(getattr(model, field)))).scalars()) == [value] * len(expected)
        await db.execute(delete(model))
        assert list((await db.execute(select(model.id))).scalars()) == []
    finally:
        clear_tenant_context(tenant_token=token)

    remaining = (await db.execute(select(model.id, getattr(model, field)))).all()
    original = {"notes": "original"} if model is models.CareSessionDraft else "original"
    assert {row[0] for row in remaining} == rows[2][key]
    assert all(row[1] == original for row in remaining)
