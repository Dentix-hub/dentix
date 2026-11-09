"""Tool Executor.

Executes AI tool commands against the database and enforces the same RBAC
boundaries as the equivalent HTTP workflows.
"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import logging
import traceback

from backend import models
from backend.ai.errors import AIException
from backend.core.permissions import Permission, has_permission
from backend.core.commercial_registry import CapabilityKey, OperationClass
from backend.services.commercial_decision import CommercialDecisionEngine, CommercialReasonCode

from ..ai.handlers.patient import PatientHandler
from ..ai.handlers.appointment import AppointmentHandler
from ..ai.handlers.finance import FinanceHandler
from ..ai.handlers.clinical import ClinicalHandler
from ..ai.handlers.admin import AdminHandler

logger = logging.getLogger(__name__)


_TOOL_REQUIRED_PERMISSION = {
    # Patient tools
    "get_patient_file": Permission.PATIENT_READ,
    "search_patients": Permission.PATIENT_SEARCH,
    "get_patients_with_balance": Permission.RECEIVABLE_READ,
    "summarize_patient": Permission.PATIENT_READ,
    "create_patient": Permission.PATIENT_CREATE,
    # Appointment tools
    "get_appointments": Permission.APPOINTMENT_READ,
    "find_available_slots": Permission.APPOINTMENT_READ,
    "smart_book_appointment": Permission.APPOINTMENT_CREATE,
    "create_appointment": Permission.APPOINTMENT_CREATE,
    # Finance tools — keep AI enforcement aligned with the HTTP endpoints.
    "get_financial_record": Permission.RECEIVABLE_READ,
    "create_payment": Permission.PAYMENT_CREATE,
    "get_procedure_price": Permission.REPORT_READ,
    "get_today_payments": Permission.PAYMENT_READ,
    "get_expenses": Permission.EXPENSE_READ,
    "get_procedures_list": Permission.REPORT_READ,
    # Clinical tools
    "get_recent_treatments": Permission.CLINICAL_READ,
    "get_lab_orders": Permission.CLINICAL_READ,
    "record_medical_note": Permission.CLINICAL_WRITE,
    "add_treatment_voice": Permission.CLINICAL_WRITE,
    "add_treatment": Permission.CLINICAL_WRITE,
    "update_tooth_status": Permission.CLINICAL_WRITE,
    # Operational/admin reads and writes
    "get_dashboard_stats": Permission.APPOINTMENT_READ,
    "get_subscription_info": Permission.SYSTEM_CONFIG,
    "get_clinic_info": Permission.SYSTEM_CONFIG,
    "get_users_list": Permission.SYSTEM_CONFIG,
    "get_doctor_ranking": Permission.REPORT_READ,
    "compare_periods": Permission.REPORT_READ,
    "get_ai_stats": Permission.SYSTEM_CONFIG,
    "learn_clinic_info": Permission.SYSTEM_CONFIG,
    "list_my_knowledge": Permission.SYSTEM_CONFIG,
    "forget_info": Permission.SYSTEM_CONFIG,
    "get_top_procedures": Permission.REPORT_READ,
    "get_revenue_trend": Permission.REPORT_READ,
    "send_appointment_reminders": Permission.APPOINTMENT_UPDATE,
    "send_whatsapp_message": Permission.APPOINTMENT_UPDATE,
}

_TOOL_CAPABILITY_MAP = {
    # Patient tools
    "get_patient_file": CapabilityKey.CLINICAL.value,
    "search_patients": CapabilityKey.CLINICAL.value,
    "get_patients_with_balance": CapabilityKey.BILLING.value,
    "summarize_patient": CapabilityKey.CLINICAL.value,
    "create_patient": CapabilityKey.CLINICAL.value,
    # Appointment tools
    "get_appointments": CapabilityKey.CLINICAL.value,
    "find_available_slots": CapabilityKey.CLINICAL.value,
    "smart_book_appointment": CapabilityKey.CLINICAL.value,
    "create_appointment": CapabilityKey.CLINICAL.value,
    "send_appointment_reminders": CapabilityKey.CLINICAL.value,
    "send_whatsapp_message": CapabilityKey.CLINICAL.value,
    # Finance tools
    "get_financial_record": CapabilityKey.BILLING.value,
    "create_payment": CapabilityKey.BILLING.value,
    "get_procedure_price": CapabilityKey.BILLING.value,
    "get_today_payments": CapabilityKey.BILLING.value,
    "get_expenses": CapabilityKey.BILLING.value,
    "get_procedures_list": CapabilityKey.BILLING.value,
    # Clinical tools
    "get_recent_treatments": CapabilityKey.CLINICAL.value,
    "get_lab_orders": CapabilityKey.LABORATORIES.value,
    "record_medical_note": CapabilityKey.CLINICAL.value,
    "add_treatment_voice": CapabilityKey.CLINICAL.value,
    "add_treatment": CapabilityKey.CLINICAL.value,
    "update_tooth_status": CapabilityKey.CLINICAL.value,
    "parse_medical_dictation": CapabilityKey.CLINICAL.value,
    "analyze_medical_dictation": CapabilityKey.CLINICAL.value,
    # Report & Admin tools
    "get_doctor_ranking": CapabilityKey.EXPORT_REPORTS.value,
    "compare_periods": CapabilityKey.EXPORT_REPORTS.value,
    "get_top_procedures": CapabilityKey.EXPORT_REPORTS.value,
    "get_revenue_trend": CapabilityKey.EXPORT_REPORTS.value,
    "get_dashboard_stats": CapabilityKey.EXPORT_REPORTS.value,
    "get_subscription_info": CapabilityKey.AI_INSIGHTS.value,
    "get_clinic_info": CapabilityKey.AI_INSIGHTS.value,
    "get_users_list": CapabilityKey.AI_INSIGHTS.value,
    "get_ai_stats": CapabilityKey.AI_INSIGHTS.value,
    "learn_clinic_info": CapabilityKey.AI_INSIGHTS.value,
    "list_my_knowledge": CapabilityKey.AI_INSIGHTS.value,
    "forget_info": CapabilityKey.AI_INSIGHTS.value,
}


class ToolExecutor:
    """Execute AI tools with governance, RBAC, and structured errors."""

    def __init__(self, db: AsyncSession, user: models.User, registry=None):
        self.db = db
        self.user = user
        self.tenant_id = user.tenant_id
        self._handlers = {}
        self.registry = registry

    @property
    def patient(self):
        if "patient" not in self._handlers:
            self._handlers["patient"] = PatientHandler(self.db, self.user)
        return self._handlers["patient"]

    @property
    def appointment(self):
        if "appointment" not in self._handlers:
            self._handlers["appointment"] = AppointmentHandler(self.db, self.user)
        return self._handlers["appointment"]

    @property
    def finance(self):
        if "finance" not in self._handlers:
            self._handlers["finance"] = FinanceHandler(self.db, self.user)
        return self._handlers["finance"]

    @property
    def clinical(self):
        if "clinical" not in self._handlers:
            self._handlers["clinical"] = ClinicalHandler(self.db, self.user)
        return self._handlers["clinical"]

    @property
    def admin(self):
        if "admin" not in self._handlers:
            self._handlers["admin"] = AdminHandler(self.db, self.user)
        return self._handlers["admin"]

    @property
    def tools(self):
        return {
            "get_patient_file": self.patient.get_patient_file,
            "search_patients": self.patient.search_patients,
            "get_patients_with_balance": self.patient.get_patients_with_balance,
            "summarize_patient": self.patient.summarize_patient,
            "create_patient": self.patient.create_patient,
            "get_appointments": self.appointment.get_appointments,
            "find_available_slots": self.appointment.find_available_slots,
            "smart_book_appointment": self.appointment.smart_book_appointment,
            "create_appointment": self.appointment.create_appointment,
            "get_financial_record": self.finance.get_financial_record,
            "create_payment": self.finance.create_payment,
            "get_procedure_price": self.finance.get_procedure_price,
            "get_today_payments": self.finance.get_today_payments,
            "get_expenses": self.finance.get_expenses,
            "get_recent_treatments": self.clinical.get_recent_treatments,
            "get_lab_orders": self.clinical.get_lab_orders,
            "record_medical_note": self.clinical.record_medical_note,
            "add_treatment_voice": self.clinical.add_treatment_voice,
            "add_treatment": self.clinical.add_treatment_voice,
            "update_tooth_status": self.clinical.update_tooth_status,
            "parse_medical_dictation": self.clinical.parse_medical_dictation,
            "analyze_medical_dictation": self.clinical.parse_medical_dictation,
            "get_dashboard_stats": self.admin.get_dashboard_stats,
            "get_subscription_info": self.admin.get_subscription_info,
            "get_clinic_info": self.admin.get_clinic_info,
            "get_users_list": self.admin.get_users_list,
            "get_doctor_ranking": self.admin.get_doctor_ranking,
            "compare_periods": self.admin.compare_periods,
            "get_ai_stats": self.admin.get_ai_stats,
            "learn_clinic_info": self.admin.learn_clinic_info,
            "list_my_knowledge": self.admin.list_my_knowledge,
            "forget_info": self.admin.forget_info,
            "get_top_procedures": self.admin.get_top_procedures,
            "get_revenue_trend": self.admin.get_revenue_trend,
            "send_appointment_reminders": self.admin.send_appointment_reminders,
            "send_whatsapp_message": self.admin.send_whatsapp_message,
            "get_procedures_list": self.finance.get_procedure_price,
            "greeting": self._greeting,
            "response": self._greeting,
        }

    def _permission_error(self, tool_name: str) -> Dict[str, Any] | None:
        required = _TOOL_REQUIRED_PERMISSION.get(tool_name)
        if required is None:
            return None
        if has_permission(getattr(self.user, "role", "guest"), required):
            return None
        return {
            "success": False,
            "error_code": "permission_denied",
            "message": "ليس لديك صلاحية لتنفيذ هذا الإجراء عبر المساعد الذكي.",
            "risk_level": "BLOCKED",
        }

    async def _commercial_capability_error(self, tool_name: str) -> Dict[str, Any] | None:
        """PR-08: Enforce commercial per-plan capability in executor as an additional AND condition."""
        req_cap = _TOOL_CAPABILITY_MAP.get(tool_name)
        if not self.tenant_id:
            return None

        # Avoid async lazy-loading relationship error on self.user.tenant
        tenant = self.user.__dict__.get("tenant")
        if (tenant is None or tenant.__dict__.get("subscription_plan") is None or (getattr(tenant, "future_plan_id", None) and "future_plan" not in tenant.__dict__)) and self.tenant_id and self.db is not None:
            try:
                stmt = (
                    select(models.Tenant)
                    .options(selectinload(models.Tenant.subscription_plan), selectinload(models.Tenant.future_plan))
                    .where(models.Tenant.id == self.tenant_id)
                )
                res = await self.db.execute(stmt)
                fetched = res.scalar_one_or_none()
                if fetched is not None:
                    tenant = fetched
            except Exception:
                pass

        if not tenant:
            return None

        from backend.core.ai_tool_policy import normalize_ai_tool_policy
        from backend.services.subscription_period import resolve_subscription_period

        period = resolve_subscription_period(tenant)
        plan = tenant.__dict__.get("future_plan") if period.future_started else tenant.__dict__.get("subscription_plan")
        try:
            allowed_tools = normalize_ai_tool_policy(getattr(plan, "ai_features", None))
            tool_denied = allowed_tools is not None and tool_name not in allowed_tools
        except (ValueError, TypeError):
            tool_denied = True
        from backend.core.config import get_subscription_enforcement_mode
        if tool_denied and get_subscription_enforcement_mode() == "enforce":
            return {"success": False, "error_code": "tool_not_in_plan",
                    "message": "الأداة غير متاحة وفق سياسة أدوات الباقة.", "risk_level": "BLOCKED"}

        if not req_cap:
            return None

        from backend.services.entitlement_service import EntitlementService

        mode = get_subscription_enforcement_mode()
        is_write = tool_name.startswith(("create_", "add_", "update_", "record_", "send_", "learn_", "forget_"))
        op_class = OperationClass.WRITE_BUSINESS.value if is_write else OperationClass.READ_HISTORY.value

        emergency_restrictions, active_overrides = (
            await EntitlementService.async_resolve_restrictions_and_overrides(
                self.db, self.tenant_id
            )
        )
        decision = CommercialDecisionEngine.evaluate_capability(
            tenant=tenant,
            capability=req_cap,
            operation=op_class,
            override_mode=mode,
            commercial_overrides=active_overrides,
            emergency_restrictions=emergency_restrictions,
        )
        if not decision.allowed:
            logger.warning(
                "AI tool denied by commercial capability: tool=%s capability=%s reason=%s",
                tool_name,
                req_cap,
                decision.reason_code.value,
            )
            rc = decision.reason_code
            if rc == CommercialReasonCode.SUBSCRIPTION_EXPIRED:
                error_code = "subscription_expired"
            elif rc == CommercialReasonCode.SUBSCRIPTION_CANCELLED:
                error_code = "subscription_cancelled"
            elif rc == CommercialReasonCode.TENANT_SUSPENDED:
                error_code = "tenant_suspended"
            elif rc == CommercialReasonCode.EMERGENCY_RESTRICTION_ACTIVE:
                error_code = "emergency_restriction_active"
            else:
                error_code = "plan_restricted"

            return {
                "success": False,
                "error_code": error_code,
                "message": decision.explanation_ar or f"عفواً، خاصية '{req_cap}' غير مفعلة في باقة اشتراك العيادة.",
                "risk_level": "BLOCKED",
            }
        return None

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        parent_reservation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a tool after resolving it and re-enforcing domain permission & commercial capability."""
        handler = self.tools.get(tool_name)
        if not handler and self.registry:
            tool_def = self.registry.get(tool_name)
            if tool_def and tool_def.handler:
                handler = tool_def.handler

        if not handler:
            return {
                "success": False,
                "error_code": "unknown_tool",
                "message": f"الأداة '{tool_name}' غير معروفة",
                "risk_level": "UNKNOWN",
            }

        permission_error = self._permission_error(tool_name)
        if permission_error:
            logger.warning(
                "AI tool denied by RBAC: tool=%s user_id=%s role=%s",
                tool_name,
                getattr(self.user, "id", None),
                getattr(self.user, "role", None),
            )
            return permission_error

        capability_error = await self._commercial_capability_error(tool_name)
        if capability_error:
            return capability_error

        from backend.core.config import is_ai_read_only, is_ai_disabled

        if is_ai_disabled():
            return {
                "success": False,
                "error_code": "ai_disabled",
                "message": "AI temporarily disabled for safety (Maintenance Mode).",
                "risk_level": "BLOCKED",
            }

        if is_ai_read_only():
            safe_prefixes = (
                "get_",
                "search_",
                "find_",
                "list_",
                "greeting",
                "response",
                "parse_",
                "analyze_",
            )
            is_safe = tool_name.startswith(safe_prefixes) or tool_name in ["greeting", "response"]
            if not is_safe:
                return {
                    "success": False,
                    "error_code": "read_only_mode",
                    "message": "⚠️ النظام في وضع 'القراءة فقط'. العمليات التي تغير البيانات غير مسموح بها حالياً.",
                    "risk_level": "BLOCKED",
                }

        if parent_reservation_id and isinstance(parameters, dict):
            parameters["_parent_reservation_id"] = parent_reservation_id

        try:
            result = await handler(parameters)
            if isinstance(result, dict):
                if "error" in result:
                    return {
                        "success": False,
                        "error_code": result.get("error"),
                        "message": result.get("message", "حدث خطأ"),
                        "debug_info": result.get("debug"),
                    }
                if "success" not in result:
                    result["success"] = True
            return result
        except AIException as e:
            logger.warning("AI Logic Error (%s): %s", tool_name, e.message)
            return {
                "success": False,
                "error_code": e.code,
                "message": e.message,
                "debug_info": e.debug_info,
            }
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error("Tool Execution Critical Error (%s): %s", tool_name, e, exc_info=True)
            return {
                "success": False,
                "error_code": "execution_failed",
                "message": f"خطأ غير متوقع في تنفيذ {tool_name}.",
                "debug_info": {"trace": error_trace, "error": str(e)},
            }

    async def _greeting(self, params: Dict) -> Dict:
        return {
            "success": True,
            "message": f"أهلاً دكتور {self.user.full_name or self.user.username}، أنا مساعدك الذكي. إزاي أقدر أساعدك النهاردة؟",
            "suggestions": ["احجز موعد", "سعر الخلع", "ملف مريض"],
        }
