import pytest
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy import select
from unittest.mock import patch

from backend import models, schemas, crud


def make_patient(tenant_id: int, name: str = "Test Patient"):
    return models.Patient(
        tenant_id=tenant_id,
        name=name,
        age=30,
        phone="+966500000001",
        medical_history="None",
        notes="None",
        is_deleted=False,
    )


@pytest.mark.asyncio
async def test_update_appointment_cross_tenant_patient_validation(async_db_session):
    # Setup Tenant 1 and Tenant 2
    t1 = models.Tenant(name="Tenant 1", domain="t1.test")
    t2 = models.Tenant(name="Tenant 2", domain="t2.test")
    async_db_session.add_all([t1, t2])
    await async_db_session.flush()

    p1 = make_patient(t1.id, "Patient 1")
    p2 = make_patient(t2.id, "Patient 2")
    async_db_session.add_all([p1, p2])
    await async_db_session.flush()

    appt = models.Appointment(
        patient_id=p1.id,
        tenant_id=t1.id,
        date_time=datetime(2026, 11, 1, 10, 0),
        status="Scheduled",
    )
    async_db_session.add(appt)
    await async_db_session.commit()
    await async_db_session.refresh(appt)

    # Attempt to update appt with p2 (cross-tenant)
    update_data = schemas.AppointmentUpdate(patient_id=p2.id)
    with pytest.raises(HTTPException) as exc_info:
        await crud.update_appointment(
            db=async_db_session,
            appointment_id=appt.id,
            appointment=update_data,
            tenant_id=t1.id,
        )
    assert exc_info.value.status_code in (404, 422)


@pytest.mark.asyncio
async def test_update_appointment_cross_tenant_doctor_validation(async_db_session):
    t1 = models.Tenant(name="Tenant 1", domain="t1-doc.test")
    t2 = models.Tenant(name="Tenant 2", domain="t2-doc.test")
    async_db_session.add_all([t1, t2])
    await async_db_session.flush()

    u2 = models.User(
        username="doc2",
        email="doc2@t2.test",
        hashed_password="fake",
        role="doctor",
        tenant_id=t2.id,
    )
    p1 = make_patient(t1.id, "Patient 1")
    async_db_session.add_all([u2, p1])
    await async_db_session.flush()

    appt = models.Appointment(
        patient_id=p1.id,
        tenant_id=t1.id,
        date_time=datetime(2026, 11, 2, 10, 0),
        status="Scheduled",
    )
    async_db_session.add(appt)
    await async_db_session.commit()

    update_data = schemas.AppointmentUpdate(doctor_id=u2.id)
    with pytest.raises(HTTPException) as exc_info:
        await crud.update_appointment(
            db=async_db_session,
            appointment_id=appt.id,
            appointment=update_data,
            tenant_id=t1.id,
        )
    assert exc_info.value.status_code in (404, 422)


@pytest.mark.asyncio
async def test_update_appointment_conflict_check(async_db_session):
    t1 = models.Tenant(name="Tenant 1", domain="t1-conf.test")
    async_db_session.add(t1)
    await async_db_session.flush()

    p1 = make_patient(t1.id, "Patient 1")
    async_db_session.add(p1)
    await async_db_session.flush()

    time_slot_1 = datetime(2026, 11, 3, 10, 0)
    time_slot_2 = datetime(2026, 11, 3, 11, 0)

    appt1 = models.Appointment(
        patient_id=p1.id,
        tenant_id=t1.id,
        date_time=time_slot_1,
        status="Scheduled",
    )
    appt2 = models.Appointment(
        patient_id=p1.id,
        tenant_id=t1.id,
        date_time=time_slot_2,
        status="Scheduled",
    )
    async_db_session.add_all([appt1, appt2])
    await async_db_session.commit()

    # Self-exclusion check: appt1 updating to time_slot_1 must NOT trigger conflict
    res = await crud.update_appointment(
        db=async_db_session,
        appointment_id=appt1.id,
        appointment=schemas.AppointmentUpdate(date_time=time_slot_1, notes="same slot"),
        tenant_id=t1.id,
    )
    assert res is not None

    # Conflict check: appt2 updating to time_slot_1 MUST trigger 409 conflict
    with pytest.raises(HTTPException) as exc_info:
        await crud.update_appointment(
            db=async_db_session,
            appointment_id=appt2.id,
            appointment=schemas.AppointmentUpdate(date_time=time_slot_1),
            tenant_id=t1.id,
        )
    assert exc_info.value.status_code == 409
    assert "conflict" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_update_appointment_final_status_rejection(async_db_session):
    t1 = models.Tenant(name="Tenant 1", domain="t1-final.test")
    async_db_session.add(t1)
    await async_db_session.flush()

    p1 = make_patient(t1.id, "Patient 1")
    async_db_session.add(p1)
    await async_db_session.flush()

    appt_completed = models.Appointment(
        patient_id=p1.id,
        tenant_id=t1.id,
        date_time=datetime(2026, 11, 4, 10, 0),
        status="Completed",
    )
    appt_cancelled = models.Appointment(
        patient_id=p1.id,
        tenant_id=t1.id,
        date_time=datetime(2026, 11, 4, 11, 0),
        status="Cancelled",
    )
    async_db_session.add_all([appt_completed, appt_cancelled])
    await async_db_session.commit()

    # Changing date_time on Completed -> 409
    with pytest.raises(HTTPException) as exc_info:
        await crud.update_appointment(
            db=async_db_session,
            appointment_id=appt_completed.id,
            appointment=schemas.AppointmentUpdate(date_time=datetime(2026, 11, 4, 14, 0)),
            tenant_id=t1.id,
        )
    assert exc_info.value.status_code == 409

    # Changing duration on Cancelled -> 409
    with pytest.raises(HTTPException) as exc_info:
        await crud.update_appointment(
            db=async_db_session,
            appointment_id=appt_cancelled.id,
            appointment=schemas.AppointmentUpdate(duration_minutes=45),
            tenant_id=t1.id,
        )
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_update_appointment_postponed_reschedule_to_scheduled(async_db_session):
    t1 = models.Tenant(name="Tenant 1", domain="t1-post.test")
    async_db_session.add(t1)
    await async_db_session.flush()

    p1 = make_patient(t1.id, "Patient 1")
    async_db_session.add(p1)
    await async_db_session.flush()

    appt = models.Appointment(
        patient_id=p1.id,
        tenant_id=t1.id,
        date_time=datetime(2026, 11, 5, 10, 0),
        status="Postponed",
    )
    async_db_session.add(appt)
    await async_db_session.commit()

    # Reschedule date_time without passing status
    new_date = datetime(2026, 11, 6, 10, 0)
    updated = await crud.update_appointment(
        db=async_db_session,
        appointment_id=appt.id,
        appointment=schemas.AppointmentUpdate(date_time=new_date),
        tenant_id=t1.id,
    )
    assert updated.status == "Scheduled"
    assert updated.date_time == new_date


@pytest.mark.asyncio
async def test_update_appointment_persists_audit_entry(async_db_session):
    t1 = models.Tenant(name="Tenant 1", domain="t1-audit.test")
    async_db_session.add(t1)
    await async_db_session.flush()

    u1 = models.User(
        username="admin1",
        email="admin@t1.test",
        hashed_password="fake",
        role="admin",
        tenant_id=t1.id,
    )
    p1 = make_patient(t1.id, "Patient 1")
    async_db_session.add_all([u1, p1])
    await async_db_session.flush()

    appt = models.Appointment(
        patient_id=p1.id,
        tenant_id=t1.id,
        date_time=datetime(2026, 11, 7, 10, 0),
        status="Scheduled",
    )
    async_db_session.add(appt)
    await async_db_session.commit()

    new_time = datetime(2026, 11, 7, 11, 0)
    await crud.update_appointment(
        db=async_db_session,
        appointment_id=appt.id,
        appointment=schemas.AppointmentUpdate(date_time=new_time, notes="rescheduled"),
        tenant_id=t1.id,
        current_user=u1,
    )

    audit_stmt = (
        select(models.AuditLog)
        .where(
            models.AuditLog.entity_type == "appointment",
            models.AuditLog.entity_id == appt.id,
            models.AuditLog.tenant_id == t1.id,
        )
    )
    audit_row = (await async_db_session.execute(audit_stmt)).scalars().first()
    assert audit_row is not None
    assert audit_row.action == "update"
    assert "date_time" in audit_row.old_value
    assert "date_time" in audit_row.new_value


@pytest.mark.asyncio
async def test_update_appointment_stale_data_error_raises_409(async_db_session):
    t1 = models.Tenant(name="Tenant 1", domain="t1-stale.test")
    async_db_session.add(t1)
    await async_db_session.flush()

    p1 = make_patient(t1.id, "Patient 1")
    async_db_session.add(p1)
    await async_db_session.flush()

    appt = models.Appointment(
        patient_id=p1.id,
        tenant_id=t1.id,
        date_time=datetime(2026, 11, 8, 10, 0),
        status="Scheduled",
    )
    async_db_session.add(appt)
    await async_db_session.commit()

    with patch.object(async_db_session, "commit", side_effect=StaleDataError()):
        with pytest.raises(HTTPException) as exc_info:
            await crud.update_appointment(
                db=async_db_session,
                appointment_id=appt.id,
                appointment=schemas.AppointmentUpdate(notes="concurrency test"),
                tenant_id=t1.id,
            )
        assert exc_info.value.status_code == 409
        assert "تم تعديله من مستخدم آخر" in exc_info.value.detail
