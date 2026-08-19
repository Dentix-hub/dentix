"""Regression tests for tenant-local Finance Overview trend ranges."""

from datetime import datetime, timezone

import pytest

from backend import models
from backend.routers.metrics import get_profitability_trend


@pytest.mark.asyncio
async def test_profitability_trend_uses_exact_cairo_day_range(async_db_session):
    tenant_id = 148
    admin = models.User(
        id=1481,
        username="trend_admin",
        email="trend-admin-148@example.com",
        hashed_password="h",
        role="admin",
        tenant_id=tenant_id,
    )
    patient = models.Patient(
        id=1482,
        name="Trend Cairo Patient",
        age=35,
        phone="01014801480",
        medical_history="None",
        notes="Trend regression fixture",
        tenant_id=tenant_id,
        is_deleted=False,
    )
    # 21:30 UTC on Aug 17 is 00:30 on Aug 18 in Cairo and belongs in the range.
    included = models.Payment(
        id=1483,
        patient_id=patient.id,
        amount=700.0,
        date=datetime(2026, 8, 17, 21, 30, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    # 21:30 UTC on Aug 18 is 00:30 on Aug 19 in Cairo and must be excluded.
    excluded = models.Payment(
        id=1484,
        patient_id=patient.id,
        amount=900.0,
        date=datetime(2026, 8, 18, 21, 30, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    expense = models.Expense(
        id=1485,
        item_name="Same-day expense",
        cost=200.0,
        category="Supplies",
        date=datetime(2026, 8, 18).date(),
        tenant_id=tenant_id,
    )
    async_db_session.add_all([admin, patient, included, excluded, expense])
    await async_db_session.commit()

    response = await get_profitability_trend(
        period="30d",
        start_date="2026-08-18",
        end_date="2026-08-18",
        db=async_db_session,
        current_user=admin,
    )
    data = response["data"]
    assert data["start_date"] == "2026-08-18"
    assert data["end_date"] == "2026-08-18"
    assert len(data["timeline"]) == 1
    assert data["timeline"][0] == {
        "date": "2026-08-18",
        "revenue": 700.0,
        "expenses": 200.0,
        "net_profit": 500.0,
    }
