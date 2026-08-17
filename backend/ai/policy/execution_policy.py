from typing import Dict, List, Optional

from pydantic import BaseModel

from backend.core.permissions import Permission, has_permission


class PolicyRule(BaseModel):
    allowed_tools: List[str]
    requires_confirmation: bool = True
    required_permission: Optional[Permission] = None
    allowed_fields: Optional[List[str]] = None


class AIExecutionPolicy:
    """Central Policy Engine for AI Actions."""

    _POLICIES: Dict[str, PolicyRule] = {
        "student_registration": PolicyRule(
            allowed_tools=["create_patient"],
            requires_confirmation=True,
            required_permission=Permission.PATIENT_CREATE,
        ),
        "patient_registration": PolicyRule(
            allowed_tools=["create_patient"],
            requires_confirmation=True,
            required_permission=Permission.PATIENT_CREATE,
        ),
        "update_patient": PolicyRule(
            allowed_tools=["update_patient_record"],
            requires_confirmation=True,
            required_permission=Permission.PATIENT_UPDATE,
            allowed_fields=[
                "phone", "age", "date_of_birth", "address", "notes", "name",
                "default_price_list_id", "assigned_doctor_id", "gender", "medical_history",
            ],
        ),
        "book_appointment": PolicyRule(
            allowed_tools=["create_appointment", "smart_book_appointment"],
            requires_confirmation=True,
            required_permission=Permission.APPOINTMENT_CREATE,
        ),
        "financial_record": PolicyRule(
            allowed_tools=["create_payment", "add_expense"],
            requires_confirmation=True,
            required_permission=Permission.FINANCIAL_WRITE,
        ),
        "general_query": PolicyRule(
            allowed_tools=["response", "get_procedure_price", "get_working_hours"],
            requires_confirmation=False,
            required_permission=None,
        ),
    }

    @classmethod
    def check_permission(cls, intent: str, role: str) -> bool:
        policy = cls._POLICIES.get(intent)
        if not policy:
            return False
        if not policy.required_permission:
            return True
        return has_permission(role, policy.required_permission)

    @classmethod
    def get_policy(cls, intent: str) -> Optional[PolicyRule]:
        return cls._POLICIES.get(intent)

    @classmethod
    def get_policy_by_tool(cls, tool_name: str) -> Optional[PolicyRule]:
        for policy in cls._POLICIES.values():
            if tool_name in policy.allowed_tools:
                return policy
        return None

    @classmethod
    def check_requires_confirmation(cls, tool_name: str) -> bool:
        policy = cls.get_policy_by_tool(tool_name)
        return policy.requires_confirmation if policy else False


policy_engine = AIExecutionPolicy()
