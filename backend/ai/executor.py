"""
Tool Executor
Executes AI tool commands against the database.
Delegates logic to domain-specific handlers.
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import traceback

from backend import models
from backend.ai.errors import AIException, AIExecutionError, AIValidationError

from ..ai.handlers.patient import PatientHandler
from ..ai.handlers.appointment import AppointmentHandler
from ..ai.handlers.finance import FinanceHandler
from ..ai.handlers.clinical import ClinicalHandler
from ..ai.handlers.admin import AdminHandler

logger = logging.getLogger(__name__)

class ToolExecutor:
    """
    Executes AI tool commands against the database.
    Delegates logic to domain-specific handlers.
    """
    def __init__(self, db: Session, user: models.User, registry=None):
        self.db = db
        self.user = user
        self.tenant_id = user.tenant_id
        
        # Internal Cache
        self._handlers = {}
        # Optional Registry for extensions
        self.registry = registry

    # Lazy Loaders
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
        """Dynamic tool map (constructed on access to support lazy loading)."""
        return {
            # Patient Tools
            "get_patient_file": self.patient.get_patient_file,
            "search_patients": self.patient.search_patients,
            "get_patients_with_balance": self.patient.get_patients_with_balance,
            "summarize_patient": self.patient.summarize_patient,
            "create_patient": self.patient.create_patient,

            
            # Appointment Tools
            "get_appointments": self.appointment.get_appointments,
            "find_available_slots": self.appointment.find_available_slots,
            "smart_book_appointment": self.appointment.smart_book_appointment,
            "create_appointment": self.appointment.create_appointment,
            
            # Finance Tools
            "get_financial_record": self.finance.get_financial_record,
            "create_payment": self.finance.create_payment,
            "get_procedure_price": self.finance.get_procedure_price,
            "get_today_payments": self.finance.get_today_payments,
            "get_expenses": self.finance.get_expenses,
            
            # Clinical Tools
            "get_recent_treatments": self.clinical.get_recent_treatments,
            "get_lab_orders": self.clinical.get_lab_orders,
            "record_medical_note": self.clinical.record_medical_note,
            "add_treatment_voice": self.clinical.add_treatment_voice,
            "add_treatment": self.clinical.add_treatment_voice, # Alias
            "update_tooth_status": self.clinical.update_tooth_status,
            "parse_medical_dictation": self.clinical.parse_medical_dictation,
            "analyze_medical_dictation": self.clinical.parse_medical_dictation, # Alias
            
            # Admin Tools
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

            
            "get_procedures_list": self.finance.get_procedure_price, # Alias
            "greeting": self._greeting,
            "response": self._greeting
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with structured error handling."""
        # 1. Check Built-in Tools
        handler = self.tools.get(tool_name)
        
        # 2. Check Registry (Extensions)
        if not handler and self.registry:
            tool_def = self.registry.get(tool_name)
            if tool_def and tool_def.handler:
                handler = tool_def.handler

        if not handler:
            return {
                "success": False,
                "error_code": "unknown_tool",
                "message": f"الأداة '{tool_name}' غير معروفة",
                "risk_level": "UNKNOWN"
            }
        
        # 3. Governance: Check Read-Only Mode
        # 3. Governance: Check Global Kill Switch
        from backend.core.config import is_ai_read_only, is_ai_disabled
        
        if is_ai_disabled():
            return {
                "success": False,
                "error_code": "ai_disabled",
                "message": "AI temporarily disabled for safety (Maintenance Mode).",
                "risk_level": "BLOCKED"
            }

        # 4. Governance: Check Read-Only Mode
        if is_ai_read_only():
            # Allow only 'get_', 'search_', 'find_', 'response', 'greeting'
            safe_prefixes = ("get_", "search_", "find_", "list_", "greeting", "response", "parse_", "analyze_")
            is_safe = tool_name.startswith(safe_prefixes) or tool_name in ["greeting", "response"]
            
            if not is_safe:
                return {
                    "success": False,
                    "error_code": "read_only_mode",
                    "message": "⚠️ النظام في وضع 'القراءة فقط'. العمليات التي تغير البيانات غير مسموح بها حالياً.",
                    "risk_level": "BLOCKED"
                }

        try:
            # handler is already resolved above
            result = await handler(parameters)
            
            # If handler returns a dict without 'success', assume true unless 'error' exists
            if isinstance(result, dict):
                if "error" in result:
                     return {
                        "success": False,
                        "error_code": result.get("error"),
                        "message": result.get("message", "حدث خطأ"),
                        "debug_info": result.get("debug")
                     }
                if "success" not in result:
                    result["success"] = True
            
            return result

        except AIException as e:
            logger.warning(f"AI Logic Error ({tool_name}): {e.message}")
            return {
                "success": False,
                "error_code": e.code,
                "message": e.message,
                "debug_info": e.debug_info
            }

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Tool Execution Critical Error ({tool_name}): {e}", exc_info=True)
            
            return {
                "success": False,
                "error_code": "execution_failed", 
                "message": f"خطأ غير متوقع في تنفيذ {tool_name}: {str(e)} (Ver: Fix-Patient-v2)",
                "debug_info": {"trace": error_trace, "error": str(e)}
            }

    async def _greeting(self, params: Dict) -> Dict:
        """Simple greeting handler."""
        return {
            "success": True,
            "message": f"أهلاً دكتور {self.user.full_name or self.user.username}، أنا مساعدك الذكي. إزاي أقدر أساعدك النهاردة؟",
            "suggestions": ["احجز موعد", "سعر الخلع", "ملف مريض"]
        }
