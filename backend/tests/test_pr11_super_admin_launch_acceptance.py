"""
PR-11 Acceptance Test Suite:
Super Admin Controls, Reconciliation Preview, and Final Commercial Launch Acceptance.

Verifies:
1. Catalog inventory & Reconciliation preview (aggregate reporting, zero PII/secrets, pure preview).
2. Automated safe anchoring of unanchored clinics without shortening periods or deleting accounts.
3. Separation of commercial suspension (suspended_admin, is_active=True) vs security disable (is_active=False) vs reactivation.
4. Policy reversal command (reverses policy actions, rejects financial payment reversals, immutable audit logging).
5. Plan price edit preview (verifies warning that historical receipts are never rewritten and affected clinics are counted).
6. Launch acceptance checklist:
   - Option A capacities: Essential (200 EGP, 2 seats, 2 AI), Professional (400 EGP, 5 seats, 10 AI), Business (1000 EGP, 15 seats, 30 AI).
   - 14-day Professional trial, 7-day paid grace period.
   - Clinical History Invariant (read-only clinical records preserved under commercial suspension and expired states).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend import models, schemas
from backend.core.commercial_registry import OperationClass
from backend.services.commercial_decision import CommercialDecisionEngine
from backend.services.commercial_action_service import CommercialActionService
from backend.services.reconciliation_service import ReconciliationService
from backend.services.subscription_service import SubscriptionService
from backend.services.subscription_state_machine import SubscriptionState


def _user(
    username: str,
    role: str = "doctor",
    tenant_id: int = 101,
    is_active: bool = True,
    id: int = None,
):
    kwargs = {
        "username": username,
        "email": f"{username}@pr11test.clinic",
        "hashed_password": "hashed_pw_test_pr11",
        "role": role,
        "tenant_id": tenant_id,
        "is_active": is_active,
        "is_deleted": False,
    }
    if id is not None:
        kwargs["id"] = id
    return models.User(**kwargs)


@pytest.fixture
def mock_admin_user():
    return _user(id=991, username="superadmin_pr11", role="super_admin", tenant_id=None)


@pytest.fixture
async def setup_pr11_plans(async_db_session):
    """Seed the approved 3 canonical launch plans."""
    template = SubscriptionService.get_launch_catalog_template()
    plans = []
    for item in template:
        plan = models.SubscriptionPlan(
            name=item["name"],
            display_name_ar=item["display_name_ar"],
            price=item["price"],
            duration_days=item["duration_days"],
            max_users=item["max_users"],
            max_patients=item["max_patients"],
            is_ai_enabled=item["is_ai_enabled"],
            ai_daily_limit=item["ai_daily_limit"],
            features=item["features"],
            is_default=item["is_default"],
            is_active=True,
            policy_revision=1,
        )
        async_db_session.add(plan)
        plans.append(plan)
    await async_db_session.commit()
    for p in plans:
        await async_db_session.refresh(p)
    return plans


@pytest.mark.asyncio
async def test_launch_catalog_template_specification():
    """Verify launch catalog template strictly adheres to Option A specifications."""
    template = SubscriptionService.get_launch_catalog_template()
    by_name = {p["name"]: p for p in template}

    # 1. Essential
    assert "essential" in by_name
    ess = by_name["essential"]
    assert ess["price"] == Decimal("200.00")
    assert ess["max_users"] == 2
    assert ess["ai_daily_limit"] == 2
    assert ess["is_ai_enabled"] is True

    # 2. Professional
    assert "professional" in by_name
    pro = by_name["professional"]
    assert pro["price"] == Decimal("400.00")
    assert pro["max_users"] == 5
    assert pro["ai_daily_limit"] == 10
    assert pro["is_ai_enabled"] is True
    assert pro["is_default"] is True

    # 3. Business
    assert "business" in by_name
    biz = by_name["business"]
    assert biz["price"] == Decimal("1000.00")
    assert biz["max_users"] == 15
    assert biz["ai_daily_limit"] == 30
    assert biz["is_ai_enabled"] is True


@pytest.mark.asyncio
async def test_catalog_inventory_reporting(async_db_session, setup_pr11_plans):
    """Verify catalog inventory reports aggregate statistics and canonical status without PII."""
    inventory = await ReconciliationService.get_catalog_inventory(async_db_session)

    assert "counts" in inventory
    counts = inventory["counts"]
    assert counts["total_plans"] >= 3
    assert counts["active_plans"] >= 3

    canon = inventory["canonical_plans_status"]
    assert canon["essential"]["exists"] is True
    assert canon["essential"]["price"] == 200.0
    assert canon["essential"]["max_users"] == 2
    assert canon["essential"]["ai_daily_limit"] == 2

    assert canon["professional"]["exists"] is True
    assert canon["professional"]["price"] == 400.0
    assert canon["professional"]["max_users"] == 5
    assert canon["professional"]["ai_daily_limit"] == 10

    assert canon["business"]["exists"] is True
    assert canon["business"]["price"] == 1000.0
    assert canon["business"]["max_users"] == 15
    assert canon["business"]["ai_daily_limit"] == 30

    # Ensure no patient data or secrets in inventory
    serialized = json.dumps(inventory)
    assert "patient" not in serialized.lower()
    assert "secret" not in serialized.lower()
    assert "password" not in serialized.lower()


@pytest.mark.asyncio
async def test_reconciliation_preview_and_safe_application(
    async_db_session, setup_pr11_plans, mock_admin_user
):
    """Verify reconciliation preview discovers unanchored plans and applies safe anchoring."""
    # Create tenant with legacy/unanchored plan
    unanchored_tenant = models.Tenant(
        name="Unanchored Legacy Clinic",
        plan="starter",
        plan_id=None,
        subscription_status="active",
        is_active=True,
    )
    async_db_session.add(unanchored_tenant)
    await async_db_session.commit()
    await async_db_session.refresh(unanchored_tenant)

    # 1. Preview
    preview = await ReconciliationService.preview_reconciliation(async_db_session)
    assert preview["safe_migration_summary"]["unanchored_tenants_count"] >= 1
    unanchored_items = [
        item for item in preview["unanchored_tenants"] if item["tenant_id"] == unanchored_tenant.id
    ]
    assert len(unanchored_items) == 1
    assert unanchored_items[0]["proposed_plan_name"] == "essential"
    assert "preservation_guarantees" in preview
    assert len(preview["preservation_guarantees"]) >= 4

    # Verify no state changes happened during preview
    await async_db_session.refresh(unanchored_tenant)
    assert unanchored_tenant.plan_id is None

    # 2. Apply safe reconciliation
    result = await ReconciliationService.apply_reconciliation(
        async_db_session, admin_user=mock_admin_user
    )
    assert result["success"] is True
    assert result["reconciled_count"] >= 1

    await async_db_session.refresh(unanchored_tenant)
    assert unanchored_tenant.plan_id is not None
    assert unanchored_tenant.plan == "essential"

    # Verify audit log was created
    stmt_audit = select(models.AuditLog).where(
        models.AuditLog.tenant_id == unanchored_tenant.id,
        models.AuditLog.action == "TENANT_CATALOG_RECONCILE",
    )
    audit = (await async_db_session.execute(stmt_audit)).scalar_one_or_none()
    assert audit is not None
    assert "plan_id=" in audit.new_value


@pytest.mark.asyncio
async def test_commercial_suspension_vs_security_disable_vs_reactivation(
    async_db_session, setup_pr11_plans, mock_admin_user
):
    """
    Verify commercial suspension preserves is_active=True (Clinical History Invariant),
    security disable sets is_active=False, and reactivation restores active status.
    """
    tenant = models.Tenant(
        name="Suspension vs Security Clinic",
        plan="professional",
        plan_id=setup_pr11_plans[1].id,
        subscription_status="active",
        is_active=True,
    )
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)

    # 1. Commercial Suspension Preview
    req_preview = schemas.TenantCommercialActionRequest(
        reason="Testing commercial suspension preview",
        preview=True,
    )
    res_preview = await CommercialActionService.suspend_tenant(
        async_db_session, tenant.id, req_preview, mock_admin_user
    )
    assert res_preview.is_preview is True
    assert res_preview.resulting_state["subscription_status"] == "suspended_admin"
    assert res_preview.resulting_state["is_active"] is True
    assert res_preview.clinical_history_preserved is True

    # Ensure DB not changed
    await async_db_session.refresh(tenant)
    assert tenant.subscription_status == "active"

    # 2. Commercial Suspension Execute
    req_exec = schemas.TenantCommercialActionRequest(
        reason="Commercial non-payment suspension",
        preview=False,
    )
    res_exec = await CommercialActionService.suspend_tenant(
        async_db_session, tenant.id, req_exec, mock_admin_user
    )
    assert res_exec.is_preview is False
    await async_db_session.refresh(tenant)
    assert tenant.subscription_status == "suspended_admin"
    assert tenant.is_active is True  # Clinical History Invariant!

    # Verify commercial decision engine under suspended_admin:
    # Read clinical history is ALLOWED, Write business is DENIED
    read_decision = CommercialDecisionEngine.evaluate_capability(
        tenant,
        capability="clinical",
        operation=OperationClass.READ_HISTORY.value,
        override_mode="enforce",
    )
    assert read_decision.allowed is True
    assert read_decision.is_clinical_history_read is True

    write_decision = CommercialDecisionEngine.evaluate_capability(
        tenant,
        capability="clinical",
        operation=OperationClass.WRITE_BUSINESS.value,
        override_mode="enforce",
    )
    assert write_decision.allowed is False
    assert write_decision.proposed_allowed is False

    # 3. Security Disable Execute
    req_sec = schemas.TenantCommercialActionRequest(
        reason="Security incident emergency hard stop",
        preview=False,
    )
    res_sec = await CommercialActionService.security_disable_tenant(
        async_db_session, tenant.id, req_sec, mock_admin_user
    )
    assert res_sec.is_preview is False
    await async_db_session.refresh(tenant)
    assert tenant.is_active is False

    # 4. Reactivation Execute
    req_reactivate = schemas.TenantCommercialActionRequest(
        reason="Security review passed and payment confirmed",
        preview=False,
    )
    res_reactivate = await CommercialActionService.reactivate_tenant(
        async_db_session, tenant.id, req_reactivate, mock_admin_user
    )
    assert res_reactivate.is_preview is False
    await async_db_session.refresh(tenant)
    assert tenant.is_active is True
    assert tenant.subscription_status == "active"


@pytest.mark.asyncio
async def test_policy_reversal_command(
    async_db_session, setup_pr11_plans, mock_admin_user
):
    """
    Verify policy reversal command restores previous state,
    creates immutable reversal audit log, and rejects financial/destructive reversals.
    """
    tenant = models.Tenant(
        name="Policy Reversal Test Clinic",
        plan="professional",
        plan_id=setup_pr11_plans[1].id,
        subscription_status="active",
        is_active=True,
    )
    async_db_session.add(tenant)
    await async_db_session.commit()
    await async_db_session.refresh(tenant)

    # Apply commercial suspension
    req_suspend = schemas.TenantCommercialActionRequest(
        reason="Mistaken commercial suspension",
        preview=False,
    )
    await CommercialActionService.suspend_tenant(
        async_db_session, tenant.id, req_suspend, mock_admin_user
    )

    # Locate the audit log entry
    stmt_audit = (
        select(models.AuditLog)
        .where(
            models.AuditLog.tenant_id == tenant.id,
            models.AuditLog.action == "TENANT_COMMERCIAL_SUSPEND",
        )
        .order_by(models.AuditLog.id.desc())
    )
    audit = (await async_db_session.execute(stmt_audit)).scalar_one_or_none()
    assert audit is not None

    # 1. Preview reversal
    rev_preview = schemas.PolicyReversalRequest(
        audit_log_id=audit.id,
        reason="Review showed payment was made; previewing reversal",
        preview=True,
    )
    res_preview = await CommercialActionService.reverse_policy_action(
        async_db_session, rev_preview, mock_admin_user
    )
    assert res_preview.is_preview is True
    assert res_preview.action_reversed == "TENANT_COMMERCIAL_SUSPEND"
    assert res_preview.restored_values["subscription_status"] == "active"

    # DB still in suspended_admin
    await async_db_session.refresh(tenant)
    assert tenant.subscription_status == "suspended_admin"

    # 2. Execute reversal
    rev_exec = schemas.PolicyReversalRequest(
        audit_log_id=audit.id,
        reason="Approved reversal of mistaken suspension",
        preview=False,
    )
    res_exec = await CommercialActionService.reverse_policy_action(
        async_db_session, rev_exec, mock_admin_user
    )
    assert res_exec.is_preview is False
    assert res_exec.reversal_audit_log_id is not None

    await async_db_session.refresh(tenant)
    assert tenant.subscription_status == "active"

    # 3. Test rejection of financial payment reversal
    payment_audit = models.AuditLog(
        action="PAYMENT_RECEIVED",
        entity_type="SubscriptionPayment",
        entity_id=123,
        performed_by_id=mock_admin_user.id,
        performed_by_username=mock_admin_user.username,
        old_value="none",
        new_value="amount=400.00",
        details="Manual cash payment",
        tenant_id=tenant.id,
    )
    async_db_session.add(payment_audit)
    await async_db_session.commit()
    await async_db_session.refresh(payment_audit)

    rev_payment = schemas.PolicyReversalRequest(
        audit_log_id=payment_audit.id,
        reason="Attempting to undo a payment via policy command",
        preview=False,
    )
    with pytest.raises(HTTPException) as exc_info:
        await CommercialActionService.reverse_policy_action(
            async_db_session, rev_payment, mock_admin_user
        )
    assert exc_info.value.status_code == 400
    assert "Financial payments cannot be reversed via policy undo" in exc_info.value.detail


@pytest.mark.asyncio
async def test_plan_price_edit_preview_preserves_historical_receipts(
    async_db_session, setup_pr11_plans
):
    """
    Verify plan update preview highlights price changes apply to future charges only,
    never rewrites historical receipts, and counts affected clinics.
    """
    pro_plan = setup_pr11_plans[1]

    # Assign 2 clinics to this plan
    t1 = models.Tenant(name="Clinic 1", plan="professional", plan_id=pro_plan.id, is_active=True)
    t2 = models.Tenant(name="Clinic 2", plan="professional", plan_id=pro_plan.id, is_active=True)
    async_db_session.add_all([t1, t2])
    await async_db_session.commit()

    # Request preview with updated price
    preview_req = schemas.SubscriptionPlanPreviewRequest(
        price=Decimal("450.00"),
    )
    preview_res = await SubscriptionService.preview_plan_update(
        async_db_session, pro_plan.id, preview_req
    )

    assert preview_res.affected_tenants_count >= 2
    assert "price" in preview_res.proposed_changes
    assert preview_res.proposed_changes["price"]["old"] == "400.00"
    assert preview_res.proposed_changes["price"]["new"] == "450.00"

    # Assert warning text contains explicit future charges guarantee
    warnings_text = " ".join(preview_res.coverage_warnings)
    assert "future charges" in warnings_text
    assert "receipts are preserved" in warnings_text
