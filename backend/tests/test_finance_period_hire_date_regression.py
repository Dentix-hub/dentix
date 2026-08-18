"""Regression coverage for employment-date-aware period compensation."""

from datetime import date

import pytest

from backend import models
from backend.services.accounting_service import AccountingService


@pytest.mark.asyncio
async def test_period_fixed_compensation_starts_on_hire_date(async_db_session):
    tenant_id = 152
    doctor = models.User(
        id=1521,
        username="mid_month_doctor",
        email="mid-month-doctor@example.com",
        hashed_password="h",
        role="doctor",
        tenant_id=tenant_id,
        fixed_salary=3100.0,
        commission_percent=0.0,
        hire_date=date(2026, 8, 16),
    )
    assistant = models.User(
        id=1522,
        username="mid_month_assistant",
        email="mid-month-assistant@example.com",
        hashed_password="h",
        role="assistant",
        tenant_id=tenant_id,
        fixed_salary=3100.0,
        per_appointment_fee=0.0,
        hire_date=date(2026, 8, 16),
    )
    async_db_session.add_all([doctor, assistant])
    await async_db_session.commit()

    service = AccountingService(async_db_session, tenant_id)

    month_start, month_end = service.parse_date_range("2026-08-01", "2026-08-31")
    doctor_row = next(
        row
        for row in await service.get_doctor_revenue_analytics(month_start, month_end)
        if row["doctor_id"] == doctor.id
    )
    assert doctor_row["fixed_salary_period"] == 1600.0
    assert doctor_row["total_due"] == 1600.0

    staff_rows, staff_total = await service.calculate_staff_dues(
        month_start,
        month_end,
        total_appointments=0,
    )
    staff_row = next(row for row in staff_rows if row["id"] == assistant.id)
    assert staff_row["fixed_salary_period"] == 1600.0
    assert staff_row["total_due"] == 1600.0
    assert staff_total == 1600.0

    before_hire_start, before_hire_end = service.parse_date_range(
        "2026-08-01",
        "2026-08-15",
    )
    doctor_before_hire = next(
        row
        for row in await service.get_doctor_revenue_analytics(
            before_hire_start,
            before_hire_end,
        )
        if row["doctor_id"] == doctor.id
    )
    assert doctor_before_hire["fixed_salary_period"] == 0.0
    assert doctor_before_hire["total_due"] == 0.0

    staff_before_hire, total_before_hire = await service.calculate_staff_dues(
        before_hire_start,
        before_hire_end,
        total_appointments=0,
    )
    assistant_before_hire = next(
        row for row in staff_before_hire if row["id"] == assistant.id
    )
    assert assistant_before_hire["fixed_salary_period"] == 0.0
    assert assistant_before_hire["total_due"] == 0.0
    assert total_before_hire == 0.0
