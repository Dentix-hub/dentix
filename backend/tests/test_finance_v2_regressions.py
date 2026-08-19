"""Regression coverage for Finance V2 staging failures found during online validation."""

from datetime import datetime, timezone

import pytest

from backend import models
from backend.routers.metrics import get_profitability_trend
from backend.services.accounting_service import AccountingService
from backend.utils.tenant_time import tenant_local_date


@pytest.mark.asyncio
async def test_patient_reports_use_existing_patient_id_as_display_file_number(async_db_session):
    """Receivables must not depend on a non-existent patients.file_number DB column."""
    tenant_id = 130
    patient = models.Patient(
        id=1301,
        name="Finance Regression Patient",
        age=35,
        phone="01013001300",
        medical_history="None",
        notes="Regression fixture",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    treatment = models.Treatment(
        id=1302,
        patient_id=patient.id,
        diagnosis="Caries",
        procedure="Filling",
        cost=1000.0,
        discount=100.0,
        date=datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
        is_deleted=False,
    )
    payment = models.Payment(
        id=1303,
        patient_id=patient.id,
        amount=400.0,
        date=datetime(2026, 8, 11, 10, 0, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    async_db_session.add_all([patient, treatment, payment])
    await async_db_session.commit()

    assert patient.file_number == patient.id
    assert payment.patient_file_number == patient.id

    service = AccountingService(async_db_session, tenant_id=tenant_id)
    report = await service.get_patients_report(skip=0, limit=20)

    assert report["total"] == 1
    assert len(report["patients"]) == 1
    assert report["patients"][0]["file_number"] == patient.id
    assert report["patients"][0]["all_time_outstanding"] == 500.0

    details = await service.get_patient_financial_details(patient.id)
    assert details is not None
    assert details["file_number"] == patient.id
    assert details["outstanding_balance"] == 500.0


@pytest.mark.asyncio
async def test_profitability_trend_returns_tenant_scoped_daily_series(async_db_session):
    """The Finance Overview trend route must exist and isolate tenant cash movements."""
    tenant_id = 131
    other_tenant_id = 132
    now_utc = datetime.now(timezone.utc)
    tenant_today = tenant_local_date("Africa/Cairo")

    admin = models.User(
        id=1311,
        username="finance_trend_admin",
        email="finance-trend-admin@example.com",
        hashed_password="h",
        role="admin",
        tenant_id=tenant_id,
    )
    patient = models.Patient(
        id=1312,
        name="Trend Patient",
        age=40,
        phone="01013101310",
        medical_history="None",
        notes="Trend fixture",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    other_patient = models.Patient(
        id=1322,
        name="Other Tenant Patient",
        age=41,
        phone="01013201320",
        medical_history="None",
        notes="Isolation fixture",
        tenant_id=other_tenant_id,
        is_deleted=False,
    )
    payment = models.Payment(
        id=1313,
        patient_id=patient.id,
        amount=1000.0,
        date=now_utc,
        tenant_id=tenant_id,
    )
    expense = models.Expense(
        id=1314,
        item_name="Supplies",
        cost=200.0,
        category="Supplies",
        date=tenant_today,
        tenant_id=tenant_id,
    )
    other_payment = models.Payment(
        id=1323,
        patient_id=other_patient.id,
        amount=9999.0,
        date=now_utc,
        tenant_id=other_tenant_id,
    )
    other_expense = models.Expense(
        id=1324,
        item_name="Other expense",
        cost=9999.0,
        category="Other",
        date=tenant_today,
        tenant_id=other_tenant_id,
    )
    async_db_session.add_all(
        [admin, patient, other_patient, payment, expense, other_payment, other_expense]
    )
    await async_db_session.commit()

    response = await get_profitability_trend(
        period="7d",
        db=async_db_session,
        current_user=admin,
    )

    data = response["data"]
    assert data["period"] == "7d"
    assert len(data["timeline"]) == 7

    today_row = next(
        item for item in data["timeline"] if item["date"] == tenant_today.isoformat()
    )
    assert today_row["revenue"] == 1000.0
    assert today_row["expenses"] == 200.0
    assert today_row["net_profit"] == 800.0
