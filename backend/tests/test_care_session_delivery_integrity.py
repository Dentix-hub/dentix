"""Live PostgreSQL regression gates for care-session delivery and recovery."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend import models
from backend.services.tenant_archive_export import export_clinic_archive_data
from backend.services.tenant_archive_import import replace_clinic_business_data
from backend.services.tenant_archive import ArchiveError
from backend.services.tenant_archive_registry import (
    ARCHIVE_COLUMNS, CLINICAL_REFERENCE_COLUMNS,
    validate_archive_compatibility, validate_archive_references,
)


@pytest.fixture
async def care_pg():
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://")):
        pytest.skip("Requires a preflight-initialized PostgreSQL TEST_DATABASE_URL")
    engine = create_async_engine(url.replace("postgres://", "postgresql+asyncpg://", 1)
                                 .replace("postgresql://", "postgresql+asyncpg://", 1))
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            async with AsyncSession(bind=connection, expire_on_commit=False) as db:
                suffix = uuid4().hex
                tenants = [models.Tenant(name=f"Synthetic care {i} {suffix}") for i in range(2)]
                db.add_all(tenants)
                await db.flush()
                users = [models.User(tenant_id=t.id, username=f"care-{i}-{suffix}",
                                     hashed_password="synthetic-not-a-credential", role="doctor")
                         for i, t in enumerate(tenants)]
                patients = [models.Patient(tenant_id=t.id, name=f"Synthetic patient {i}")
                            for i, t in enumerate(tenants)]
                db.add_all(users + patients)
                await db.flush()
                visits = [models.CareSession(tenant_id=t.id, patient_id=p.id, status="completed")
                          for t, p in zip(tenants, patients, strict=True)]
                items = [models.ClinicalWorkItem(tenant_id=t.id, patient_id=p.id,
                                                  kind="procedure", code="ENDO_RCT", status="active")
                         for t, p in zip(tenants, patients, strict=True)]
                db.add_all(visits + items)
                await db.flush()
                yield db, tenants, users, patients, visits, items
            await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("table,key", [
    ("procedures", "care_session_id"), ("procedures", "work_item_id"),
    ("drafts", "patient_id"), ("drafts", "care_session_id"),
])
async def test_new_care_tables_reject_cross_tenant_parents(care_pg, table, key):
    db, tenants, users, patients, visits, items = care_pg
    if table == "procedures":
        cls = models.CareSessionProcedure
        values = dict(tenant_id=tenants[0].id, care_session_id=visits[0].id,
                      work_item_id=items[0].id)
        foreign = dict(care_session_id=visits[1].id, work_item_id=items[1].id)
    else:
        cls = models.CareSessionDraft
        values = dict(tenant_id=tenants[0].id, patient_id=patients[0].id,
                      care_session_id=visits[0].id, author_user_id=users[0].id,
                      draft_payload={"notes": "Synthetic"})
        foreign = dict(patient_id=patients[1].id, care_session_id=visits[1].id)
    with pytest.raises(DBAPIError, match="Tenant mismatch"):
        async with db.begin_nested():
            db.add(cls(**{**values, key: foreign[key]}))
            await db.flush()
    db.add(cls(**values))
    await db.flush()


@pytest.mark.asyncio
async def test_archive_restore_remaps_follow_up_and_visit_provenance(care_pg):
    db, tenants, users, patients, visits, items = care_pg
    tenant, doctor, patient, visit, item = tenants[0], users[0], patients[0], visits[0], items[0]
    replacement = models.User(tenant_id=tenant.id, username=f"replacement-{uuid4().hex}",
                              hashed_password="synthetic-not-a-credential", role="doctor")
    db.add(replacement)
    await db.flush()
    visit.recorded_by_user_id = doctor.id
    amended = models.CareSession(tenant_id=tenant.id, patient_id=patient.id,
                                 status="completed", amends_session_id=visit.id,
                                 recorded_by_user_id=doctor.id)
    db.add(amended)
    await db.flush()
    request = models.NextVisitRequest(
        tenant_id=tenant.id, patient_id=patient.id, care_session_id=amended.id,
        work_item_id=item.id, reason="Synthetic follow-up", status="postponed",
        associated_work_item_ids=[item.id], assigned_doctor_id=doctor.id,
        stopped_by_user_id=doctor.id, postponed_by_user_id=doctor.id,
        handoff_by_user_id=doctor.id, handoff_to_user_id=doctor.id,
    )
    db.add(request)
    await db.flush()
    old_visit, old_amended, old_item, old_request = visit.id, amended.id, item.id, request.id
    payload = await export_clinic_archive_data(db, tenant.id, validate_restore=False)
    data, _ = await validate_archive_compatibility(db, payload, tenant_id=tenant.id, external_ids={})
    _, mapping = await replace_clinic_business_data(
        db, tenant_id=tenant.id, data=data,
        staff_mapping={doctor.id: replacement.id, replacement.id: doctor.id},
    )
    restored = (await db.execute(select(models.NextVisitRequest).where(
        models.NextVisitRequest.tenant_id == tenant.id,
        models.NextVisitRequest.id == mapping["next_visit_requests"][old_request],
    ))).scalar_one()
    restored_visit = (await db.execute(select(models.CareSession).where(
        models.CareSession.tenant_id == tenant.id,
        models.CareSession.id == mapping["care_sessions"][old_amended],
    ))).scalar_one()
    assert mapping["clinical_work_items"][old_item] != old_item
    assert mapping["care_sessions"][old_visit] != old_visit
    assert restored.associated_work_item_ids == [mapping["clinical_work_items"][old_item]]
    for key in ("assigned_doctor_id", "stopped_by_user_id", "postponed_by_user_id",
                "handoff_by_user_id", "handoff_to_user_id"):
        assert getattr(restored, key) == replacement.id, key
    assert restored_visit.recorded_by_user_id == replacement.id
    assert restored_visit.amends_session_id == mapping["care_sessions"][old_visit]
    other_patient = (await db.execute(select(models.Patient).where(
        models.Patient.tenant_id == tenants[1].id, models.Patient.id == patients[1].id,
    ))).scalar_one()
    assert other_patient.tenant_id == tenants[1].id


@pytest.mark.asyncio
async def test_upgraded_care_indexes_match_model_contract(care_pg):
    db, *_ = care_pg
    connection = await db.connection()

    def check_indexes(sync_connection):
        inspector = inspect(sync_connection)
        for name in ("care_sessions", "care_session_steps", "care_observations",
                     "care_session_procedures", "care_session_drafts", "next_visit_requests"):
            existing = {index["name"]: tuple(index["column_names"])
                        for index in inspector.get_indexes(name)}
            for index in models.Base.metadata.tables[name].indexes:
                assert existing.get(index.name) == tuple(column.name for column in index.columns), index.name

    await connection.run_sync(check_indexes)


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["care_session_procedures", "care_session_drafts"])
async def test_new_care_tables_enforce_rls_under_restricted_role(care_pg, table):
    db, tenants, users, patients, visits, items = care_pg
    for i in range(2):
        db.add(models.CareSessionProcedure(tenant_id=tenants[i].id,
                                           care_session_id=visits[i].id, work_item_id=items[i].id))
        db.add(models.CareSessionDraft(tenant_id=tenants[i].id, patient_id=patients[i].id,
                                       care_session_id=visits[i].id, author_user_id=users[i].id,
                                       draft_payload={"notes": "Synthetic"}))
    await db.flush()
    role = f"care_review_{uuid4().hex}"
    # DDL/grants are rolled back with the fixture; no persistent role remains.
    await db.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER NOBYPASSRLS'))
    await db.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
    await db.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{role}"'))
    await db.execute(text(f'GRANT INSERT ON "{table}" TO "{role}"'))
    await db.execute(text(f'GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO "{role}"'))
    await db.execute(text(f'SET LOCAL ROLE "{role}"'))
    role_flags = (await db.execute(text(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
    ))).one()
    assert tuple(role_flags) == (False, False)
    await db.execute(text("SELECT set_config('rls.tenant_id', :tenant, true)"), {"tenant": str(tenants[0].id)})
    rows = (await db.execute(text(f'SELECT tenant_id FROM "{table}"'))).scalars().all()
    assert rows == [tenants[0].id]
    await db.execute(text("SELECT set_config('rls.tenant_id', '', true)"))
    await db.execute(text("SELECT set_config('rls.bypass_rls', 'true', true)"))
    assert (await db.execute(text(f'SELECT count(*) FROM "{table}"'))).scalar_one() == 0
    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            if table == "care_session_procedures":
                stmt = text("INSERT INTO care_session_procedures (tenant_id, care_session_id, work_item_id) "
                            "VALUES (:tenant, :visit, :item)")
            else:
                stmt = text("INSERT INTO care_session_drafts (tenant_id, patient_id, care_session_id, author_user_id, draft_payload) "
                            "VALUES (:tenant, :patient, :visit, :author, '{}')")
            await db.execute(stmt, {"tenant": tenants[1].id, "patient": patients[1].id,
                                    "visit": visits[1].id, "item": items[1].id, "author": users[1].id})


@pytest.mark.parametrize("table,key,target", [
    (table, key, target)
    for table, columns in CLINICAL_REFERENCE_COLUMNS.items()
    for key, target in columns.items()
])
@pytest.mark.parametrize("value,category", [(99999, "invalid_reference"), (True, "invalid_reference_type")])
def test_archive_rejects_invalid_clinical_provenance(table, key, target, value, category):
    data = {name: [] for name in ARCHIVE_COLUMNS}
    data["staff_references"] = []
    data[table] = [{"id": 1, "tenant_id": 7, key: value}]
    with pytest.raises(ArchiveError) as error:
        validate_archive_references(data, tenant_id=7)
    assert error.value.category == category
    assert error.value.field == key
    assert error.value.referenced_section == target


@pytest.mark.parametrize("value,category", [
    ([99999], "invalid_reference"), ([True], "invalid_reference_type"),
    (["1"], "invalid_reference_type"), ({"id": 1}, "invalid_reference_type"),
])
def test_archive_rejects_invalid_follow_up_procedure_ids(value, category):
    data = {name: [] for name in ARCHIVE_COLUMNS}
    data["staff_references"] = []
    data["next_visit_requests"] = [{"id": 1, "tenant_id": 7, "associated_work_item_ids": value}]
    with pytest.raises(ArchiveError) as error:
        validate_archive_references(data, tenant_id=7)
    assert error.value.category == category
    assert error.value.field == "associated_work_item_ids"
