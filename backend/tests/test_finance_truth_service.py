"""Regression coverage for the Finance V2 truth boundary."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from backend import models
from backend.services.finance_summary_service import (
    CompensationSettingsService,
    FinanceSummaryService,
)


@pytest.mark.asyncio
async def test_current_patient_debt_keeps_patient_owned_legacy_null_tenant_rows(
    async_db_session,
):
    tenant_id = 201
    patient = models.Patient(
        id=2011,
        name="Legacy debt patient",
        age=40,
        phone="01020102011",
        medical_history="None",
        notes="Finance truth regression",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    other_patient = models.Patient(
        id=2012,
        name="Other tenant patient",
        age=41,
        phone="01020102012",
        medical_history="None",
        notes="Must remain isolated",
        tenant_id=202,
        is_deleted=False,
    )
    async_db_session.add_all(
        [
            patient,
            other_patient,
            models.Treatment(
                id=2013,
                patient_id=patient.id,
                procedure="Legacy crown",
                diagnosis="Missing tooth",
                cost=Decimal("1000.00"),
                discount=Decimal("100.00"),
                date=datetime(2026, 8, 10, 10, 0),
                tenant_id=None,
                is_deleted=False,
            ),
            models.Payment(
                id=2014,
                patient_id=patient.id,
                amount=Decimal("300.00"),
                date=datetime(2026, 8, 11, 10, 0),
                tenant_id=None,
            ),
            models.Treatment(
                id=2015,
                patient_id=other_patient.id,
                procedure="Other tenant treatment",
                diagnosis="Other",
                cost=Decimal("5000.00"),
                discount=Decimal("0.00"),
                date=datetime(2026, 8, 10, 10, 0),
                tenant_id=None,
                is_deleted=False,
            ),
        ]
    )
    await async_db_session.commit()

    service = FinanceSummaryService(async_db_session, tenant_id)

    assert await service.get_current_patient_debt() == Decimal("600.00")
    assert await service.get_current_patient_debt(patient_id=patient.id) == Decimal(
        "600.00"
    )
    assert await service.get_current_patient_debt(search="Legacy debt") == Decimal(
        "600.00"
    )


@pytest.mark.asyncio
async def test_summary_uses_one_period_contract_and_legacy_patient_ownership(
    async_db_session,
):
    tenant_id = 203
    tenant = models.Tenant(id=tenant_id, name="Finance Truth Clinic", timezone="Africa/Cairo")
    patient = models.Patient(
        id=2031,
        name="Period patient",
        age=35,
        phone="01020302031",
        medical_history="None",
        notes="Period contract regression",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    async_db_session.add_all(
        [
            tenant,
            patient,
            models.Treatment(
                id=2032,
                patient_id=patient.id,
                procedure="Period crown",
                diagnosis="Crown",
                cost=Decimal("1200.00"),
                discount=Decimal("200.00"),
                date=datetime(2026, 8, 15, 9, 0),
                tenant_id=None,
                is_deleted=False,
            ),
            models.Payment(
                id=2033,
                patient_id=patient.id,
                amount=Decimal("400.00"),
                date=datetime(2026, 8, 16, 9, 0),
                tenant_id=None,
            ),
        ]
    )
    await async_db_session.commit()

    service = FinanceSummaryService(async_db_session, tenant_id)
    summary = await service.get_summary(
        start_date="2026-08-01",
        end_date="2026-08-31",
    )

    assert summary["period"] == {
        "kind": "period",
        "scope": "period",
        "start": "2026-08-01",
        "end": "2026-08-31",
        "timezone": "Africa/Cairo",
    }
    assert summary["definition_version"] == "finance-summary-v1"
    assert summary["income"]["gross_revenue"] == 1200.0
    assert summary["income"]["total_discounts"] == 200.0
    assert summary["income"]["net_revenue"] == 1000.0
    assert summary["income"]["total_collected"] == 400.0
    assert summary["income"]["period_balance"] == 600.0
    assert summary["income"]["all_time_outstanding"] == 600.0
    assert summary["net_operational_result"] == summary["net_profit"]


@pytest.mark.asyncio
async def test_compensation_patch_preserves_omitted_fields_and_updates_hire_date(
    async_db_session,
):
    tenant_id = 204
    admin = models.User(
        id=2041,
        username="finance_truth_admin",
        email="finance-truth-admin@example.com",
        hashed_password="h",
        role="admin",
        tenant_id=tenant_id,
    )
    employee = models.User(
        id=2042,
        username="finance_truth_doctor",
        email="finance-truth-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=tenant_id,
        commission_percent=Decimal("25.0000"),
        fixed_salary=Decimal("3000.00"),
        per_appointment_fee=Decimal("75.00"),
        hire_date=date(2026, 1, 1),
    )
    async_db_session.add_all([admin, employee])
    await async_db_session.commit()

    result = await CompensationSettingsService(
        async_db_session,
        tenant_id,
    ).patch_settings(
        employee.id,
        admin,
        {
            "fixed_salary": Decimal("3500.00"),
            "hire_date": date(2026, 2, 1),
        },
    )

    await async_db_session.refresh(employee)
    assert result is not None
    assert result["updated_fields"] == ["fixed_salary", "hire_date"]
    assert employee.fixed_salary == Decimal("3500.00")
    assert employee.hire_date == date(2026, 2, 1)
    assert employee.commission_percent == Decimal("25.0000")
    assert employee.per_appointment_fee == Decimal("75.00")
