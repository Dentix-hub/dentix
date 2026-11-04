# backend/services/account_admission_service.py
"""
Centralized atomic active-account admission service for PR-05.

Defines the single authoritative count for clinic seat consumption:
  Active login-capable, non-deleted clinic accounts including the owner.
  Inactive accounts, soft-deleted accounts, platform super admins,
  and non-login staff references do NOT consume a seat.

Centralizes atomic admission across all user creation and reactivation paths
using serialized tenant row-locking (with_for_update) to guarantee race-safe
enforcement of 2/5/15 caps across concurrent requests.
"""

from typing import Optional, Tuple
import logging
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from backend import models
from backend.core.commercial_registry import resolve_plan_spec

logger = logging.getLogger("smart_clinic.commercial.admission")


class AccountCapacityExceededError(HTTPException):
    """Raised when adding or reactivating an account would exceed the plan cap."""

    def __init__(self, max_users: int, current_count: int):
        detail = (
            f"لقد وصلت للحد الأقصى من المستخدمين ({max_users}) في خطتك الحالية. "
            "يرجى الترقية لإضافة المزيد."
        )
        super().__init__(status_code=400, detail=detail)
        self.max_users = max_users
        self.current_count = current_count


class AccountAdmissionService:
    @classmethod
    async def get_active_account_count(cls, db: AsyncSession, tenant_id: int) -> int:
        """
        Count active, non-deleted clinic accounts for the tenant.
        Excludes platform super_admins, soft-deleted users, and disabled users.
        """
        stmt = select(func.count(models.User.id)).where(
            models.User.tenant_id == tenant_id,
            models.User.is_active == True,  # noqa: E712
            models.User.is_deleted == False,  # noqa: E712
            models.User.role != "super_admin",
        )
        res = await db.execute(stmt)
        return res.scalar() or 0

    @classmethod
    def resolve_effective_max_users(cls, tenant: models.Tenant) -> Optional[int]:
        """
        Resolve the maximum active users allowed for a tenant.
        1. Explicit SubscriptionPlan.max_users if linked.
        2. Fallback to canonical PlanTierSpec (Essential=2, Professional=5, Business=15).
        3. If a lower-cap downgrade is scheduled, enforce the pending lower cap.
        """
        plan = None
        if "subscription_plan" in getattr(tenant, "__dict__", {}):
            plan = tenant.__dict__["subscription_plan"]
        else:
            try:
                from sqlalchemy.orm import attributes

                state = attributes.instance_state(tenant)
                if "subscription_plan" not in state.unloaded:
                    plan = tenant.subscription_plan
            except Exception:
                pass

        base_max: Optional[int] = None
        if plan is not None and plan.max_users is not None:
            base_max = plan.max_users
        else:
            plan_key = getattr(plan, "name", None) or getattr(tenant, "plan", None)
            if plan_key:
                spec = resolve_plan_spec(plan_key)
                if spec is not None:
                    base_max = spec.max_active_users

        # Check for scheduled pending lower cap (Task 10)
        downgrade_plan = None
        if "scheduled_downgrade_plan" in getattr(tenant, "__dict__", {}):
            downgrade_plan = tenant.__dict__["scheduled_downgrade_plan"]
        elif getattr(tenant, "scheduled_downgrade_plan_id", None) is not None:
            try:
                from sqlalchemy.orm import attributes

                state = attributes.instance_state(tenant)
                if "scheduled_downgrade_plan" not in state.unloaded:
                    downgrade_plan = tenant.scheduled_downgrade_plan
            except Exception:
                pass

        if downgrade_plan is not None and downgrade_plan.max_users is not None:
            if base_max is None:
                return downgrade_plan.max_users
            return min(base_max, downgrade_plan.max_users)

        return base_max

    @classmethod
    async def can_admit_active_account(
        cls, db: AsyncSession, tenant_id: int
    ) -> Tuple[bool, int, Optional[int]]:
        """
        Non-locking capacity check for UI diagnostics and pre-flight queries.
        Returns: (can_admit, current_active_count, effective_max_users)
        """
        stmt = (
            select(models.Tenant)
            .options(
                selectinload(models.Tenant.subscription_plan),
                selectinload(models.Tenant.scheduled_downgrade_plan),
            )
            .where(models.Tenant.id == tenant_id)
        )
        res = await db.execute(stmt)
        tenant = res.scalar_one_or_none()
        if not tenant:
            return False, 0, None

        current_count = await cls.get_active_account_count(db, tenant_id)
        max_users = cls.resolve_effective_max_users(tenant)

        if max_users is None:
            return True, current_count, None

        return (current_count < max_users), current_count, max_users

    @classmethod
    async def admit_active_account(
        cls,
        db: AsyncSession,
        tenant_id: int,
        target_user_id: Optional[int] = None,
    ) -> int:
        """
        Atomically check and admit an active account for a tenant.
        Locks the Tenant row (FOR UPDATE) to serialize concurrent admissions per tenant.

        If target_user_id is provided and the user is already active and non-deleted,
        admission is granted as a no-op without consuming an extra seat.

        Returns:
            The projected active account count after admission.

        Raises:
            AccountCapacityExceededError (HTTP 400) if limit would be exceeded.
            HTTPException (404) if tenant not found.
        """
        # If target user is already active and non-deleted, no additional seat is consumed
        if target_user_id is not None:
            target_res = await db.execute(
                select(models.User).where(
                    models.User.id == target_user_id,
                    models.User.tenant_id == tenant_id,
                )
            )
            target_user = target_res.scalar_one_or_none()
            if target_user and target_user.is_active and not target_user.is_deleted:
                return await cls.get_active_account_count(db, tenant_id)

        # 1. Row-lock Tenant to serialize admissions per tenant (PostgreSQL row lock; safe on SQLite)
        stmt_tenant = (
            select(models.Tenant)
            .options(
                selectinload(models.Tenant.subscription_plan),
                selectinload(models.Tenant.scheduled_downgrade_plan),
            )
            .where(models.Tenant.id == tenant_id)
            .with_for_update()
        )
        res_tenant = await db.execute(stmt_tenant)
        tenant = res_tenant.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # 2. Count current active accounts inside the locked transaction
        current_count = await cls.get_active_account_count(db, tenant_id)

        # 3. Resolve max active users limit
        max_users = cls.resolve_effective_max_users(tenant)

        # 4. Check capacity
        if max_users is not None and current_count >= max_users:
            logger.warning(
                "Admission denied for tenant %s: current_count=%s >= max_users=%s",
                tenant_id,
                current_count,
                max_users,
            )
            raise AccountCapacityExceededError(max_users=max_users, current_count=current_count)

        logger.info(
            "Account admitted for tenant %s: current_count=%s, max_users=%s (projected=%s)",
            tenant_id,
            current_count,
            max_users,
            current_count + 1,
        )
        return current_count + 1
