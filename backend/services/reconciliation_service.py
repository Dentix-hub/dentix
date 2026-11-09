"""
Reconciliation & Catalog Inventory Service (PR-11).
Authoritative, read-only aggregation of catalog plans, tenant plan anchors,
status/date mismatches, and safe reconciliation previews.
Guarantees:
- Aggregate / synthetic reporting only; NO patient content, passwords or secrets.
- Pure preview without side effects unless explicitly applied by Super Admin.
- Never shortens active paid periods, never deletes clinical accounts or history.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.services.policy_snapshot import tenant_policy_marker
from backend.services.commercial_decision import CAPABILITY_REGISTRY
from backend.services.subscription_state_machine import SubscriptionState

logger = logging.getLogger(__name__)


class ReconciliationService:
    @staticmethod
    def _utc_now_naive() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @classmethod
    async def get_catalog_inventory(cls, db: AsyncSession) -> Dict[str, Any]:
        """
        Inspect all subscription plans and tenants to produce an authoritative catalog inventory.
        Zero PII or secrets.
        """
        now = cls._utc_now_naive()

        # 1. Plans inspection
        stmt_plans = select(models.SubscriptionPlan).order_by(
            models.SubscriptionPlan.id.asc()
        )
        plans = (await db.execute(stmt_plans)).scalars().all()

        total_plans = len(plans)
        active_plans = [p for p in plans if p.is_active]
        retired_plans = [p for p in plans if not p.is_active]

        active_plan_ids = {p.id for p in plans}
        active_plan_names = {p.name.lower(): p for p in active_plans}

        # Check canonical launch tiers
        canonical_names = {"essential", "professional", "business"}
        canonical_status = {}
        for cname in canonical_names:
            p = active_plan_names.get(cname)
            if p:
                canonical_status[cname] = {
                    "exists": True,
                    "plan_id": p.id,
                    "price": float(p.price) if p.price is not None else 0.0,
                    "max_users": p.max_users,
                    "ai_daily_limit": p.ai_daily_limit,
                    "is_active": p.is_active,
                    "is_default": p.is_default,
                }
            else:
                canonical_status[cname] = {"exists": False}

        # 2. Tenants inspection
        stmt_tenants = select(models.Tenant).order_by(models.Tenant.id.asc())
        tenants = (await db.execute(stmt_tenants)).scalars().all()

        total_tenants = len(tenants)
        orphan_plan_tenants = 0
        null_or_zero_limits = 0
        status_date_mismatches = 0
        warnings: List[str] = []

        for t in tenants:
            # Check orphan reference
            if t.plan_id is None or t.plan_id not in active_plan_ids:
                orphan_plan_tenants += 1

            # Check status / date mismatch
            status = (t.subscription_status or "trial").lower().strip()
            end_date = t.subscription_end_date
            if status == SubscriptionState.ACTIVE.value and end_date and end_date < now:
                status_date_mismatches += 1
            elif (
                status == SubscriptionState.EXPIRED_READ_ONLY.value
                and end_date
                and end_date > now
            ):
                status_date_mismatches += 1

        # Check null or zero limits in active plans
        for p in active_plans:
            if p.max_users is None or p.max_users <= 0:
                null_or_zero_limits += 1
                warnings.append(
                    f"Plan '{p.name}' (id={p.id}) has unconstrained or zero max_users."
                )
            if p.is_ai_enabled and (p.ai_daily_limit is None or p.ai_daily_limit <= 0):
                null_or_zero_limits += 1
                warnings.append(
                    f"Plan '{p.name}' (id={p.id}) has AI enabled but zero/null ai_daily_limit."
                )

        # 3. Overrides count
        stmt_ov = select(func.count(models.CommercialTenantOverride.id))
        total_overrides = (await db.execute(stmt_ov)).scalar() or 0

        from backend.core.config import get_subscription_enforcement_mode
        enforcement_mode = get_subscription_enforcement_mode()

        catalog_plans_summary = [
            {
                "id": p.id,
                "name": p.name,
                "display_name_ar": p.display_name_ar,
                "price": float(p.price) if p.price is not None else 0.0,
                "max_users": p.max_users,
                "ai_daily_limit": p.ai_daily_limit,
                "is_active": p.is_active,
                "is_default": p.is_default,
                "policy_revision": p.policy_revision or 1,
            }
            for p in plans
        ]

        return {
            "counts": {
                "total_plans": total_plans,
                "active_plans": len(active_plans),
                "retired_plans": len(retired_plans),
                "total_tenants": total_tenants,
                "orphan_plan_tenants": orphan_plan_tenants,
                "null_or_zero_limits": null_or_zero_limits,
                "status_date_mismatches": status_date_mismatches,
                "tenants_with_overrides": total_overrides,
            },
            "canonical_plans_status": canonical_status,
            "enforcement_mode": enforcement_mode,
            "catalog_plans": catalog_plans_summary,
            "warnings": warnings,
        }

    @classmethod
    async def preview_reconciliation(cls, db: AsyncSession) -> Dict[str, Any]:
        """
        Pure preview of catalog and tenant reconciliation.
        Identifies unanchored plans, status anomalies, and proposes mappings.
        Zero state mutations.
        """
        now = cls._utc_now_naive()

        # Query active plans for new catalog proposals
        stmt_plans = select(models.SubscriptionPlan).where(
            models.SubscriptionPlan.is_active.is_(True)
        )
        active_plans = (await db.execute(stmt_plans)).scalars().all()
        plan_by_name = {p.name.lower(): p for p in active_plans}

        # Query all existing plans (including retired contracts) to preserve valid historical/retired anchors
        stmt_all_plans = select(models.SubscriptionPlan)
        all_plans = (await db.execute(stmt_all_plans)).scalars().all()
        all_plan_ids = {p.id for p in all_plans}

        stmt_tenants = select(models.Tenant).order_by(models.Tenant.id.asc())
        tenants = (await db.execute(stmt_tenants)).scalars().all()

        unanchored_tenants: List[Dict[str, Any]] = []
        status_anomalies: List[Dict[str, Any]] = []

        proposed_mappings = {
            "free": "essential",
            "starter": "essential",
            "basic": "essential",
            "مجاني": "essential",
            "pro": "professional",
            "standard": "professional",
            "enterprise": "business",
            "vip": "business",
            "unlimited": "business",
        }

        for t in tenants:
            raw_plan = (t.plan or "").lower().strip()
            # 1. Unanchored or orphan check:
            # Preserves valid current paid anchors, including retired catalog records
            if t.plan_id is not None and t.plan_id in all_plan_ids:
                # Tenant is already anchored to a valid catalog plan contract (active or retired)
                pass
            else:
                # Genuinely unanchored or orphan
                mapped_name = proposed_mappings.get(raw_plan)
                matched_plan = (
                    plan_by_name.get(mapped_name)
                    if mapped_name
                    else plan_by_name.get(raw_plan)
                )
                target_plan = matched_plan

                unanchored_tenants.append(
                    {
                        "tenant_id": t.id,
                        "tenant_name": t.name,
                        "current_raw_plan": t.plan,
                        "current_plan_id": t.plan_id,
                        "policy_revision": t.policy_revision or 1,
                        "proposed_plan_id": target_plan.id if target_plan else None,
                        "proposed_plan_name": target_plan.name
                        if target_plan
                        else "essential",
                        "reason": "Missing or orphan plan_id anchor in catalog",
                    }
                )

            # 2. Status anomaly check
            status = (t.subscription_status or "trial").lower().strip()
            end_date = t.subscription_end_date
            if status == SubscriptionState.ACTIVE.value and end_date and end_date < now:
                status_anomalies.append(
                    {
                        "tenant_id": t.id,
                        "tenant_name": t.name,
                        "current_status": status,
                        "subscription_end_date": str(end_date),
                        "proposed_status": SubscriptionState.EXPIRED_READ_ONLY.value,
                        "reason": "Active subscription has passed end_date without renewal",
                    }
                )
            elif (
                status == SubscriptionState.EXPIRED_READ_ONLY.value
                and end_date
                and end_date > now
            ):
                status_anomalies.append(
                    {
                        "tenant_id": t.id,
                        "tenant_name": t.name,
                        "current_status": status,
                        "subscription_end_date": str(end_date),
                        "proposed_status": SubscriptionState.ACTIVE.value,
                        "reason": "Expired status is inconsistent with future subscription_end_date",
                    }
                )

        return {
            "safe_migration_summary": {
                "unanchored_tenants_count": len(unanchored_tenants),
                "status_anomalies_count": len(status_anomalies),
                "total_tenants_inspected": len(tenants),
            },
            "unanchored_tenants": unanchored_tenants,
            "status_anomalies": status_anomalies,
            "proposed_canonical_mappings": proposed_mappings,
            "preservation_guarantees": [
                "No paid subscription period will be shortened or rewritten.",
                "Active clinical user accounts will never be automatically deleted or downgraded.",
                "Clinical history remains accessible (read-only) for authorized readers across all transitions.",
                "Staging and production seeds will never overwrite active tenant contracts without explicit Super Admin review.",
            ],
        }

    @classmethod
    async def apply_reconciliation(cls, db, admin_user=None, selection=None):
        if selection is None:
            raise HTTPException(
                status_code=409,
                detail="Explicit reviewed mappings, revision and reason required",
            )
        if admin_user is None:
            raise HTTPException(status_code=403, detail="Audited platform actor required")
        ids = [item.tenant_id for item in selection.mappings]
        if len(set(ids)) != len(ids):
            raise HTTPException(status_code=422, detail="Duplicate tenant selection")
        try:
            # Validate the complete batch under locks before performing any writes.
            changes = []
            for item in sorted(selection.mappings, key=lambda x: x.tenant_id):
                tenant = (
                    await db.execute(
                        select(models.Tenant)
                        .where(models.Tenant.id == item.tenant_id)
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    )
                ).scalar_one_or_none()
                if (
                    tenant is None
                    or tenant.plan_id != item.expected_plan_id
                    or (tenant.policy_revision or 1) != item.expected_revision
                ):
                    raise HTTPException(
                        status_code=409, detail="Stale tenant reconciliation selection"
                    )
                if tenant.future_plan_id or tenant.scheduled_downgrade_plan_id:
                    raise HTTPException(
                        status_code=409,
                        detail="Scheduled contract requires canonical subscription workflow",
                    )
                if tenant.plan_id is not None and await db.get(
                    models.SubscriptionPlan, tenant.plan_id
                ):
                    raise HTTPException(
                        status_code=409,
                        detail="Existing contract must use canonical plan-change workflow",
                    )
                platform_user = (
                    await db.execute(
                        select(models.User.id)
                        .where(
                            models.User.tenant_id == tenant.id,
                            models.User.role == "super_admin",
                        )
                        .limit(1)
                    )
                ).first()
                if platform_user:
                    raise HTTPException(
                        status_code=409, detail="Platform tenant cannot be reconciled"
                    )
                plan = await db.get(models.SubscriptionPlan, item.plan_id)
                if plan is None or not plan.is_active:
                    raise HTTPException(
                        status_code=409, detail="Selected plan is unavailable"
                    )
                from backend.services.account_admission_service import (
                    AccountAdmissionService,
                )

                count = await AccountAdmissionService.get_active_account_count(
                    db, tenant.id
                )
                if plan.max_users is not None and count > plan.max_users:
                    raise HTTPException(
                        status_code=409, detail="Active accounts exceed selected plan"
                    )
                changes.append((tenant, plan))
            for tenant, plan in changes:
                before = {"plan": tenant.plan, "plan_id": tenant.plan_id}
                tenant.plan, tenant.plan_id = plan.name, plan.id
                tenant.policy_revision = (tenant.policy_revision or 1) + 1
                if admin_user:
                    db.add(
                        models.AuditLog(
                            action="TENANT_CATALOG_RECONCILE",
                            entity_type="Tenant",
                            entity_id=tenant.id,
                            tenant_id=tenant.id,
                            performed_by_id=admin_user.id,
                            performed_by_username=admin_user.username,
                            old_value=json.dumps(before),
                            new_value=json.dumps(
                                {
                                    "plan": plan.name,
                                    "plan_id": plan.id,
                                    **tenant_policy_marker(tenant),
                                }
                            ),
                            details=selection.reason,
                        )
                    )
            await db.commit()
            return {"success": True, "reconciled_count": len(changes)}
        except Exception:
            await db.rollback()
            raise
