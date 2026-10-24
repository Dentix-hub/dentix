"""
Real PostgreSQL concurrency gate for appointments:
Advisory Lock Serialization and Interval Conflict Detection.

Proves:
1. Two concurrent requests attempting to reschedule different appointments
   for the same doctor into the same overlapping time interval cannot both succeed.
   Exactly one succeeds and the other raises HTTP 409 (Appointment conflict).
2. Database invariants hold: only one active appointment exists for the doctor at that time slot.
"""

import asyncio
from datetime import datetime, timezone
from fastapi import HTTPException
import pytest
from sqlalchemy import select

from backend import models, schemas
from backend.crud import appointment as appointment_crud
from backend.database import AsyncSessionLocal, RlsContext

TENANT_APPT = 99831
USER_APPT_ID = 998310
DOCTOR_APPT_ID = 998311
PATIENT_APPT_ID = 998312
APPT_1_ID = 998313
APPT_2_ID = 998314


async def _seed() -> None:
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            if await db.get(models.Tenant, TENANT_APPT) is None:
                tenant = models.Tenant(
                    id=TENANT_APPT,
                    name="Appointment Concurrency Postgres Tenant",
                    is_active=True,
                )
                db.add(tenant)
                await db.flush()

                user = models.User(
                    id=USER_APPT_ID,
                    tenant_id=TENANT_APPT,
                    username="concurrency_user_appt",
                    email="concurrency_appt@example.com",
                    hashed_password="fakepassword",
                    role="admin",
                    is_active=True,
                )
                doctor = models.User(
                    id=DOCTOR_APPT_ID,
                    tenant_id=TENANT_APPT,
                    username="concurrency_doc_appt",
                    email="concurrency_doc@example.com",
                    hashed_password="fakepassword",
                    role="doctor",
                    is_active=True,
                )
                db.add_all([user, doctor])
                await db.flush()

                patient = models.Patient(
                    id=PATIENT_APPT_ID,
                    tenant_id=TENANT_APPT,
                    name="Patient Concurrency Appt",
                    age=28,
                    phone="01099831001",
                    medical_history="",
                    notes="",
                )
                db.add(patient)
                await db.flush()

            # Clean up or ensure initial appointments for test
            stmt = select(models.Appointment).where(
                models.Appointment.id.in_([APPT_1_ID, APPT_2_ID])
            )
            existing = (await db.execute(stmt)).scalars().all()
            for appt in existing:
                await db.delete(appt)
            await db.flush()

            appt1 = models.Appointment(
                id=APPT_1_ID,
                patient_id=PATIENT_APPT_ID,
                tenant_id=TENANT_APPT,
                doctor_id=DOCTOR_APPT_ID,
                date_time=datetime(2026, 12, 1, 9, 0),
                duration_minutes=30,
                status="Scheduled",
            )
            appt2 = models.Appointment(
                id=APPT_2_ID,
                patient_id=PATIENT_APPT_ID,
                tenant_id=TENANT_APPT,
                doctor_id=DOCTOR_APPT_ID,
                date_time=datetime(2026, 12, 1, 14, 0),
                duration_minutes=30,
                status="Scheduled",
            )
            db.add_all([appt1, appt2])
            await db.commit()


@pytest.mark.asyncio
async def test_concurrent_reschedules_to_same_slot_serialize_and_reject_one():
    """
    Two concurrent attempts to reschedule appt1 and appt2 to 10:00 AM on the same day
    for the same doctor.
    With PostgreSQL advisory locking and interval conflict checking, exactly one
    must succeed and one must be rejected with 409.
    """
    await _seed()

    target_slot = datetime(2026, 12, 1, 10, 0)
    update_payload = schemas.AppointmentUpdate(date_time=target_slot, duration_minutes=30)

    async def reschedule(appt_id: int):
        async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_APPT)) as session:
            try:
                res = await appointment_crud.update_appointment(
                    db=session,
                    appointment_id=appt_id,
                    appointment=update_payload,
                    tenant_id=TENANT_APPT,
                )
                return ("success", res.id)
            except HTTPException as exc:
                return ("conflict", exc.status_code, exc.detail)

    res1, res2 = await asyncio.gather(
        reschedule(APPT_1_ID),
        reschedule(APPT_2_ID),
    )

    statuses = [res1[0], res2[0]]
    assert "success" in statuses, f"Expected at least one success, got {res1}, {res2}"
    assert "conflict" in statuses, f"Expected one 409 conflict, got {res1}, {res2}"

    conflict_res = res1 if res1[0] == "conflict" else res2
    assert conflict_res[1] == 409
    assert "conflict" in conflict_res[2].lower()

    # Verify database state has only 1 appointment at target_slot
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_APPT)) as session:
        stmt = select(models.Appointment).where(
            models.Appointment.tenant_id == TENANT_APPT,
            models.Appointment.doctor_id == DOCTOR_APPT_ID,
            models.Appointment.date_time == target_slot,
            models.Appointment.is_deleted == False,  # noqa: E712
        )
        appts_at_slot = (await session.execute(stmt)).scalars().all()
        assert len(appts_at_slot) == 1
