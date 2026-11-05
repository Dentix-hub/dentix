from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from backend import models, schemas
from backend.services.ai_quota_service import AIQuotaService
from backend.services.ai_service import AIService
from backend.services.commercial_action_service import CommercialActionService
from backend.services.reconciliation_service import ReconciliationService
from backend.ai.agent.core import get_agent
from backend.models.ai_accounting import AIQuotaWindow
from backend.routers.analytics_ai_v2 import analyze_clinic, ClinicStats
from starlette.requests import Request
from backend.auth import create_access_token


@pytest.fixture(autouse=True)
def enforced(monkeypatch):
    monkeypatch.setenv('SUBSCRIPTION_ENFORCEMENT_MODE', 'enforce')
    monkeypatch.setenv('AI_DISABLED', 'false')
    monkeypatch.delenv('GROQ_API_KEY', raising=False)


@pytest.fixture
def sample(db_session):
    plan = models.SubscriptionPlan(
        name='professional', display_name_ar='Synthetic Professional',
        price=Decimal('400.00'), duration_days=30, max_users=5,
        features='{"clinical":true,"billing":true,"ai_insights":true}',
        is_ai_enabled=True, ai_daily_limit=10, is_active=True,
    )
    db_session.add(plan)
    db_session.flush()
    tenant = models.Tenant(
        name='Synthetic review clinic', plan='professional', plan_id=plan.id,
        subscription_status='active', is_active=True,
        subscription_end_date=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(days=20),
        timezone='Africa/Cairo', policy_revision=1,
    )
    db_session.add(tenant)
    db_session.flush()
    user = models.User(
        username='synthetic_review_owner', email='owner@example.invalid',
        hashed_password='not-a-real-password-hash', role='admin',
        tenant_id=tenant.id, is_active=True, is_deleted=False,
    )
    admin = models.User(
        username='synthetic_review_superadmin', email='platform@example.invalid',
        hashed_password='not-a-real-password-hash', role='super_admin',
        is_active=True, is_deleted=False,
    )
    db_session.add_all([user,admin])
    db_session.commit()
    tenant.subscription_plan = plan
    user.tenant = tenant
    return SimpleNamespace(plan=plan,tenant=tenant,user=user,admin=admin)


@pytest.fixture
def provider(monkeypatch):
    agent=get_agent()
    monkeypatch.setattr(agent,'mock_mode',False)
    stub=AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Synthetic provider response'))]))
    monkeypatch.setattr(agent,'_call_llm_safe',stub)
    return stub


def test_admin_configured_ai_cap_is_authoritative(db_session,sample):
    sample.plan.ai_daily_limit=1
    db_session.commit()
    actual=AIQuotaService.get_effective_ai_daily_limit(db_session,sample.tenant.id)
    assert actual==1, f'Configured daily limit 1, quota service returned {actual}'


@pytest.mark.asyncio
async def test_persisted_emergency_stop_blocks_direct_provider(db_session,async_db_session,sample,provider):
    db_session.add(models.SystemSetting(key='emergency_restriction_ai_insights',value='true'))
    db_session.commit()
    sample.user.tenant=sample.tenant
    service=AIService(async_db_session,sample.user)
    response=await service.analyze_direct('Synthetic non-patient revenue commentary')
    assert provider.await_count==0, f'Emergency restriction persisted, provider dispatched {provider.await_count} times; success={response.success}'


@pytest.mark.asyncio
async def test_replayed_header_must_not_redispatch_provider(db_session,async_db_session,sample,provider):
    sample.plan.name='essential'
    sample.plan.ai_daily_limit=2
    sample.plan.max_users=2
    sample.tenant.plan='essential'
    db_session.commit()
    # Call the real endpoint function, real aggregation and real reservation ledger.
    # The only fake is the external provider transport.
    req=Request({'type':'http','method':'POST','path':'/api/v1/admin/ai/analyze-clinic','headers':[(b'x-idempotency-key',b'same-logical-user-request')]})
    stats=ClinicStats(revenue=0,breakdown={},total_costs=0,net_profit=0,margin_percent=0)
    for _ in range(3):
        _ = await analyze_clinic(stats=stats,request=req,db=async_db_session,current_user=sample.user)
    window=db_session.query(AIQuotaWindow).filter_by(tenant_id=sample.tenant.id).one()
    assert provider.await_count==1, f'Same header/payload dispatched provider {provider.await_count} times; ledger consumed={window.consumed_count}'


@pytest.mark.asyncio
async def test_reversing_old_suspend_cannot_undo_later_security_disable(async_db_session,sample):
    req=schemas.TenantCommercialActionRequest(reason='Synthetic review suspension')
    await CommercialActionService.suspend_tenant(async_db_session,sample.tenant.id,req,sample.admin)
    old_audit=(await async_db_session.execute(select(models.AuditLog).where(models.AuditLog.tenant_id==sample.tenant.id,models.AuditLog.action=='TENANT_COMMERCIAL_SUSPEND'))).scalar_one()
    await CommercialActionService.security_disable_tenant(async_db_session,sample.tenant.id,schemas.TenantCommercialActionRequest(reason='Later synthetic security disable'),sample.admin)
    reverse=schemas.PolicyReversalRequest(audit_log_id=old_audit.id,reason='Reverse only old commercial action')
    try:
        await CommercialActionService.reverse_policy_action(async_db_session,reverse,sample.admin)
    except Exception as exc:
        if getattr(exc,'status_code',None) not in (400,409):
            raise
    tenant=(await async_db_session.execute(select(models.Tenant).where(models.Tenant.id==sample.tenant.id))).scalar_one()
    assert tenant.is_active is False, 'Reversing older commercial suspension silently re-enabled later security-disabled clinic'


@pytest.mark.asyncio
async def test_reconcile_must_preserve_valid_retired_paid_contract(db_session,async_db_session,sample):
    retired=models.SubscriptionPlan(name='business',display_name_ar='Synthetic retired Business contract',price=Decimal('1000.00'),duration_days=30,max_users=15,is_ai_enabled=True,ai_daily_limit=30,features='{"clinical":true,"billing":true,"ai_insights":true}',is_active=False)
    db_session.add(retired)
    db_session.commit()
    old_id=retired.id
    sample.tenant.plan_id=old_id
    sample.tenant.plan=retired.name
    db_session.commit()
    await ReconciliationService.apply_reconciliation(async_db_session,admin_user=sample.admin)
    db_session.expire_all()
    actual=db_session.get(models.Tenant,sample.tenant.id)
    assert actual.plan_id==old_id, f'Valid retired paid contract {old_id} overwritten by active fallback plan {actual.plan_id}'


@pytest.mark.asyncio
async def test_reconciliation_reversal_restores_real_plan_anchor(db_session,async_db_session,sample):
    sample.tenant.subscription_plan=None
    sample.tenant.plan_id=None
    sample.tenant.plan='unmapped_synthetic_contract'
    db_session.commit()
    await ReconciliationService.apply_reconciliation(async_db_session,admin_user=sample.admin)
    audit=(await async_db_session.execute(select(models.AuditLog).where(models.AuditLog.tenant_id==sample.tenant.id,models.AuditLog.action=='TENANT_CATALOG_RECONCILE'))).scalar_one()
    before=sample.plan.name,sample.plan.id
    try:
        await CommercialActionService.reverse_policy_action(async_db_session,schemas.PolicyReversalRequest(audit_log_id=audit.id,reason='Synthetic explicit reversal'),sample.admin)
    except Exception as exc:
        if getattr(exc,'status_code',None) not in (400,409):
            raise
        db_session.expire_all()
        tenant=db_session.get(models.Tenant,sample.tenant.id)
        assert (tenant.plan,tenant.plan_id)==before, 'Rejected ambiguous reversal changed the persisted plan'
        return
    db_session.expire_all()
    tenant=db_session.get(models.Tenant,sample.tenant.id)
    assert (tenant.plan,tenant.plan_id)==('unmapped_synthetic_contract',None), f'Successful reversal left inconsistent plan={tenant.plan!r}, plan_id={tenant.plan_id!r}'


def _auth(sample):
    token=create_access_token(data={"sub":sample.user.username,"role":sample.user.role,"tenant_id":sample.tenant.id})
    return {"Authorization":f"Bearer {token}","X-Idempotency-Key":"same-http-logical-request"}


def test_http_emergency_denied_before_dispatch(db_session,client,sample,provider):
    db_session.add(models.SystemSetting(key="emergency_restriction_ai_insights",value="true"))
    db_session.commit()
    response=client.post("/api/v1/admin/ai/analyze-clinic",json={"revenue":0,"breakdown":{},"total_costs":0,"net_profit":0,"margin_percent":0},headers=_auth(sample))
    assert provider.await_count==0, f"Real HTTP status={response.status_code}; emergency restriction dispatched provider {provider.await_count} times"


def test_http_replay_cannot_dispatch_again(db_session,client,sample,provider):
    sample.plan.name='essential'
    sample.plan.ai_daily_limit=2
    sample.plan.max_users=2
    sample.tenant.plan='essential'
    db_session.commit()
    for _ in range(3):
        response=client.post("/api/v1/admin/ai/analyze-clinic",json={"revenue":0,"breakdown":{},"total_costs":0,"net_profit":0,"margin_percent":0},headers=_auth(sample))
        assert response.status_code==200, response.text
    window=db_session.query(AIQuotaWindow).filter_by(tenant_id=sample.tenant.id).one()
    assert provider.await_count==1, f"Real HTTP replays dispatched {provider.await_count} times with only {window.consumed_count} consumed quota unit"
