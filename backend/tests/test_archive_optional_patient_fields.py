"""Optional demographics must survive export and authenticated preview unchanged."""
from datetime import date

import pytest

from backend import models
from backend.services.tenant_archive import decode_archive, encode_archive
from backend.services.tenant_archive_export import export_clinic_archive_data
from backend.services.tenant_restore_preview import create_restore_preview


@pytest.mark.asyncio
@pytest.mark.parametrize('age,dob', [(None, None), (None, date(2015, 3, 10)), (0, None)])
async def test_optional_demographics_survive_archive_and_preview(async_db_session, test_user, age, dob):
    patient = models.Patient(
        tenant_id=test_user.tenant_id, name='Synthetic optional demographics',
        age=age, phone=None, date_of_birth=dob,
    )
    async_db_session.add(patient)
    await async_db_session.commit()
    patient_id = patient.id

    payload = await export_clinic_archive_data(async_db_session, test_user.tenant_id)
    row = next(row for row in payload['data']['patients'] if row['id'] == patient_id)
    assert row['age'] == age
    assert row['phone'] is None
    assert row['date_of_birth'] == (dob.isoformat() if dob else None)
    assert all(row['tenant_id'] == test_user.tenant_id for row in payload['data']['patients'])

    archive = encode_archive(
        payload, tenant_id=test_user.tenant_id, installation_id='synthetic',
        schema_revision='e2b3c4d5e6f7', key_id='test', key=b'x' * 32,
    )
    _, decoded = decode_archive(
        archive, tenant_id=test_user.tenant_id, installation_id='synthetic', keys={'test': b'x' * 32},
    )
    assert decoded == payload
    operation, _, _, counts, _ = await create_restore_preview(
        async_db_session, tenant_id=test_user.tenant_id, actor_id=test_user.id,
        archive=archive, installation_id='synthetic', keys={'test': b'x' * 32},
        supported_revisions={'e2b3c4d5e6f7'}, max_bytes=1000000,
    )
    assert operation.status == 'previewed'
    assert counts['patients'] == 1
    await async_db_session.refresh(patient)
    assert patient.age == age and patient.phone is None and patient.date_of_birth == dob
