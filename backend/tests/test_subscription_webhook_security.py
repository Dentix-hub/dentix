import json
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend import models, schemas
from backend.routers import repair
from backend.services.subscription_service import SubscriptionService
from backend.services.webhook_service import WebhookService


WEBHOOK_SECRET = "subscription-webhook-test-secret-32-bytes-minimum"


async def _create_checkout(async_db_session):
    plan = models.SubscriptionPlan(
        name="secure-plan",
        display_name_ar="الخطة الآمنة",
        price=500.0,
        duration_days=30,
        is_active=True,
    )
    tenant = models.Tenant(name="Secure Checkout Clinic", is_active=False)
    async_db_session.add_all([plan, tenant])
    await async_db_session.commit()
    await async_db_session.refresh(plan)
    await async_db_session.refresh(tenant)

    checkout = await SubscriptionService.create_checkout_session(
        async_db_session,
        schemas.SubscriptionCheckoutCreate(
            tenant_id=tenant.id,
            plan_id=plan.id,
            provider="test-provider",
        ),
    )
    return tenant, plan, checkout


def _signed_event(checkout, tenant, plan, *, amount=500.0, payment_id="pay_123"):
    payload = {
        "provider": "test-provider",
        "provider_reference": checkout.provider_reference,
        "provider_payment_id": payment_id,
        "provider_status": "paid",
        "tenant_id": tenant.id,
        "plan_id": plan.id,
        "amount": amount,
        "currency": "EGP",
        "paid_by": "provider",
        "notes": "verified webhook",
    }
    raw_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    timestamp = datetime.now(timezone.utc).isoformat()
    signature = WebhookService(WEBHOOK_SECRET).generate_raw_signature(
        raw_payload, timestamp
    )
    return schemas.SubscriptionWebhookEvent(**payload), raw_payload, timestamp, signature


@pytest.mark.asyncio
async def test_webhook_requires_configured_signature(async_db_session, monkeypatch):
    tenant, plan, checkout = await _create_checkout(async_db_session)
    event, raw_payload, timestamp, _ = _signed_event(checkout, tenant, plan)
    monkeypatch.delenv("SUBSCRIPTION_WEBHOOK_SECRET", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        await SubscriptionService.handle_provider_webhook(
            async_db_session,
            event,
            raw_payload=raw_payload,
            timestamp=timestamp,
            signature="invalid",
        )

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_webhook_does_not_bypass_rls_before_signature_verification(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_WEBHOOK_SECRET", WEBHOOK_SECRET)

    class FailIfBypassed:
        def bypass_rls(self):
            raise AssertionError("RLS bypass started before signature verification")

    event = schemas.SubscriptionWebhookEvent(
        provider="test-provider",
        provider_reference="sub_unknown",
        provider_payment_id="pay_invalid_signature",
        provider_status="paid",
        tenant_id=1,
        plan_id=1,
        amount=500,
        currency="EGP",
    )

    with pytest.raises(HTTPException) as exc_info:
        await SubscriptionService.handle_provider_webhook(
            FailIfBypassed(),
            event,
            raw_payload=b"{}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            signature="invalid",
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_signed_webhook_is_bound_to_checkout_and_idempotent(
    async_db_session, monkeypatch
):
    monkeypatch.setenv("SUBSCRIPTION_WEBHOOK_SECRET", WEBHOOK_SECRET)
    tenant, plan, checkout = await _create_checkout(async_db_session)
    event, raw_payload, timestamp, signature = _signed_event(checkout, tenant, plan)

    payment = await SubscriptionService.handle_provider_webhook(
        async_db_session,
        event,
        raw_payload=raw_payload,
        timestamp=timestamp,
        signature=signature,
    )
    await async_db_session.refresh(tenant)
    first_end_date = tenant.subscription_end_date

    replay = await SubscriptionService.handle_provider_webhook(
        async_db_session,
        event,
        raw_payload=raw_payload,
        timestamp=timestamp,
        signature=signature,
    )
    await async_db_session.refresh(tenant)
    payment_count = await async_db_session.scalar(
        select(func.count(models.SubscriptionPayment.id))
    )

    assert replay.id == payment.id
    assert payment_count == 1
    assert tenant.subscription_end_date == first_end_date
    assert tenant.is_active is True


@pytest.mark.asyncio
async def test_signed_webhook_cannot_change_checkout_amount(
    async_db_session, monkeypatch
):
    monkeypatch.setenv("SUBSCRIPTION_WEBHOOK_SECRET", WEBHOOK_SECRET)
    tenant, plan, checkout = await _create_checkout(async_db_session)
    event, raw_payload, timestamp, signature = _signed_event(
        checkout, tenant, plan, amount=1.0
    )

    with pytest.raises(HTTPException) as exc_info:
        await SubscriptionService.handle_provider_webhook(
            async_db_session,
            event,
            raw_payload=raw_payload,
            timestamp=timestamp,
            signature=signature,
        )

    assert exc_info.value.status_code == 400
    assert await async_db_session.scalar(
        select(func.count(models.SubscriptionPayment.id))
    ) == 0


def test_repair_mutations_are_post_only_and_production_guarded(monkeypatch):
    methods_by_path = {
        route.path: route.methods for route in repair.router.routes if hasattr(route, "methods")
    }
    assert methods_by_path["/repair/schema"] == {"POST"}
    assert methods_by_path["/repair/reset-password"] == {"POST"}
    assert repair.router.dependencies

    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(HTTPException) as exc_info:
        repair._ensure_not_production()
    assert exc_info.value.status_code == 404
