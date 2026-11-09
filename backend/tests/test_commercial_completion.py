from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from backend.tests import test_commercial_release_hardening as fixtures

sample = fixtures.sample
provider = fixtures.provider
enforced = fixtures.enforced
_auth = fixtures._auth
from backend import models, schemas
from backend.auth import create_access_token
from backend.services.ai_quota_service import AIQuotaService
from backend.services.ai_service import AIService
from backend.services.scribe_service import ScribeService
from backend.services.commercial_action_service import CommercialActionService
from backend.services.subscription_service import SubscriptionService
from backend.models.ai_accounting import AIQuotaWindow, ReservationStatus
from backend.routers.analytics_ai_v2 import ClinicStats


def _essential(db, s):
    s.plan.name = "essential"
    s.plan.max_users = 2
    s.plan.ai_daily_limit = 2
    s.tenant.plan = "essential"
    db.commit()


def test_chat_http_replay_dispatches_once(db_session, client, sample, provider):
    _essential(db_session, sample)
    headers = _auth(sample)
    headers["X-Idempotency-Key"] = "same-chat-logical-request"
    for _ in range(3):
        response = client.post(
            "/api/v1/ai/query",
            json={
                "text": "Explain general clinic efficiency without individual patient information.",
                "context": [],
            },
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["success"], response.text
    window = db_session.query(AIQuotaWindow).filter_by(tenant_id=sample.tenant.id).one()
    assert provider.await_count == 1, (
        f"Chat provider calls={provider.await_count}, consumed={window.consumed_count}, cap=2"
    )


def test_scribe_replay_dispatches_once(db_session, sample, monkeypatch):
    _essential(db_session, sample)
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    svc = ScribeService()
    transport = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content='{"procedures":[]}'))
            ]
        )
    )
    svc.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=transport))
    )
    for _ in range(3):
        svc.analyze_dictation(
            "Describe routine dental cleaning.",
            tenant_id=sample.tenant.id,
            user_id=sample.user.id,
            idempotency_key="same-scribe-logical-request",
            session=db_session,
        )
    window = db_session.query(AIQuotaWindow).filter_by(tenant_id=sample.tenant.id).one()
    assert transport.call_count == 1, (
        f"Scribe provider calls={transport.call_count}, consumed={window.consumed_count}, cap=2"
    )


def test_disabled_zero_plan_has_zero_ledger_limit(db_session, sample):
    sample.plan.is_ai_enabled = False
    sample.plan.ai_daily_limit = 0
    db_session.commit()
    actual = AIQuotaService.get_effective_ai_daily_limit(db_session, sample.tenant.id)
    assert actual == 0, f"Persisted disabled/zero policy returned quota={actual}"


def test_uncertain_replay_does_not_claim_completed_insights(
    db_session, client, sample, provider
):
    stats = ClinicStats(
        revenue=0, breakdown={}, total_costs=0, net_profit=0, margin_percent=0
    )
    payload = stats.model_dump()
    reservation = AIQuotaService.reserve_quota(
        db_session,
        tenant_id=sample.tenant.id,
        user_id=sample.user.id,
        operation="analyze_clinic",
        payload=payload,
        idempotency_key="uncertain-existing-request",
    )
    AIQuotaService.finalize_reservation(
        db_session,
        reservation_id=reservation.reservation_id,
        status=ReservationStatus.UNCERTAIN,
        reconciliation_notes="Synthetic timeout: provider outcome is unknown.",
    )
    headers = _auth(sample)
    headers["X-Idempotency-Key"] = "uncertain-existing-request"
    response = client.post(
        "/api/v1/admin/ai/analyze-clinic", json=payload, headers=headers
    )
    body = response.json()
    completed = (
        response.status_code == 200
        and isinstance(body.get("data"), dict)
        and "insights" in body["data"]
    )
    assert not completed, (
        f"UNCERTAIN returned completed insights: status={response.status_code}, body={body}"
    )
    assert provider.await_count == 0


def test_bulk_apply_requires_explicit_mapping(db_session, client, sample):
    sample.tenant.subscription_plan = None
    sample.tenant.plan_id = None
    sample.tenant.plan = "unknown_unreviewed_synthetic_contract"
    db_session.commit()
    token = create_access_token(
        data={"sub": sample.admin.username, "role": "super_admin", "tenant_id": None}
    )
    response = client.post(
        "/api/v1/admin/subscriptions/reconcile-tenants",
        headers={"Authorization": f"Bearer {token}"},
    )
    db_session.expire_all()
    tenant = db_session.get(models.Tenant, sample.tenant.id)
    assert tenant.plan_id is None, (
        f"No reviewed mapping/revision/reason submitted, HTTP {response.status_code} assigned plan_id={tenant.plan_id}"
    )


@pytest.mark.asyncio
async def test_override_reversal_restores_real_override(async_db_session, sample):
    update = schemas.TenantCommercialOverridesUpdateRequest(
        expected_revision=1,
        reason="Synthetic denial for review",
        overrides=[
            schemas.CommercialOverrideItem(
                capability_key="ai_insights", override_value="deny"
            )
        ],
    )
    await SubscriptionService.update_tenant_commercial_overrides(
        async_db_session, sample.tenant.id, update, sample.admin
    )
    audit = (
        await async_db_session.execute(
            select(models.AuditLog).where(
                models.AuditLog.tenant_id == sample.tenant.id,
                models.AuditLog.action == "TENANT_COMMERCIAL_OVERRIDES_UPDATE",
            )
        )
    ).scalar_one()
    try:
        response = await CommercialActionService.reverse_policy_action(
            async_db_session,
            schemas.PolicyReversalRequest(
                audit_log_id=audit.id, reason="Restore previous inherited policy"
            ),
            sample.admin,
        )
    except Exception as exc:
        if getattr(exc, "status_code", None) not in (400, 409):
            raise
        return
    rows = (
        (
            await async_db_session.execute(
                select(models.CommercialTenantOverride).where(
                    models.CommercialTenantOverride.tenant_id == sample.tenant.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert not rows, (
        f"Reversal claimed success ({response.action_reversed}) but persisted overrides remain: {[(x.capability_key, x.override_value) for x in rows]}"
    )


@pytest.mark.asyncio
async def test_override_store_error_fails_closed(
    db_session, async_db_session, sample, provider, monkeypatch
):
    db_session.add(
        models.CommercialTenantOverride(
            tenant_id=sample.tenant.id,
            capability_key="ai_insights",
            override_value="deny",
            reason="Persisted synthetic tenant denial",
        )
    )
    db_session.commit()
    sample.user.tenant = sample.tenant
    real_execute = async_db_session.execute

    async def policy_store_fault(statement, *args, **kwargs):
        if "commercial_tenant_overrides" in str(statement):
            raise RuntimeError("Synthetic policy store timeout")
        return await real_execute(statement, *args, **kwargs)

    monkeypatch.setattr(async_db_session, "execute", policy_store_fault)
    response = await AIService(async_db_session, sample.user).analyze_direct(
        "Synthetic financial summary without patient information"
    )
    assert provider.await_count == 0, (
        f"Tenant policy lookup failed, provider called={provider.await_count}, success={response.success}"
    )


@pytest.mark.asyncio
async def test_superseded_security_reversal_conflicts(async_db_session, sample):
    await CommercialActionService.security_disable_tenant(
        async_db_session,
        sample.tenant.id,
        schemas.TenantCommercialActionRequest(reason="First security disable"),
        sample.admin,
    )
    audit = (
        await async_db_session.execute(
            select(models.AuditLog).where(
                models.AuditLog.tenant_id == sample.tenant.id,
                models.AuditLog.action == "TENANT_SECURITY_DISABLE",
            )
        )
    ).scalar_one()
    old_id = audit.id
    await CommercialActionService.reactivate_tenant(
        async_db_session,
        sample.tenant.id,
        schemas.TenantCommercialActionRequest(reason="Explicit later reactivation"),
        sample.admin,
    )
    await CommercialActionService.security_disable_tenant(
        async_db_session,
        sample.tenant.id,
        schemas.TenantCommercialActionRequest(reason="Newer security incident disable"),
        sample.admin,
    )
    try:
        await CommercialActionService.reverse_policy_action(
            async_db_session,
            schemas.PolicyReversalRequest(
                audit_log_id=old_id, reason="Reverse only the obsolete first event"
            ),
            sample.admin,
        )
    except Exception as exc:
        if getattr(exc, "status_code", None) not in (400, 409):
            raise
    tenant = (
        await async_db_session.execute(
            select(models.Tenant).where(models.Tenant.id == sample.tenant.id)
        )
    ).scalar_one()
    assert tenant.is_active is False, (
        "Reversing obsolete disable event undid a newer security disable without revision conflict"
    )


@pytest.mark.asyncio
async def test_explicit_reconciliation_rejects_stale_revision_without_writes(
    db_session, async_db_session, sample
):
    sample.tenant.subscription_plan = None
    sample.tenant.plan_id = None
    db_session.commit()
    from backend.services.reconciliation_service import ReconciliationService

    selection = schemas.ReconciliationApplyRequest(
        reason="Reviewed synthetic mapping",
        mappings=[
            schemas.ReconciliationSelection(
                tenant_id=sample.tenant.id,
                plan_id=sample.plan.id,
                expected_revision=999,
                expected_plan_id=None,
            )
        ],
    )
    with pytest.raises(Exception) as exc:
        await ReconciliationService.apply_reconciliation(
            async_db_session, sample.admin, selection
        )
    assert exc.value.status_code == 409
    db_session.expire_all()
    assert db_session.get(models.Tenant, sample.tenant.id).plan_id is None


def test_scribe_child_retry_keeps_cached_result(db_session, sample, monkeypatch):
    monkeypatch.setenv("EXTERNAL_AI_PHI_MODE", "deidentified")
    parent = AIQuotaService.reserve_quota(
        db_session, sample.tenant.id, sample.user.id, "ai_chat", "synthetic parent"
    )
    service = ScribeService()
    transport = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content='{"procedures":[]}'))
            ]
        )
    )
    service.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=transport))
    )
    for _ in range(3):
        assert (
            service.analyze_dictation(
                "Routine cleaning",
                tenant_id=sample.tenant.id,
                user_id=sample.user.id,
                parent_reservation_id=parent.reservation_id,
                session=db_session,
            )
            == []
        )
    assert transport.call_count == 1


def test_quota_requires_plan_anchor_and_uses_started_future_period(db_session, sample):
    from datetime import datetime, timedelta

    sample.tenant.subscription_plan = None
    sample.tenant.plan_id = None
    db_session.commit()
    assert (
        AIQuotaService.get_effective_ai_daily_limit(db_session, sample.tenant.id) == 0
    )
    future = models.SubscriptionPlan(
        name="future_custom",
        display_name_ar="Synthetic",
        price=200,
        is_ai_enabled=True,
        ai_daily_limit=2,
    )
    db_session.add(future)
    db_session.flush()
    now = datetime.utcnow()
    sample.tenant.plan_id = sample.plan.id
    sample.tenant.future_plan_id = future.id
    sample.tenant.future_plan_start_date = now + timedelta(days=1)
    db_session.commit()
    assert (
        AIQuotaService.get_effective_ai_daily_limit(db_session, sample.tenant.id, now)
        == 10
    )
    assert (
        AIQuotaService.get_effective_ai_daily_limit(
            db_session, sample.tenant.id, now + timedelta(days=2)
        )
        == 2
    )
