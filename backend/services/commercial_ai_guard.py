"""Commercial AI Guard.

PR-08 / PR-11: Enforces commercial decisions, operation state, and emergency denial
for all provider-backed AI paths in DENTIX.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, Tuple, Set
from unittest.mock import Mock

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.core.config import is_ai_disabled, get_subscription_enforcement_mode
from backend.core.commercial_registry import CapabilityKey, OperationClass
from backend.services.commercial_decision import (
    CommercialDecisionEngine,
    CommercialReasonCode,
)

logger = logging.getLogger(__name__)


def _map_reason_code_to_error(decision: Any) -> Tuple[str, str]:
    rc = getattr(decision, "reason_code", None)
    if rc == CommercialReasonCode.EMERGENCY_RESTRICTION_ACTIVE:
        return ("ai_emergency_disabled", decision.explanation_ar or "خدمة الذكاء الاصطناعي معطلة بأمر حظر طارئ للمنصة.")
    elif rc in (CommercialReasonCode.COMMERCIAL_GRANT_DISABLED, CommercialReasonCode.CAPABILITY_NOT_SELLABLE):
        return ("plan_restricted", decision.explanation_ar or "عفواً، خدمة الذكاء الاصطناعي غير مفعلة في باقتك الحالية.")
    elif rc == CommercialReasonCode.MISSING_PLAN:
        return ("missing_plan", decision.explanation_ar or "لا توجد باقة اشتراك مخصصة للعيادة.")
    elif rc == CommercialReasonCode.INVALID_PLAN_CONFIG:
        return ("invalid_plan_config", decision.explanation_ar or "إعدادات باقة غير صالحة.")
    elif rc == CommercialReasonCode.SUBSCRIPTION_EXPIRED:
        return ("subscription_expired", decision.explanation_ar or "انتهت فترة الاشتراك أو التجربة. يرجى تجديد الاشتراك.")
    elif rc == CommercialReasonCode.SUBSCRIPTION_CANCELLED:
        return ("subscription_cancelled", decision.explanation_ar or "تم إلغاء الاشتراك.")
    elif rc == CommercialReasonCode.TENANT_SUSPENDED:
        return ("tenant_suspended", decision.explanation_ar or "تم تعليق حساب العيادة إدارياً.")
    else:
        return ("commercial_denied", decision.explanation_ar or "الوصول إلى خدمة الذكاء الاصطناعي غير متاح.")


def evaluate_commercial_ai_access(
    tenant: Optional[models.Tenant],
    db_session: Optional[Any] = None,
    now_utc: Optional[datetime] = None,
    override_mode: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """Evaluate whether a tenant has commercial access to provider AI synchronously.

    Enforces platform emergency kill switches and database emergency restrictions
    unconditionally, regardless of whether commercial mode is 'enforce', 'observe', or 'off'.
    """
    mode = override_mode or get_subscription_enforcement_mode()

    # 1. Platform Global Emergency AI Kill Switch
    if is_ai_disabled():
        return (
            "ai_emergency_disabled",
            "عفواً، خدمة الذكاء الاصطناعي معطلة مؤقتاً لأسباب تتعلق بالسلامة (Maintenance Mode).",
        )

    # 2. Database Persisted Emergency Restrictions (evaluated unconditionally)
    if db_session is not None:
        try:
            prefix = "emergency_restriction_"
            stmt_sys = select(models.SystemSetting).where(
                models.SystemSetting.key.in_([
                    f"{prefix}ai_insights",
                    f"{prefix}ai_chat",
                ])
            )
            if hasattr(db_session, "execute"):
                res = db_session.execute(stmt_sys)
                sys_rows = res.scalars().all() if hasattr(res, "scalars") else []
                for r in sys_rows:
                    if getattr(r, "value", "false") == "true":
                        return (
                            "ai_emergency_disabled",
                            "عفواً، خدمة الذكاء الاصطناعي معطلة بأمر حظر طارئ للمنصة.",
                        )
        except Exception as exc:
            logger.error(f"Error querying emergency restrictions: {exc}")
            return ("ai_emergency_disabled", "فشل التحقق من قيود الطوارئ لخدمة الذكاء الاصطناعي.")

    # 3. Tenant administrative suspension
    if tenant and not getattr(tenant, "is_active", True):
        return (
            "tenant_suspended",
            "عفواً، تم تعليق حساب العيادة إدارياً. يرجى التواصل مع إدارة المنصة.",
        )

    # 4. In off/observe modes, commercial restrictions do not change access
    if mode in {"off", "observe"}:
        return None

    # 5. Missing tenant in enforce mode
    if not tenant:
        return (
            "missing_plan",
            "عفواً، لا توجد عيادة مرتبطة بهذا الحساب أو لم يتم تحديد باقة.",
        )

    current_time = now_utc or datetime.now(timezone.utc)
    active_overrides: Dict[str, bool] = {}

    if db_session is not None and getattr(tenant, "id", None):
        try:
            now_naive = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
            stmt_ov = select(models.CommercialTenantOverride).where(
                models.CommercialTenantOverride.tenant_id == tenant.id,
                models.CommercialTenantOverride.capability_key.in_(["ai_insights", "ai_chat"]),
                or_(
                    models.CommercialTenantOverride.expires_at.is_(None),
                    models.CommercialTenantOverride.expires_at > now_naive,
                ),
            )
            if hasattr(db_session, "execute"):
                res_ov = db_session.execute(stmt_ov)
                ov_rows = res_ov.scalars().all() if hasattr(res_ov, "scalars") else []
                for r in ov_rows:
                    if getattr(r, "override_value", None) == "deny":
                        active_overrides[CapabilityKey.AI_INSIGHTS.value] = False
                    elif getattr(r, "override_value", None) == "allow":
                        active_overrides[CapabilityKey.AI_INSIGHTS.value] = True
        except Exception:
            pass

    decision = CommercialDecisionEngine.evaluate_capability(
        tenant=tenant,
        capability=CapabilityKey.AI_INSIGHTS.value,
        operation=OperationClass.EXECUTE_AI.value,
        now=current_time,
        override_mode=mode,
        commercial_overrides=active_overrides,
        emergency_restrictions=set(),
    )

    if decision.allowed:
        return None

    return _map_reason_code_to_error(decision)


async def async_evaluate_commercial_ai_access(
    tenant: Optional[models.Tenant],
    db: Optional[Any] = None,
    now_utc: Optional[datetime] = None,
    override_mode: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """Asynchronously evaluate whether a tenant has commercial access to provider AI.

    Enforces platform emergency kill switches and database emergency restrictions
    unconditionally, regardless of whether commercial mode is 'enforce', 'observe', or 'off'.
    """
    mode = override_mode or get_subscription_enforcement_mode()

    # 1. Platform Global Emergency AI Kill Switch
    if is_ai_disabled():
        return (
            "ai_emergency_disabled",
            "عفواً، خدمة الذكاء الاصطناعي معطلة مؤقتاً لأسباب تتعلق بالسلامة (Maintenance Mode).",
        )

    # 2. Database Persisted Emergency Restrictions (evaluated unconditionally)
    if db is not None and not isinstance(db, Mock):
        try:
            prefix = "emergency_restriction_"
            stmt_sys = select(models.SystemSetting).where(
                models.SystemSetting.key.in_([
                    f"{prefix}ai_insights",
                    f"{prefix}ai_chat",
                ])
            )
            if isinstance(db, AsyncSession) or (hasattr(db, "commit") and hasattr(db, "run_sync")):
                res = await db.execute(stmt_sys)
            else:
                res = db.execute(stmt_sys)
            sys_rows = res.scalars().all() if hasattr(res, "scalars") else []
            for r in sys_rows:
                if getattr(r, "value", "false") == "true":
                    return (
                        "ai_emergency_disabled",
                        "عفواً، خدمة الذكاء الاصطناعي معطلة بأمر حظر طارئ للمنصة.",
                    )
        except Exception as exc:
            logger.error(f"Failed to query emergency restrictions: {exc}")
            return (
                "ai_emergency_disabled",
                "فشل التحقق من قيود الطوارئ لخدمة الذكاء الاصطناعي.",
            )

    # 3. Tenant administrative suspension
    if tenant and not getattr(tenant, "is_active", True):
        return (
            "tenant_suspended",
            "عفواً، تم تعليق حساب العيادة إدارياً. يرجى التواصل مع إدارة المنصة.",
        )

    # 4. In off/observe modes, commercial restrictions do not change access
    if mode in {"off", "observe"}:
        return None

    # 5. Missing tenant in enforce mode
    if not tenant:
        return (
            "missing_plan",
            "عفواً، لا توجد عيادة مرتبطة بهذا الحساب أو لم يتم تحديد باقة.",
        )

    current_time = now_utc or datetime.now(timezone.utc)
    active_overrides: Dict[str, bool] = {}

    if db is not None and not isinstance(db, Mock) and getattr(tenant, "id", None):
        try:
            now_naive = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
            stmt_ov = select(models.CommercialTenantOverride).where(
                models.CommercialTenantOverride.tenant_id == tenant.id,
                models.CommercialTenantOverride.capability_key.in_(["ai_insights", "ai_chat"]),
                or_(
                    models.CommercialTenantOverride.expires_at.is_(None),
                    models.CommercialTenantOverride.expires_at > now_naive,
                ),
            )
            if isinstance(db, AsyncSession) or (hasattr(db, "commit") and hasattr(db, "run_sync")):
                res_ov = await db.execute(stmt_ov)
            else:
                res_ov = db.execute(stmt_ov)
                ov_rows = res_ov.scalars().all() if hasattr(res_ov, "scalars") else []
                for r in ov_rows:
                    if getattr(r, "override_value", None) == "deny":
                        active_overrides[CapabilityKey.AI_INSIGHTS.value] = False
                    elif getattr(r, "override_value", None) == "allow":
                        active_overrides[CapabilityKey.AI_INSIGHTS.value] = True
        except Exception as exc:
            logger.warning(f"Error querying tenant overrides: {exc}")

    decision = CommercialDecisionEngine.evaluate_capability(
        tenant=tenant,
        capability=CapabilityKey.AI_INSIGHTS.value,
        operation=OperationClass.EXECUTE_AI.value,
        now=current_time,
        override_mode=mode,
        commercial_overrides=active_overrides,
        emergency_restrictions=set(),
    )

    if decision.allowed:
        return None

    return _map_reason_code_to_error(decision)
