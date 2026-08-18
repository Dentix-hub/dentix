"""Finance regressions for historical event rows with NULL tenant_id."""

from datetime import datetime, timezone

import pytest

from backend import models
from backend.services.accounting_service import AccountingService
from backend.services.billing_service import BillingService


@pytest.mark.asyncio
async def test_patient_owned_legacy_null_event_tenant_rows_remain_in_totals(async_db_session):
    tenant_id = 149
    other_tenant_id = 150
    patient = models.Patient(
        id=1491,
        name="Legacy Finance Patient",
        age=36,
        phone="01014901490",
        medical_history="None",
        notes="Legacy NULL event tenant regression",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    other_patient = models.Patient(
        id=1501,
        name="Other Clinic Patient",
        age=37,
        phone="01015001500",
        medical_history="None",
        notes="Isolation fixture",
        tenant_id=other_tenant_id,
        is_deleted=False,
    )
    treatment = models.Treatment(
        id=1492,
        patient_id=patient.id,
        procedure="Legacy treatment",
        diagnosis="Caries",
        cost=1000.0,
        discount=100.0,
        date=datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc),
        tenant_id=None,
        is_deleted=False,
    )
    payment = models.Payment(
        id=1493,
        patient_id=patient.id,
        amount=400.0,
        date=datetime(2026, 8, 18, 11, 0, tzinfo=timezone.utc),
        tenant_id=None,
    )
    other_payment = models.Payment(
        id=1502,
        patient_id=other_patient.id,
        amount=9999.0,
        date=datetime(2026, 8, 18, 11, 0, tzinfo=timezone.utc),
        tenant_id=None,
    )
    async_db_session.add_all(
        [patient, other_patient, treatment, payment, other_payment]
    )
    await async_db_session.commit()

    service = AccountingService(async_db_session, tenant_id)
    start, end = service.parse_date_range("2026-08-18", "2026-08-18")
    assert await service.get_total_income(start, end) == 900.0
    assert await service.get_total_collected(start, end) == 400.0
    assert await BillingService(async_db_session, tenant_id).get_outstanding_balance() == 500.0
