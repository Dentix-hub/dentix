"""Fresh startup must use the approved catalog without rewriting existing contracts."""

from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend import models
from backend.core import seeding
from backend.services.subscription_service import SubscriptionService


APPROVED = {
    "essential": (Decimal("200.00"), 2, 2),
    "professional": (Decimal("400.00"), 5, 10),
    "business": (Decimal("1000.00"), 15, 30),
}


def assert_catalog(plans):
    assert {p.name: (p.price, p.max_users, p.ai_daily_limit) for p in plans} == APPROVED
    for p in plans:
        assert p.billing_cycle_unit == "month"
        assert p.is_active is True
        assert p.is_ai_enabled is True
        assert p.max_patients is None
        assert p.is_default is (p.name == "professional")


@pytest.mark.asyncio
async def test_actual_startup_seed_provides_professional_trial(
    async_db_session, monkeypatch
):
    monkeypatch.setenv("ENVIRONMENT", "test")
    await seeding.seed_default_data(async_db_session)
    policy = await SubscriptionService.get_trial_policy(async_db_session)
    assert policy.trial_plan_id is not None, (
        "Fresh startup leaves registration without its configured Professional trial"
    )
    assert policy.trial_plan_name == "professional"
    assert policy.trial_duration_days == 14
    assert policy.is_card_required is False
    plans = (
        (await async_db_session.execute(select(models.SubscriptionPlan)))
        .scalars()
        .all()
    )
    assert_catalog(plans)
    await seeding.seed_default_data(async_db_session)
    assert_catalog(
        (await async_db_session.execute(select(models.SubscriptionPlan)))
        .scalars()
        .all()
    )


@pytest.mark.asyncio
async def test_alternate_async_seed_uses_same_approved_catalog(
    async_db_session, monkeypatch
):
    @asynccontextmanager
    async def session():
        yield async_db_session

    monkeypatch.setattr(seeding.database, "system_session_scope", session)
    await seeding.seed_subscription_plans()
    assert_catalog(
        (await async_db_session.execute(select(models.SubscriptionPlan)))
        .scalars()
        .all()
    )


@pytest.mark.asyncio
async def test_startup_preserves_existing_retired_contract_and_history(
    async_db_session, monkeypatch
):
    monkeypatch.setenv("ENVIRONMENT", "test")
    plan = models.SubscriptionPlan(
        name="pro",
        display_name_ar="Synthetic retired contract",
        price=Decimal("123.45"),
        max_users=7,
        is_active=False,
        features='{"clinical":false}',
    )
    async_db_session.add(plan)
    await async_db_session.flush()
    tenant = models.Tenant(
        name="Synthetic existing clinic",
        plan_id=plan.id,
        plan="pro",
        is_active=False,
        subscription_status="active",
        subscription_end_date=datetime(2027, 1, 31),
    )
    async_db_session.add(tenant)
    await async_db_session.flush()
    patient = models.Patient(name="Synthetic history", tenant_id=tenant.id)
    receipt = models.SubscriptionPayment(
        tenant_id=tenant.id,
        plan_id=plan.id,
        amount=Decimal("123.45"),
        payment_method="test",
    )
    async_db_session.add_all([patient, receipt])
    await async_db_session.flush()
    await seeding.seed_default_data(async_db_session)
    await async_db_session.refresh(plan)
    await async_db_session.refresh(tenant)
    assert (plan.price, plan.max_users, plan.is_active, plan.features) == (
        Decimal("123.45"),
        7,
        False,
        '{"clinical":false}',
    )
    assert (
        tenant.plan_id,
        tenant.plan,
        tenant.subscription_end_date,
        tenant.is_active,
    ) == (plan.id, "pro", datetime(2027, 1, 31), False)
    plans = (
        (await async_db_session.execute(select(models.SubscriptionPlan)))
        .scalars()
        .all()
    )
    assert [p.id for p in plans] == [plan.id]
    assert (
        await SubscriptionService.get_trial_policy(async_db_session)
    ).trial_plan_id is None
    assert (
        await async_db_session.execute(
            select(models.Patient.id).where(models.Patient.tenant_id == tenant.id)
        )
    ).scalar_one() == patient.id
    assert (
        await async_db_session.execute(
            select(models.SubscriptionPayment.amount).where(
                models.SubscriptionPayment.tenant_id == tenant.id
            )
        )
    ).scalar_one() == Decimal("123.45")
