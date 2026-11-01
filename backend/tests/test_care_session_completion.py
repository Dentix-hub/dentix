"""Patient-facing completion paths: private queues and immutable visit corrections."""
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import select

from backend import models, schemas
from backend.auth import create_access_token
from backend.main import app
from backend.services.care_session_service import CareSessionService
from backend.tests.services.test_care_session_workflow_unification_v2 import (
    setup_env as setup_env, seed_visit, set_native_writes_flag,
)
from backend.tests.test_care_session_delivery_integrity import care_pg as care_pg
from backend.services.tenant_archive_export import export_clinic_archive_data
from backend.services.tenant_archive_import import replace_clinic_business_data
from backend.services.tenant_archive_registry import validate_archive_compatibility


@pytest.mark.asyncio
async def test_historical_ui_payload_records_treating_clinician_separately_from_recorder(async_db_session, setup_env):
    env = setup_env
    _, item, _ = await seed_visit(async_db_session, env, status='completed')
    recorder, provider = env['doctor1'], env['doctor2']
    token = create_access_token(data={'sub': recorder.username, 'tenant_id': recorder.tenant_id, 'role': recorder.role})
    payload = {
        'is_historical': True, 'actual_visit_date': '2026-10-01T10:00:00Z',
        'provider_user_id': provider.id, 'work_item_ids': [item.id], 'notes': 'Previously delivered care',
        'historical_steps': [{'title': 'Shade assessment', 'step_order': 1, 'status': 'completed', 'work_item_id': item.id}],
        'historical_observations': [{'observation_code': 'shade', 'work_item_id': item.id, 'structured_value': {'value': 'A2'}}],
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        response = await client.post(f"/api/v1/patients/{env['patient1'].id}/care-sessions", json=payload, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 201, response.text
    visit = response.json()['data']
    assert visit['provider_user_id'] == provider.id
    assert visit['recorded_by_user_id'] == recorder.id
    assert visit['steps'][0]['work_item_id'] == item.id
    assert visit['observations'][0]['structured_value']['value'] == 'A2'


@pytest.mark.asyncio
async def test_historical_clinician_must_be_active_doctor_in_the_same_clinic(async_db_session, setup_env):
    env = setup_env
    other_tenant = models.Tenant(name='Synthetic other clinic')
    async_db_session.add(other_tenant)
    await async_db_session.flush()
    foreign = models.User(tenant_id=other_tenant.id, username='foreign_care_provider', hashed_password='synthetic', role='doctor', is_active=True)
    reception = models.User(tenant_id=env['tenant'].id, username='reception_care_provider', hashed_password='synthetic', role='receptionist', is_active=True)
    async_db_session.add_all([foreign, reception])
    env['doctor2'].is_active = False
    await async_db_session.commit()
    service = CareSessionService(async_db_session, env['tenant'].id, env['doctor1'])
    for provider in (foreign, reception, env['doctor2']):
        with pytest.raises(HTTPException) as error:
            await service.start_session(env['patient1'].id, schemas.CareSessionCreate(
                is_historical=True, actual_visit_date=datetime(2026, 10, 1, tzinfo=timezone.utc), provider_user_id=provider.id))
        assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_reception_queue_and_http_endpoint_exclude_hidden_patients(async_db_session, setup_env):
    env = setup_env
    requests = [models.NextVisitRequest(tenant_id=env['tenant'].id, patient_id=env[key].id,
                                       reason='Synthetic private follow-up', status='requested')
                for key in ('patient1', 'patient2')]
    async_db_session.add_all(requests)
    await async_db_session.commit()
    doctor = env['doctor1']
    service = CareSessionService(async_db_session, env['tenant'].id, doctor)
    rows = await service.list_reception_queue(status='all')
    assert [row.patient_id for row in rows] == [env['patient1'].id]
    assert await service.list_reception_queue(patient_id=env['patient2'].id) == []
    admin_rows = await CareSessionService(async_db_session, env['tenant'].id, env['admin']).list_reception_queue()
    assert {row.patient_id for row in admin_rows} == {env['patient1'].id, env['patient2'].id}
    token = create_access_token(data={'sub': doctor.username, 'tenant_id': doctor.tenant_id, 'role': doctor.role})
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        response = await client.get('/api/v1/next-visit-requests', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200, response.text
    assert [row['patient_id'] for row in response.json()['data']] == [env['patient1'].id]


@pytest.mark.asyncio
async def test_visit_addenda_preserve_finalized_documentation_and_active_visit(async_db_session, setup_env):
    env = setup_env
    visit, _, procedure = await seed_visit(async_db_session, env, status='completed')
    visit.notes = 'Original visit narrative'
    visit.actual_visit_date = datetime(2026, 10, 1, tzinfo=timezone.utc)
    active = models.CareSession(tenant_id=env['tenant'].id, patient_id=env['patient1'].id, status='in_progress')
    async_db_session.add(active)
    await async_db_session.commit()
    original_version, original_recorded = visit.version_id, visit.created_at
    service = CareSessionService(async_db_session, env['tenant'].id, env['doctor1'])
    first = await service.add_session_addendum(env['patient1'].id, visit.id,
                                              schemas.CareSessionAddendumCreate(notes='Corrected narrative', reason='Transcription error'))
    second = await service.add_session_addendum(env['patient1'].id, visit.id,
                                               schemas.CareSessionAddendumCreate(notes='Additional finding', reason='Review of radiograph'))
    await async_db_session.refresh(visit)
    await async_db_session.refresh(procedure)
    assert (visit.notes, visit.version_id, visit.created_at) == ('Original visit narrative', original_version, original_recorded)
    assert procedure.procedure_notes == 'Original clinical note'
    assert (await service.get_active_session(env['patient1'].id)).id == active.id
    for entry in (first, second):
        read = schemas.CareSessionRead.model_validate(entry)
        assert read.amends_session_id == visit.id
        assert read.recorded_by_user_id == env['doctor1'].id
        assert read.status == 'completed' and not read.procedures and not read.steps
        assert read.actual_visit_date.date() == visit.actual_visit_date.date()
        assert read.created_at.date() > visit.actual_visit_date.date()
    events = (await async_db_session.execute(select(models.ClinicalEvent).where(
        models.ClinicalEvent.tenant_id == env['tenant'].id,
        models.ClinicalEvent.event_type == 'care_session_addendum_recorded',
    ))).scalars().all()
    assert len(events) == 2
    assert all(event.payload['amends_session_id'] == visit.id for event in events)


@pytest.mark.asyncio
async def test_visit_addendum_api_enforces_visibility_rbac_and_flag(async_db_session, setup_env):
    env = setup_env
    visit, _, _ = await seed_visit(async_db_session, env, status='completed')
    reception = models.User(tenant_id=env['tenant'].id, username='care_reception', hashed_password='synthetic', role='receptionist', is_active=True)
    async_db_session.add(reception)
    await async_db_session.commit()
    path = f"/api/v1/patients/{env['patient1'].id}/care-sessions/{visit.id}/addenda"
    payload = {'notes': 'Traceable correction', 'reason': 'Clinical review'}
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
        for user, expected in ((reception, 403), (env['doctor2'], 404), (env['doctor1'], 201)):
            token = create_access_token(data={'sub': user.username, 'tenant_id': user.tenant_id, 'role': user.role})
            response = await client.post(path, json=payload, headers={'Authorization': f'Bearer {token}'})
            assert response.status_code == expected, response.text
        await set_native_writes_flag(async_db_session, env['tenant'].id, False)
        response = await client.post(path, json=payload, headers={'Authorization': f'Bearer {token}'})
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_addenda_reject_active_visits_and_wrong_patient(async_db_session, setup_env):
    env = setup_env
    visit, _, _ = await seed_visit(async_db_session, env)
    service = CareSessionService(async_db_session, env['tenant'].id, env['admin'])
    for patient_id, expected in ((env['patient1'].id, 409), (env['patient2'].id, 404)):
        with pytest.raises(HTTPException) as exc:
            await service.add_session_addendum(patient_id, visit.id, schemas.CareSessionAddendumCreate(notes='Correction', reason='Review'))
        assert exc.value.status_code == expected


@pytest.mark.parametrize('schema,payload', [
    (schemas.CareSessionAddendumCreate, {'notes': ' ', 'reason': 'Review'}),
    (schemas.CareSessionAddendumCreate, {'notes': 'Correction', 'reason': ' '}),
    (schemas.CareObservationAmend, {'reason': ' '}),
])
def test_corrections_require_actual_documentation_and_reason(schema, payload):
    with pytest.raises(ValidationError):
        schema(**payload)


@pytest.mark.asyncio
async def test_observation_amendment_matches_route_visit_and_validates_tooth(async_db_session, setup_env):
    env = setup_env
    visit, item, _ = await seed_visit(async_db_session, env, status='completed')
    observation = models.CareObservation(tenant_id=env['tenant'].id, patient_id=env['patient1'].id,
        care_session_id=visit.id, work_item_id=item.id, observation_code='working_length', tooth_key='46',
        structured_value={'length_mm': 20, 'canal_id': 'MB'})
    async_db_session.add(observation)
    await async_db_session.commit()
    service = CareSessionService(async_db_session, env['tenant'].id, env['doctor1'])
    for session_id, tooth, expected in ((visit.id + 1000, '46', 404), (visit.id, '99', 422)):
        with pytest.raises(HTTPException) as error:
            await service.amend_observation(env['patient1'].id, observation.id,
                schemas.CareObservationAmend(reason='Correct target', tooth_key=tooth), session_id=session_id)
        assert error.value.status_code == expected
    assert not observation.is_superseded
    replacement = await service.amend_observation(env['patient1'].id, observation.id,
        schemas.CareObservationAmend(reason='Remove incorrect canal association', canal_id=None), session_id=visit.id)
    assert replacement.canal_id is None
    assert observation.structured_value == {'length_mm': 20, 'canal_id': 'MB'}


@pytest.mark.asyncio
async def test_recorded_visit_addendum_survives_postgresql_archive_roundtrip(care_pg):
    db, tenants, users, patients, visits, _ = care_pg
    tenant, user, patient, visit = tenants[0], users[0], patients[0], visits[0]
    patient.assigned_doctor_id = user.id
    visit.notes = 'Immutable original narrative'
    await set_native_writes_flag(db, tenant.id, True)
    service = CareSessionService(db, tenant.id, user)
    addendum = await service.add_session_addendum(patient.id, visit.id,
        schemas.CareSessionAddendumCreate(notes='Corrected clinical narrative', reason='Chart review'))
    old_visit_id, old_addendum_id = visit.id, addendum.id
    archive = await export_clinic_archive_data(db, tenant.id, validate_restore=False)
    data, _ = await validate_archive_compatibility(db, archive, tenant_id=tenant.id, external_ids={})
    _, mapping = await replace_clinic_business_data(db, tenant_id=tenant.id, data=data, staff_mapping={user.id: user.id})
    restored = (await db.execute(select(models.CareSession).where(
        models.CareSession.tenant_id == tenant.id,
        models.CareSession.id == mapping['care_sessions'][old_addendum_id],
    ))).scalar_one()
    assert restored.amends_session_id == mapping['care_sessions'][old_visit_id]
    assert restored.amends_session_id != old_visit_id
    assert restored.notes == 'Corrected clinical narrative'
    event = (await db.execute(select(models.ClinicalEvent).where(
        models.ClinicalEvent.tenant_id == tenant.id,
        models.ClinicalEvent.care_session_id == restored.id,
        models.ClinicalEvent.event_type == 'care_session_addendum_recorded',
    ))).scalar_one()
    assert event.payload['amends_session_id'] == restored.amends_session_id
