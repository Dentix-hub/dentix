"""Regression coverage for LabOrder provider attribution."""

from datetime import datetime

import pytest

from backend import models
from backend.routers.laboratories import _resolve_lab_provider_id


@pytest.mark.asyncio
async def test_nurse_uses_assigned_doctor_instead_of_becoming_financial_provider(async_db_session):
    tenant_id = 176
    doctor = models.User(
        id=1761,
        username="lab_assigned_doctor",
        email="lab-assigned-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=tenant_id,
        is_active=True,
        is_deleted=False,
    )
    nurse = models.User(
        id=1762,
        username="lab_order_nurse",
        email="lab-order-nurse@example.com",
        hashed_password="h",
        role="nurse",
        tenant_id=tenant_id,
        is_active=True,
        is_deleted=False,
    )
    patient = models.Patient(
        id=1763,
        name="Assigned Lab Patient",
        age=30,
        phone="01017601760",
        medical_history="None",
        notes="Lab provider regression",
        tenant_id=tenant_id,
        assigned_doctor_id=doctor.id,
        is_deleted=False,
    )
    async_db_session.add_all([doctor, nurse, patient])
    await async_db_session.commit()

    resolved = await _resolve_lab_provider_id(async_db_session, nurse, patient)

    assert resolved == doctor.id
    assert resolved != nurse.id


@pytest.mark.asyncio
async def test_staff_falls_back_to_latest_real_provider_when_patient_unassigned(async_db_session):
    tenant_id = 177
    doctor = models.User(
        id=1771,
        username="lab_recent_doctor",
        email="lab-recent-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=tenant_id,
        is_active=True,
        is_deleted=False,
    )
    nurse = models.User(
        id=1772,
        username="lab_recent_nurse",
        email="lab-recent-nurse@example.com",
        hashed_password="h",
        role="nurse",
        tenant_id=tenant_id,
        is_active=True,
        is_deleted=False,
    )
    patient = models.Patient(
        id=1773,
        name="Recent Provider Patient",
        age=34,
        phone="01017701770",
        medical_history="None",
        notes="Latest provider regression",
        tenant_id=tenant_id,
        assigned_doctor_id=None,
        is_deleted=False,
    )
    treatment = models.Treatment(
        id=1774,
        patient_id=patient.id,
        doctor_id=doctor.id,
        diagnosis="Dx",
        procedure="Crown preparation",
        cost=500.0,
        discount=0.0,
        date=datetime(2026, 8, 18, 9, 0),
        tenant_id=tenant_id,
        is_deleted=False,
    )
    async_db_session.add_all([doctor, nurse, patient, treatment])
    await async_db_session.commit()

    resolved = await _resolve_lab_provider_id(async_db_session, nurse, patient)

    assert resolved == doctor.id
    assert resolved != nurse.id
