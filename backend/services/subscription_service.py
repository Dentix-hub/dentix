from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import logging
import os
from uuid import uuid4
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from backend import models, schemas
from fastapi import HTTPException
from backend.core.commercial_registry import (
    CAPABILITY_REGISTRY,
    canonicalize_capability_key,
    is_sellable_capability,
)
from backend.services.webhook_service import WebhookService

logger = logging.getLogger("smart_clinic.subscription")


class SubscriptionService:
    DEFAULT_GRACE_PERIOD_DAYS = 7
    CHECKOUT_TTL_MINUTES = 15
    WEBHOOK_MAX_AGE_SECONDS = 300

    @staticmethod
    def _utc_now_naive() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _money(value: float | Decimal) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"))

    @staticmethod
    def _verify_provider_signature(
        raw_payload: bytes, timestamp: str, signature: str
    ) -> None:
        secret = os.getenv("SUBSCRIPTION_WEBHOOK_SECRET", "")
        if len(secret) < 32:
            raise HTTPException(
                status_code=503,
                detail="Subscription webhook verification is not configured",
            )

        verifier = WebhookService(secret)
        if not verifier.verify_raw_signature(
            raw_payload,
            timestamp,
            signature,
            max_age_seconds=SubscriptionService.WEBHOOK_MAX_AGE_SECONDS,
        ):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    @staticmethod
    async def check_subscription_status(db: AsyncSession, tenant_id: int):
        """
        Evaluates the current status of a tenant subscription.
        Returns: 'active', 'grace_period', 'expired', 'suspended'
        """
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            return None

        # 1. Check Forced Suspension
        # If manually set to inactive? The model has is_active.
        if not tenant.is_active:
            return "suspended"

        # 2. Check Expiry
        if not tenant.subscription_end_date:
            return "active"  # Assuming permanent/trial if no date? Or indefinite.

        now = datetime.now(timezone.utc)

        sub_end = tenant.subscription_end_date
        if sub_end and sub_end.tzinfo is None:
            sub_end = sub_end.replace(tzinfo=timezone.utc)
        if now <= sub_end:
            return "active"

        # 3. Check Grace Period
        grace_end = tenant.grace_period_until
        if grace_end and grace_end.tzinfo is None:
            grace_end = grace_end.replace(tzinfo=timezone.utc)

        if grace_end and now <= grace_end:
            return "grace_period"

        return "expired"

    @staticmethod
    async def extend_grace_period(db: AsyncSession, tenant_id: int, days: int, reason: str):
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.grace_period_until = datetime.now(timezone.utc) + timedelta(days=days)
        tenant.manual_override_reason = reason
        tenant.is_active = True

        await db.commit()
        return tenant

    @staticmethod
    async def manual_suspend(db: AsyncSession, tenant_id: int, reason: str):
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.is_active = False
        tenant.manual_override_reason = f"Suspended: {reason}"
        await db.commit()
        return tenant

    @staticmethod
    async def get_subscription_details(db: AsyncSession, tenant_id: int):
        """Get full subscription details for UI/AI."""
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            return None

        plan = None
        if tenant.plan_id:
            stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.id == tenant.plan_id)
            plan = (await db.execute(stmt)).scalar_one_or_none()

        plan_name = plan.display_name_ar if plan else (tenant.plan or "مجاني")
        plan_price = plan.price if plan else 0

        return {
            "plan_name": plan_name,
            "plan_price": plan_price,
            "status": tenant.subscription_status or "active",
            "start_date": None,
            "end_date": str(tenant.subscription_end_date)
            if tenant.subscription_end_date
            else None,
            "is_active": tenant.subscription_status == "active",
        }

    @staticmethod
    async def get_all_plans(db: AsyncSession):
        """List all active subscription plans."""
        stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.is_active == True)  # noqa: E712
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def create_plan(
        db: AsyncSession,
        plan_data: schemas.SubscriptionPlanCreate,
        admin_user: Optional[models.User] = None,
    ):
        """Create a new subscription plan with validation and transactional audit."""
        stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.name == plan_data.name)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400, detail="Plan with this name already exists"
            )

        if getattr(plan_data, "is_default", False):
            stmt = update(models.SubscriptionPlan).values(is_default=False)
            await db.execute(stmt)

        new_plan = models.SubscriptionPlan(
            name=plan_data.name,
            display_name_ar=plan_data.display_name_ar,
            price=plan_data.price,
            duration_days=plan_data.duration_days,
            max_users=plan_data.max_users,
            max_patients=plan_data.max_patients,
            features=plan_data.features,
            is_ai_enabled=plan_data.is_ai_enabled,
            ai_daily_limit=plan_data.ai_daily_limit,
            ai_features=plan_data.ai_features,
            is_default=getattr(plan_data, "is_default", False),
            is_active=True,
            policy_revision=1,
            billing_cycle_unit=getattr(plan_data, "billing_cycle_unit", "month"),
        )
        db.add(new_plan)
        await db.flush()

        if admin_user:
            audit = models.AuditLog(
                action="SUBSCRIPTION_PLAN_CREATE",
                entity_type="SubscriptionPlan",
                entity_id=new_plan.id,
                performed_by_id=admin_user.id,
                performed_by_username=admin_user.username,
                new_value=json.dumps({
                    "name": new_plan.name,
                    "display_name_ar": new_plan.display_name_ar,
                    "price": str(new_plan.price),
                    "max_users": new_plan.max_users,
                    "is_ai_enabled": new_plan.is_ai_enabled,
                    "ai_daily_limit": new_plan.ai_daily_limit,
                    "features": new_plan.features,
                }, ensure_ascii=False),
                details=f"Created subscription plan '{new_plan.name}'",
            )
            db.add(audit)

        await db.commit()
        await db.refresh(new_plan)
        return new_plan

    @staticmethod
    async def update_plan(
        db: AsyncSession,
        plan_id: int,
        update_data: schemas.SubscriptionPlanUpdate,
        admin_user: Optional[models.User] = None,
    ):
        """Update an existing plan with optimistic locking and transactional audit."""
        stmt = (
            select(models.SubscriptionPlan)
            .where(models.SubscriptionPlan.id == plan_id)
            .with_for_update()
        )
        plan = (await db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Optimistic concurrency check
        if update_data.expected_revision is not None:
            if plan.policy_revision != update_data.expected_revision:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Policy revision conflict: expected revision {update_data.expected_revision}, "
                        f"but current revision is {plan.policy_revision}. Please refresh and re-submit."
                    ),
                )

        update_dict = update_data.model_dump(exclude_unset=True)
        update_dict.pop("expected_revision", None)
        reason = update_dict.pop("reason", None) or "Subscription plan updated by Super Admin"

        # AI Limit consistency check with resulting state
        effective_ai_enabled = (
            update_dict["is_ai_enabled"]
            if "is_ai_enabled" in update_dict
            else plan.is_ai_enabled
        )
        effective_ai_limit = (
            update_dict["ai_daily_limit"]
            if "ai_daily_limit" in update_dict
            else plan.ai_daily_limit
        )
        if effective_ai_enabled and (effective_ai_limit is None or effective_ai_limit <= 0):
            raise HTTPException(
                status_code=422,
                detail="ai_daily_limit must be greater than 0 when is_ai_enabled is True",
            )
        if not effective_ai_enabled and (effective_ai_limit is not None and effective_ai_limit > 0):
            raise HTTPException(
                status_code=422,
                detail="ai_daily_limit must be 0 when is_ai_enabled is False",
            )

        if update_dict.get("is_default") is True:
            stmt = (
                update(models.SubscriptionPlan)
                .where(models.SubscriptionPlan.id != plan_id)
                .values(is_default=False)
            )
            await db.execute(stmt)

        old_values: Dict[str, Any] = {}
        new_values: Dict[str, Any] = {}
        for key, value in update_dict.items():
            old_val = getattr(plan, key, None)
            if old_val != value:
                old_values[key] = str(old_val) if isinstance(old_val, Decimal) else old_val
                new_values[key] = str(value) if isinstance(value, Decimal) else value
                setattr(plan, key, value)

        plan.policy_revision = (plan.policy_revision or 1) + 1

        if admin_user and (old_values or new_values):
            audit = models.AuditLog(
                action="SUBSCRIPTION_PLAN_UPDATE",
                entity_type="SubscriptionPlan",
                entity_id=plan.id,
                performed_by_id=admin_user.id,
                performed_by_username=admin_user.username,
                old_value=json.dumps(old_values, ensure_ascii=False),
                new_value=json.dumps(new_values, ensure_ascii=False),
                details=reason,
            )
            db.add(audit)

        await db.commit()
        await db.refresh(plan)
        return plan

    @staticmethod
    async def preview_plan_update(
        db: AsyncSession,
        plan_id: int,
        preview_data: schemas.SubscriptionPlanPreviewRequest,
    ) -> schemas.SubscriptionPlanPreviewResponse:
        """Pure preview of plan updates without persisting mutations."""
        stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.id == plan_id)
        plan = (await db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        stmt_count = select(func.count(models.Tenant.id)).where(models.Tenant.plan_id == plan_id)
        affected_count = (await db.execute(stmt_count)).scalar() or 0

        update_dict = preview_data.model_dump(exclude_unset=True)
        proposed_changes: Dict[str, Dict[str, Any]] = {}
        coverage_warnings: List[str] = []

        for key, new_val in update_dict.items():
            old_val = getattr(plan, key, None)
            if old_val != new_val:
                proposed_changes[key] = {
                    "old": str(old_val) if isinstance(old_val, Decimal) else old_val,
                    "new": str(new_val) if isinstance(new_val, Decimal) else new_val,
                }

        if "price" in proposed_changes:
            coverage_warnings.append(
                f"Plan price will change from {proposed_changes['price']['old']} to {proposed_changes['price']['new']} EGP for future charges. Past historical receipts are preserved."
            )
        if "max_users" in proposed_changes:
            coverage_warnings.append(
                f"Seat limit will change from {proposed_changes['max_users']['old']} to {proposed_changes['max_users']['new']}."
            )
        if "features" in proposed_changes:
            coverage_warnings.append(
                "Capabilities modified. Changes take effect on next request admission."
            )

        return schemas.SubscriptionPlanPreviewResponse(
            plan_id=plan.id,
            plan_name=plan.name,
            current_revision=plan.policy_revision or 1,
            affected_tenants_count=affected_count,
            proposed_changes=proposed_changes,
            coverage_warnings=coverage_warnings,
            can_apply=True,
        )

    @staticmethod
    async def delete_plan(
        db: AsyncSession,
        plan_id: int,
        reason: Optional[str] = None,
        admin_user: Optional[models.User] = None,
    ):
        """Soft delete a plan (set is_active=False) with audit. Does not revoke existing tenant contracts."""
        stmt = (
            select(models.SubscriptionPlan)
            .where(models.SubscriptionPlan.id == plan_id)
            .with_for_update()
        )
        plan = (await db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        plan.is_active = False
        plan.policy_revision = (plan.policy_revision or 1) + 1

        if admin_user:
            audit = models.AuditLog(
                action="SUBSCRIPTION_PLAN_DEACTIVATE",
                entity_type="SubscriptionPlan",
                entity_id=plan.id,
                performed_by_id=admin_user.id,
                performed_by_username=admin_user.username,
                details=reason or f"Deactivated subscription plan '{plan.name}' (catalog retirement)",
            )
            db.add(audit)

        await db.commit()
        return {"success": True, "message": "Plan deactivated successfully"}

    @staticmethod
    async def reconcile_duplicate_plans(db: AsyncSession) -> Dict[str, Any]:
        """
        Inspect all subscription plans, group by canonical name, and reconcile duplicates atomically.
        Preserves historical payments and foreign keys. Sets redundant duplicates to is_active=False.
        """
        stmt = select(models.SubscriptionPlan).order_by(models.SubscriptionPlan.id.asc())
        all_plans = (await db.execute(stmt)).scalars().all()
        by_name: Dict[str, List[models.SubscriptionPlan]] = {}
        for p in all_plans:
            by_name.setdefault(p.name.strip().lower(), []).append(p)

        reconciled = []
        for name, plans_list in by_name.items():
            if len(plans_list) > 1:
                # Find one with active tenants or highest id
                best_plan = max(plans_list, key=lambda p: (len(getattr(p, "tenants", [])), p.id))
                for dup in plans_list:
                    if dup.id != best_plan.id and dup.is_active:
                        dup.is_active = False
                        reconciled.append({
                            "deactivated_id": dup.id,
                            "deactivated_name": dup.name,
                            "kept_active_id": best_plan.id,
                        })
        if reconciled:
            await db.commit()
        return {
            "scanned_plans_count": len(all_plans),
            "duplicates_detected": len(reconciled),
            "reconciled": reconciled,
        }

    # --- Commercial Tenant Overrides ---
    @staticmethod
    async def get_tenant_commercial_overrides(
        db: AsyncSession,
        tenant_id: int,
    ) -> schemas.TenantCommercialOverridesResponse:
        """Fetch all commercial capability overrides for a specific tenant."""
        stmt_t = select(models.Tenant).where(models.Tenant.id == tenant_id)
        tenant = (await db.execute(stmt_t)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        stmt_ov = (
            select(models.CommercialTenantOverride)
            .options(selectinload(models.CommercialTenantOverride.created_by))
            .where(models.CommercialTenantOverride.tenant_id == tenant_id)
            .order_by(models.CommercialTenantOverride.capability_key.asc())
        )
        rows = (await db.execute(stmt_ov)).scalars().all()

        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        overrides_list = []
        effective_map: Dict[str, bool] = {}

        for r in rows:
            is_expired = bool(r.expires_at and r.expires_at < current_time)
            overrides_list.append(
                schemas.CommercialTenantOverrideResponse(
                    id=r.id,
                    tenant_id=r.tenant_id,
                    capability_key=r.capability_key,
                    override_value=r.override_value,
                    reason=r.reason,
                    expires_at=r.expires_at,
                    is_expired=is_expired,
                    created_by_id=r.created_by_id,
                    created_by_username=r.created_by.username if r.created_by else None,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )
            if not is_expired:
                if r.override_value == "allow":
                    effective_map[r.capability_key] = True
                elif r.override_value == "deny":
                    effective_map[r.capability_key] = False

        return schemas.TenantCommercialOverridesResponse(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            policy_revision=tenant.policy_revision or 1,
            overrides=overrides_list,
            effective_capabilities=effective_map,
        )

    @staticmethod
    async def update_tenant_commercial_overrides(
        db: AsyncSession,
        tenant_id: int,
        update_data: schemas.TenantCommercialOverridesUpdateRequest,
        admin_user: Optional[models.User] = None,
    ) -> schemas.TenantCommercialOverridesResponse:
        """Mutate tenant commercial overrides with optimistic locking and transactional audit."""
        stmt_t = select(models.Tenant).where(models.Tenant.id == tenant_id).with_for_update()
        tenant = (await db.execute(stmt_t)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        current_rev = tenant.policy_revision or 1
        if current_rev != update_data.expected_revision:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Policy revision conflict: expected {update_data.expected_revision}, "
                    f"but current revision is {current_rev}. Please refresh and re-submit."
                ),
            )

        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

        stmt_existing = select(models.CommercialTenantOverride).where(
            models.CommercialTenantOverride.tenant_id == tenant_id
        )
        existing_rows = list((await db.execute(stmt_existing)).scalars().all())

        old_overrides_dict = {
            r.capability_key: {
                "override_value": r.override_value,
                "reason": r.reason,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in existing_rows
        }
        new_overrides_dict: Dict[str, Any] = {}

        for item in update_data.overrides:
            canon_cap = canonicalize_capability_key(item.capability_key)
            if not canon_cap or canon_cap not in CAPABILITY_REGISTRY:
                raise HTTPException(
                    status_code=422, detail=f"Unknown capability key '{item.capability_key}'"
                )

            # Non-sellable check: cannot override to allow!
            if item.override_value == "allow" and not is_sellable_capability(canon_cap):
                raise HTTPException(
                    status_code=422,
                    detail=f"Capability '{canon_cap}' is not sellable in current release and cannot be overridden to 'allow'.",
                )

            existing_row = next((r for r in existing_rows if r.capability_key == canon_cap), None)

            if item.override_value == "inherit":
                if existing_row:
                    await db.delete(existing_row)
                    existing_rows.remove(existing_row)
                new_overrides_dict[canon_cap] = {"override_value": "inherit"}
            else:
                expires_at_naive = (
                    item.expires_at.replace(tzinfo=None) if item.expires_at else None
                )
                if existing_row:
                    existing_row.override_value = item.override_value
                    existing_row.reason = update_data.reason
                    existing_row.expires_at = expires_at_naive
                    if admin_user:
                        existing_row.created_by_id = admin_user.id
                    existing_row.updated_at = now_naive
                else:
                    new_row = models.CommercialTenantOverride(
                        tenant_id=tenant_id,
                        capability_key=canon_cap,
                        override_value=item.override_value,
                        reason=update_data.reason,
                        expires_at=expires_at_naive,
                        created_by_id=admin_user.id if admin_user else None,
                        created_at=now_naive,
                        updated_at=now_naive,
                    )
                    db.add(new_row)
                    existing_rows.append(new_row)

                new_overrides_dict[canon_cap] = {
                    "override_value": item.override_value,
                    "expires_at": expires_at_naive.isoformat() if expires_at_naive else None,
                }

        tenant.policy_revision = current_rev + 1

        if admin_user:
            audit = models.AuditLog(
                action="TENANT_COMMERCIAL_OVERRIDES_UPDATE",
                entity_type="Tenant",
                entity_id=tenant.id,
                tenant_id=tenant.id,
                performed_by_id=admin_user.id,
                performed_by_username=admin_user.username,
                old_value=json.dumps(old_overrides_dict, ensure_ascii=False),
                new_value=json.dumps(new_overrides_dict, ensure_ascii=False),
                details=update_data.reason,
            )
            db.add(audit)

        await db.commit()
        return await SubscriptionService.get_tenant_commercial_overrides(db, tenant_id)

    # --- Trial Policy ---
    @staticmethod
    async def get_trial_policy(db: AsyncSession) -> schemas.TrialPolicyResponse:
        """Get current signup trial policy settings."""
        res_name = await db.execute(
            select(models.SystemSetting).where(models.SystemSetting.key == "system_trial_plan_name")
        )
        row_name = res_name.scalar_one_or_none()
        trial_plan_name = row_name.value if row_name else "professional"

        res_days = await db.execute(
            select(models.SystemSetting).where(models.SystemSetting.key == "system_trial_duration_days")
        )
        row_days = res_days.scalar_one_or_none()
        trial_days = int(row_days.value) if (row_days and row_days.value.isdigit()) else 14

        res_plans = await db.execute(
            select(models.SubscriptionPlan).where(models.SubscriptionPlan.is_active == True)  # noqa: E712
        )
        active_plans = res_plans.scalars().all()
        eligible_list = [
            {"id": p.id, "name": p.name, "display_name_ar": p.display_name_ar}
            for p in active_plans
        ]

        target_plan = next((p for p in active_plans if p.name == trial_plan_name), None)

        return schemas.TrialPolicyResponse(
            trial_plan_name=trial_plan_name,
            trial_plan_id=target_plan.id if target_plan else None,
            trial_duration_days=trial_days,
            is_card_required=False,
            eligible_plans=eligible_list,
        )

    @staticmethod
    async def update_trial_policy(
        db: AsyncSession,
        update_data: schemas.TrialPolicyUpdateRequest,
        admin_user: Optional[models.User] = None,
    ) -> schemas.TrialPolicyResponse:
        """Update future signup trial policy with transactional audit."""
        res_p = await db.execute(
            select(models.SubscriptionPlan).where(
                models.SubscriptionPlan.name == update_data.trial_plan_name,
                models.SubscriptionPlan.is_active == True,  # noqa: E712
            )
        )
        plan = res_p.scalar_one_or_none()
        if not plan:
            raise HTTPException(
                status_code=400,
                detail=f"Active plan '{update_data.trial_plan_name}' not found",
            )

        res_s1 = await db.execute(
            select(models.SystemSetting).where(models.SystemSetting.key == "system_trial_plan_name")
        )
        s1 = res_s1.scalar_one_or_none()
        old_plan_name = s1.value if s1 else "professional"
        if s1:
            s1.value = update_data.trial_plan_name
        else:
            db.add(models.SystemSetting(key="system_trial_plan_name", value=update_data.trial_plan_name))

        res_s2 = await db.execute(
            select(models.SystemSetting).where(models.SystemSetting.key == "system_trial_duration_days")
        )
        s2 = res_s2.scalar_one_or_none()
        old_days = s2.value if s2 else "14"
        if s2:
            s2.value = str(update_data.trial_duration_days)
        else:
            db.add(models.SystemSetting(key="system_trial_duration_days", value=str(update_data.trial_duration_days)))

        if admin_user:
            audit = models.AuditLog(
                action="TRIAL_POLICY_UPDATE",
                entity_type="SystemSetting",
                performed_by_id=admin_user.id,
                performed_by_username=admin_user.username,
                old_value=json.dumps({"trial_plan_name": old_plan_name, "trial_duration_days": old_days}),
                new_value=json.dumps({
                    "trial_plan_name": update_data.trial_plan_name,
                    "trial_duration_days": update_data.trial_duration_days,
                }),
                details=update_data.reason,
            )
            db.add(audit)

        await db.commit()
        return await SubscriptionService.get_trial_policy(db)

    @staticmethod
    def get_launch_catalog_template() -> List[Dict[str, Any]]:
        """Return the owner-approved launch tiers template (200/400/1000 EGP, 2/5/15 seats, 2/10/30 AI)."""
        sellable_caps = [
            k for k, defn in CAPABILITY_REGISTRY.items() if defn.is_sellable
        ]
        features_json = json.dumps(sellable_caps)
        return [
            {
                "name": "essential",
                "display_name_ar": "الأساسية",
                "price": Decimal("200.00"),
                "duration_days": 30,
                "billing_cycle_unit": "month",
                "max_users": 2,
                "max_patients": None,
                "is_ai_enabled": True,
                "ai_daily_limit": 2,
                "features": features_json,
                "is_default": False,
            },
            {
                "name": "professional",
                "display_name_ar": "الاحترافية",
                "price": Decimal("400.00"),
                "duration_days": 30,
                "billing_cycle_unit": "month",
                "max_users": 5,
                "max_patients": None,
                "is_ai_enabled": True,
                "ai_daily_limit": 10,
                "features": features_json,
                "is_default": True,
            },
            {
                "name": "business",
                "display_name_ar": "المتقدمة",
                "price": Decimal("1000.00"),
                "duration_days": 30,
                "billing_cycle_unit": "month",
                "max_users": 15,
                "max_patients": None,
                "is_ai_enabled": True,
                "ai_daily_limit": 30,
                "features": features_json,
                "is_default": False,
            },
        ]

    @staticmethod
    async def seed_launch_catalog(
        db: AsyncSession,
        admin_user: Optional[models.User] = None,
    ) -> Dict[str, Any]:
        """Produce the approved launch catalog without overwriting existing tenant contracts."""
        templates = SubscriptionService.get_launch_catalog_template()
        created = []
        existing = []

        for spec in templates:
            stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.name == spec["name"])
            found = (await db.execute(stmt)).scalar_one_or_none()
            if not found:
                p = models.SubscriptionPlan(
                    name=spec["name"],
                    display_name_ar=spec["display_name_ar"],
                    price=spec["price"],
                    duration_days=spec["duration_days"],
                    billing_cycle_unit=spec["billing_cycle_unit"],
                    max_users=spec["max_users"],
                    max_patients=spec["max_patients"],
                    is_ai_enabled=spec["is_ai_enabled"],
                    ai_daily_limit=spec["ai_daily_limit"],
                    features=spec["features"],
                    is_default=spec["is_default"],
                    is_active=True,
                    policy_revision=1,
                )
                db.add(p)
                created.append(spec["name"])
            else:
                existing.append(spec["name"])

        if created:
            if admin_user:
                db.add(
                    models.AuditLog(
                        action="SUBSCRIPTION_CATALOG_SEED",
                        entity_type="SubscriptionPlan",
                        performed_by_id=admin_user.id,
                        performed_by_username=admin_user.username,
                        new_value=json.dumps({"created_plans": created}),
                        details="Seeded initial approved launch plans",
                    )
                )
            await db.commit()

        return {
            "created_plans": created,
            "existing_plans": existing,
            "message": f"Seeded {len(created)} plans; {len(existing)} already present.",
        }

    # --- Payment Methods ---
    @staticmethod
    async def get_payments(db: AsyncSession, skip: int = 0, limit: int = 100):
        stmt = (
            select(models.SubscriptionPayment)
            .options(selectinload(models.SubscriptionPayment.tenant))
            .order_by(models.SubscriptionPayment.payment_date.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def record_payment(
        db: AsyncSession,
        payment_data: schemas.SubscriptionPaymentCreate,
        created_by: str,
        *,
        commit: bool = True,
    ):
        if payment_data.provider_payment_id:
            stmt = select(models.SubscriptionPayment).where(
                models.SubscriptionPayment.provider == payment_data.provider,
                models.SubscriptionPayment.provider_payment_id == payment_data.provider_payment_id,
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                return existing

        stmt = (
            select(models.Tenant)
            .where(models.Tenant.id == payment_data.tenant_id)
            .with_for_update()
        )
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        stmt = select(models.SubscriptionPlan).where(models.SubscriptionPlan.id == payment_data.plan_id)
        plan = (await db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        payment = models.SubscriptionPayment(
            **payment_data.model_dump(exclude={"payment_date"}),
            payment_date=payment_data.payment_date or SubscriptionService._utc_now_naive(),
            created_by=created_by,
        )
        db.add(payment)

        # Update tenant subscription
        now = datetime.now(timezone.utc)
        sub_end = tenant.subscription_end_date
        if sub_end and sub_end.tzinfo is None:
            sub_end = sub_end.replace(tzinfo=timezone.utc)
        target_date = (
            tenant.subscription_end_date
            if tenant.subscription_end_date
            and sub_end > now
            else now
        )
        tenant.subscription_end_date = target_date + timedelta(days=plan.duration_days)
        tenant.plan = plan.name
        tenant.plan_id = plan.id
        tenant.is_active = True
        tenant.subscription_status = "active"

        await db.flush()
        if commit:
            await db.commit()
            await db.refresh(payment)
        return payment

    @staticmethod
    async def create_checkout_session(
        db: AsyncSession, checkout: schemas.SubscriptionCheckoutCreate
    ) -> schemas.SubscriptionCheckoutSession:
        stmt = select(models.Tenant).where(models.Tenant.id == checkout.tenant_id)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        stmt = select(models.SubscriptionPlan).where(
            models.SubscriptionPlan.id == checkout.plan_id,
            models.SubscriptionPlan.is_active == True,  # noqa: E712
        )
        plan = (await db.execute(stmt)).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        provider_reference = f"sub_{tenant.id}_{plan.id}_{uuid4().hex[:12]}"
        checkout_url = (
            checkout.success_url
            or f"/billing/checkout/{checkout.provider}/{provider_reference}"
        )
        checkout_record = models.SubscriptionCheckout(
            provider_reference=provider_reference,
            tenant_id=tenant.id,
            plan_id=plan.id,
            provider=checkout.provider,
            expected_amount=plan.price or Decimal("0.00"),
            currency="EGP",
            status="pending",
            expires_at=SubscriptionService._utc_now_naive()
            + timedelta(minutes=SubscriptionService.CHECKOUT_TTL_MINUTES),
        )
        db.add(checkout_record)
        await db.commit()

        return schemas.SubscriptionCheckoutSession(
            provider=checkout.provider,
            provider_reference=provider_reference,
            checkout_url=checkout_url,
            amount=plan.price or Decimal("0.00"),
        )

    @staticmethod
    async def handle_provider_webhook(
        db: AsyncSession,
        event: schemas.SubscriptionWebhookEvent,
        *,
        raw_payload: bytes,
        timestamp: str,
        signature: str,
    ) -> models.SubscriptionPayment:
        SubscriptionService._verify_provider_signature(raw_payload, timestamp, signature)

        # Provider callbacks have no authenticated tenant session. Elevate only
        # after signature/replay verification and use the physically isolated
        # PostgreSQL BYPASSRLS connection; the ordinary app role cannot promote
        # itself by setting a custom GUC.
        from backend.database import system_session_scope

        async with system_session_scope() as system_db:
            return await SubscriptionService._handle_verified_provider_webhook(
                system_db, event
            )

    @staticmethod
    async def _handle_verified_provider_webhook(
        db: AsyncSession,
        event: schemas.SubscriptionWebhookEvent,
    ) -> models.SubscriptionPayment:

        if event.provider_status.lower() not in {"paid", "succeeded", "success", "completed"}:
            raise HTTPException(status_code=202, detail="Payment event ignored until it is paid")

        try:
            checkout_stmt = (
                select(models.SubscriptionCheckout)
                .where(
                    models.SubscriptionCheckout.provider_reference
                    == event.provider_reference
                )
                .with_for_update()
            )
            checkout = (await db.execute(checkout_stmt)).scalar_one_or_none()
            if not checkout:
                raise HTTPException(status_code=400, detail="Unknown checkout reference")

            if checkout.status == "completed":
                if checkout.provider_payment_id != event.provider_payment_id:
                    raise HTTPException(
                        status_code=409,
                        detail="Checkout was already completed by another payment",
                    )
                existing_stmt = select(models.SubscriptionPayment).where(
                    models.SubscriptionPayment.provider == event.provider,
                    models.SubscriptionPayment.provider_payment_id
                    == event.provider_payment_id,
                )
                existing = (await db.execute(existing_stmt)).scalar_one_or_none()
                if not existing:
                    raise HTTPException(
                        status_code=409, detail="Checkout payment state is inconsistent"
                    )
                return existing

            if checkout.status != "pending":
                raise HTTPException(
                    status_code=409, detail="Checkout is not available for payment"
                )

            now = SubscriptionService._utc_now_naive()
            if checkout.expires_at <= now:
                checkout.status = "expired"
                await db.commit()
                raise HTTPException(status_code=410, detail="Checkout has expired")

            fields_match = (
                checkout.provider == event.provider
                and checkout.tenant_id == event.tenant_id
                and checkout.plan_id == event.plan_id
                and checkout.currency == event.currency
                and SubscriptionService._money(checkout.expected_amount)
                == SubscriptionService._money(event.amount)
            )
            if not fields_match:
                raise HTTPException(
                    status_code=400,
                    detail="Webhook does not match the server checkout record",
                )

            duplicate_stmt = select(models.SubscriptionPayment).where(
                models.SubscriptionPayment.provider == event.provider,
                models.SubscriptionPayment.provider_payment_id
                == event.provider_payment_id,
            )
            if (await db.execute(duplicate_stmt)).scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail="Provider payment ID is already bound to another checkout",
                )

            payment_data = schemas.SubscriptionPaymentCreate(
                tenant_id=checkout.tenant_id,
                plan_id=checkout.plan_id,
                amount=checkout.expected_amount,
                payment_method=checkout.provider,
                paid_by=event.paid_by,
                notes=event.notes,
                provider=checkout.provider,
                provider_payment_id=event.provider_payment_id,
                provider_status=event.provider_status,
            )
            payment = await SubscriptionService.record_payment(
                db,
                payment_data,
                created_by=f"{checkout.provider}:webhook",
                commit=False,
            )
            checkout.status = "completed"
            checkout.provider_payment_id = event.provider_payment_id
            checkout.processed_at = now
            await db.commit()
            await db.refresh(payment)
            return payment
        except HTTPException:
            if db.in_transaction():
                await db.rollback()
            raise
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=409, detail="Webhook payment was already processed"
            ) from exc
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def delete_payment(db: AsyncSession, payment_id: int):
        stmt = select(models.SubscriptionPayment).where(models.SubscriptionPayment.id == payment_id)
        payment = (await db.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        await db.delete(payment)
        await db.commit()
