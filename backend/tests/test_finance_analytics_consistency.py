"""Regression tests for AI/admin analytics sharing Finance V2 semantics."""

from datetime import timedelta

import pytest

from backend import models
from backend.services.analytics_service import AnalyticsService
from backend.services.tenant_time_service import get_tenant_time_context


@pytest.mark.asyncio
async def test_doctor_ranking_uses_net_active_production(async_db_session):
    tenant_id = 155
    doctor = models.User(
        id=1551,
        username="analytics_doctor",
        email="analytics-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=tenant_id,
    )
    patient = models.Patient(
        id=1552,
        name="Analytics Patient",
        age=35,
        phone="01015501550",
        medical_history="None",
        notes="Analytics finance regression",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    context = await get_tenant_time_context(async_db_session, tenant_id)
    event_time = context.utc_start + timedelta(hours=1)
    active = models.Treatment(
        id=1553,
        patient_id=patient.id,
        doctor_id=doctor.id,
        procedure="Active",
        diagnosis="A",
        cost=1000.0,
        discount=100.0,
        date=event_time,
        tenant_id=tenant_id,
        is_deleted=False,
    )
    deleted = models.Treatment(
        id=1554,
        patient_id=patient.id,
        doctor_id=doctor.id,
        procedure="Deleted",
        diagnosis="D",
        cost=5000.0,
        discount=0.0,
        date=event_time,
        tenant_id=tenant_id,
        is_deleted=True,
    )
    async_db_session.add_all([doctor, patient, active, deleted])
    await async_db_session.commit()

    result = await AnalyticsService(async_db_session, tenant_id).get_doctor_ranking(
        "today",
        "revenue",
    )
    assert result["ranking"] == [{"name": doctor.username, "value": 900.0}]


@pytest.mark.asyncio
async def test_ai_dashboard_today_uses_tenant_business_day(async_db_session):
    tenant_id = 156
    patient = models.Patient(
        id=1561,
        name="Analytics Boundary Patient",
        age=35,
        phone="01015601560",
        medical_history="None",
        notes="Analytics boundary regression",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    context = await get_tenant_time_context(async_db_session, tenant_id)
    included = models.Payment(
        id=1562,
        patient_id=patient.id,
        amount=700.0,
        date=context.utc_start + timedelta(minutes=30),
        tenant_id=tenant_id,
    )
    excluded = models.Payment(
        id=1563,
        patient_id=patient.id,
        amount=900.0,
        date=context.utc_end + timedelta(minutes=30),
        tenant_id=tenant_id,
    )
    async_db_session.add_all([patient, included, excluded])
    await async_db_session.commit()

    result = await AnalyticsService(async_db_session, tenant_id).get_dashboard_summary("today")
    assert result["period_revenue"] == 700.0
