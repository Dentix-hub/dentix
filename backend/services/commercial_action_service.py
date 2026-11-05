"""
Commercial Action Service (PR-11).
Handles explicit Super Admin administrative operations:
- Commercial suspension (subscription_status = 'suspended_admin', is_active remains True per Clinical History Invariant).
- Security disable (is_active = False, emergency hard stop).
- Reactivation (restores is_active = True and valid subscription state).
- Policy reversal (reverses eligible policy changes with an immutable reversal audit record).
All actions support preview mode and enforce reason validation.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.services.subscription_state_machine import SubscriptionState

logger = logging.getLogger(__name__)

REVERSIBLE_ACTIONS = {
    "TENANT_COMMERCIAL_SUSPEND",
    "TENANT_SECURITY_DISABLE",
    "TENANT_REACTIVATE",
    "TENANT_ASSIGN_PLAN",
    "SUBSCRIPTION_SCHEDULE_DOWNGRADE",
    "TENANT_COMMERCIAL_OVERRIDES_UPDATE",
    "SUBSCRIPTION_PLAN_UPDATE",
    "TENANT_CATALOG_RECONCILE",
}

FORBIDDEN_REVERSAL_PREFIXES = (
    "PAYMENT",
    "SUBSCRIPTION_PAYMENT",
    "CHECKOUT",
    "PATIENT_PURGE",
    "TENANT_PERMANENT_DELETE",
    "POLICY_REVERSAL",
)


class CommercialActionService:

    @staticmethod
    async def suspend_tenant(
        db: AsyncSession,
        tenant_id: int,
        request: schemas.TenantCommercialActionRequest,
        admin_user: models.User,
    ) -> schemas.TenantCommercialActionResponse:
        """
        Apply or preview commercial suspension.
        Preserves is_active=True and existing clinical records (Clinical History Invariant).
        Mutations and new provider/paid calls are blocked.
        """
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id).with_for_update()
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        previous_state = {
            "subscription_status": tenant.subscription_status,
            "is_active": tenant.is_active,
        }
        resulting_state = {
            "subscription_status": SubscriptionState.SUSPENDED_ADMIN.value,
            "is_active": tenant.is_active,  # Intentionally preserves is_active for read-only clinical access
        }

        if request.preview:
            return schemas.TenantCommercialActionResponse(
                tenant_id=tenant.id,
                action="TENANT_COMMERCIAL_SUSPEND",
                is_preview=True,
                previous_state=previous_state,
                resulting_state=resulting_state,
                clinical_history_preserved=True,
                message="معاينة الإيقاف التجاري: سيتم حظر العمليات والإنشاءات الجديدة مع الإبقاء على قراءة السجلات الطبية السابقة.",
            )

        tenant.subscription_status = SubscriptionState.SUSPENDED_ADMIN.value
        tenant.policy_revision = (tenant.policy_revision or 1) + 1

        audit = models.AuditLog(
            action="TENANT_COMMERCIAL_SUSPEND",
            entity_type="Tenant",
            entity_id=tenant.id,
            target_username=tenant.name,
            performed_by_id=admin_user.id,
            performed_by_username=admin_user.username,
            old_value=json.dumps(previous_state, ensure_ascii=False),
            new_value=json.dumps(resulting_state, ensure_ascii=False),
            details=request.reason,
            tenant_id=tenant.id,
        )
        db.add(audit)
        await db.commit()
        await db.refresh(tenant)

        return schemas.TenantCommercialActionResponse(
            tenant_id=tenant.id,
            action="TENANT_COMMERCIAL_SUSPEND",
            is_preview=False,
            previous_state=previous_state,
            resulting_state=resulting_state,
            clinical_history_preserved=True,
            message="تم إيقاف العيادة تجارياً بنجاح. القراءة السريرية للتاريخ الطبي ما زالت متاحة.",
        )

    @staticmethod
    async def security_disable_tenant(
        db: AsyncSession,
        tenant_id: int,
        request: schemas.TenantCommercialActionRequest,
        admin_user: models.User,
    ) -> schemas.TenantCommercialActionResponse:
        """
        Apply or preview emergency security disable.
        Sets is_active=False. Halts login and all access immediately.
        """
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id).with_for_update()
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        previous_state = {
            "subscription_status": tenant.subscription_status,
            "is_active": tenant.is_active,
        }
        resulting_state = {
            "subscription_status": tenant.subscription_status,
            "is_active": False,
        }

        if request.preview:
            return schemas.TenantCommercialActionResponse(
                tenant_id=tenant.id,
                action="TENANT_SECURITY_DISABLE",
                is_preview=True,
                previous_state=previous_state,
                resulting_state=resulting_state,
                clinical_history_preserved=False,
                message="معاينة التعطيل الأمني الطارئ: سيتم تعطيل الدخول وجميع العمليات فوراً حتى إعادة التفعيل.",
            )

        tenant.is_active = False
        tenant.policy_revision = (tenant.policy_revision or 1) + 1

        audit = models.AuditLog(
            action="TENANT_SECURITY_DISABLE",
            entity_type="Tenant",
            entity_id=tenant.id,
            target_username=tenant.name,
            performed_by_id=admin_user.id,
            performed_by_username=admin_user.username,
            old_value=json.dumps(previous_state, ensure_ascii=False),
            new_value=json.dumps(resulting_state, ensure_ascii=False),
            details=request.reason,
            tenant_id=tenant.id,
        )
        db.add(audit)
        await db.commit()
        await db.refresh(tenant)

        return schemas.TenantCommercialActionResponse(
            tenant_id=tenant.id,
            action="TENANT_SECURITY_DISABLE",
            is_preview=False,
            previous_state=previous_state,
            resulting_state=resulting_state,
            clinical_history_preserved=False,
            message="تم تعطيل العيادة أمنياً بنجاح.",
        )

    @staticmethod
    async def reactivate_tenant(
        db: AsyncSession,
        tenant_id: int,
        request: schemas.TenantCommercialActionRequest,
        admin_user: models.User,
    ) -> schemas.TenantCommercialActionResponse:
        """
        Apply or preview reactivation of a tenant.
        Restores is_active=True and transitions suspended_admin back to active.
        """
        stmt = select(models.Tenant).where(models.Tenant.id == tenant_id).with_for_update()
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        previous_state = {
            "subscription_status": tenant.subscription_status,
            "is_active": tenant.is_active,
        }

        # If suspended_admin, restore to active; otherwise keep current subscription state
        target_status = (
            SubscriptionState.ACTIVE.value
            if tenant.subscription_status == SubscriptionState.SUSPENDED_ADMIN.value
            else tenant.subscription_status
        )

        resulting_state = {
            "subscription_status": target_status,
            "is_active": True,
        }

        if request.preview:
            return schemas.TenantCommercialActionResponse(
                tenant_id=tenant.id,
                action="TENANT_REACTIVATE",
                is_preview=True,
                previous_state=previous_state,
                resulting_state=resulting_state,
                clinical_history_preserved=True,
                message="معاينة إعادة التفعيل: سيتم استعادة تفعيل العيادة وتنشيط العمليات المعتمدة.",
            )

        tenant.is_active = True
        tenant.subscription_status = target_status
        tenant.policy_revision = (tenant.policy_revision or 1) + 1

        audit = models.AuditLog(
            action="TENANT_REACTIVATE",
            entity_type="Tenant",
            entity_id=tenant.id,
            target_username=tenant.name,
            performed_by_id=admin_user.id,
            performed_by_username=admin_user.username,
            old_value=json.dumps(previous_state, ensure_ascii=False),
            new_value=json.dumps(resulting_state, ensure_ascii=False),
            details=request.reason,
            tenant_id=tenant.id,
        )
        db.add(audit)
        await db.commit()
        await db.refresh(tenant)

        return schemas.TenantCommercialActionResponse(
            tenant_id=tenant.id,
            action="TENANT_REACTIVATE",
            is_preview=False,
            previous_state=previous_state,
            resulting_state=resulting_state,
            clinical_history_preserved=True,
            message="تمت إعادة تفعيل العيادة بنجاح.",
        )

    @staticmethod
    async def reverse_policy_action(
        db: AsyncSession,
        request: schemas.PolicyReversalRequest,
        admin_user: models.User,
    ) -> schemas.PolicyReversalResponse:
        """
        Reverse a previously recorded policy audit log entry.
        Strictly forbids reversing financial payments or destructive operations.
        Creates a new immutable reversal audit log entry.
        """
        stmt = select(models.AuditLog).where(models.AuditLog.id == request.audit_log_id)
        audit_log = (await db.execute(stmt)).scalar_one_or_none()
        if not audit_log:
            raise HTTPException(status_code=404, detail="Audit log entry not found")

        action = (audit_log.action or "").upper()

        # 1. Financial check
        if any(action.startswith(prefix) for prefix in FORBIDDEN_REVERSAL_PREFIXES):
            if "PAYMENT" in action or "CHECKOUT" in action:
                raise HTTPException(
                    status_code=400,
                    detail="Financial payments cannot be reversed via policy undo; use financial refund process.",
                )
            raise HTTPException(
                status_code=400,
                detail=f"Action '{audit_log.action}' cannot be undone via policy reversal.",
            )

        # 2. Reversibility check
        if action not in REVERSIBLE_ACTIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Action '{audit_log.action}' is not eligible for automatic policy reversal.",
            )

        if not audit_log.old_value:
            raise HTTPException(
                status_code=400,
                detail="Audit log does not contain prior state (old_value is empty); cannot infer reversal safely.",
            )

        # 3. Parse old value
        restored_values: Dict[str, Any] = {}
        try:
            restored_values = json.loads(audit_log.old_value)
        except Exception:
            # Handle plain string format e.g. "plan=Essential"
            if "=" in audit_log.old_value:
                parts = audit_log.old_value.split("=")
                restored_values = {parts[0].strip(): parts[1].strip()}
            else:
                restored_values = {"raw_value": audit_log.old_value}

        if request.preview:
            return schemas.PolicyReversalResponse(
                reversal_audit_log_id=None,
                original_audit_log_id=audit_log.id,
                action_reversed=audit_log.action,
                is_preview=True,
                entity_type=audit_log.entity_type or "Unknown",
                entity_id=audit_log.entity_id or 0,
                restored_values=restored_values,
                message=f"معاينة التراجع عن الإجراء '{audit_log.action}': سيتم استعادة القيم السابقة بأمان.",
            )

        # 4. Apply reversal to target entity
        if audit_log.entity_type == "Tenant" and audit_log.entity_id:
            stmt_t = select(models.Tenant).where(models.Tenant.id == audit_log.entity_id).with_for_update()
            target_tenant = (await db.execute(stmt_t)).scalar_one_or_none()
            if target_tenant:
                if "is_active" in restored_values:
                    target_tenant.is_active = bool(restored_values["is_active"])
                if "subscription_status" in restored_values:
                    target_tenant.subscription_status = str(restored_values["subscription_status"])
                if "plan" in restored_values:
                    target_tenant.plan = str(restored_values["plan"])
                if action == "SUBSCRIPTION_SCHEDULE_DOWNGRADE":
                    target_tenant.scheduled_downgrade_plan_id = None
                target_tenant.policy_revision = (target_tenant.policy_revision or 1) + 1

        elif audit_log.entity_type == "SubscriptionPlan" and audit_log.entity_id:
            stmt_p = select(models.SubscriptionPlan).where(models.SubscriptionPlan.id == audit_log.entity_id).with_for_update()
            target_plan = (await db.execute(stmt_p)).scalar_one_or_none()
            if target_plan:
                for k, v in restored_values.items():
                    if hasattr(target_plan, k):
                        setattr(target_plan, k, v)
                target_plan.policy_revision = (target_plan.policy_revision or 1) + 1

        # 5. Create new immutable audit log
        reversal_audit = models.AuditLog(
            action="POLICY_REVERSAL",
            entity_type=audit_log.entity_type,
            entity_id=audit_log.entity_id,
            target_username=audit_log.target_username,
            performed_by_id=admin_user.id,
            performed_by_username=admin_user.username,
            old_value=audit_log.new_value,
            new_value=json.dumps(restored_values, ensure_ascii=False),
            details=f"Reversed policy action '{audit_log.action}' (Audit ID #{audit_log.id}). Reason: {request.reason}",
            tenant_id=audit_log.tenant_id,
        )
        db.add(reversal_audit)
        await db.commit()
        await db.refresh(reversal_audit)

        return schemas.PolicyReversalResponse(
            reversal_audit_log_id=reversal_audit.id,
            original_audit_log_id=audit_log.id,
            action_reversed=audit_log.action,
            is_preview=False,
            entity_type=audit_log.entity_type or "Unknown",
            entity_id=audit_log.entity_id or 0,
            restored_values=restored_values,
            message=f"تم التراجع عن الإجراء '{audit_log.action}' بنجاح وتوثيق عملية الإلغاء.",
        )
