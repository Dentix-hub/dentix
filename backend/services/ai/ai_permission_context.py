"""
AI Permission Context (Multi-Doctor Support)

SECURITY CRITICAL: This module ensures AI never exceeds user permissions.

The AI Assistant:
- Can ONLY see data the user is allowed to see
- Must REFUSE to answer about hidden data
- Cannot infer or guess restricted information
"""

from sqlalchemy.orm import Session
from typing import Set
from dataclasses import dataclass, field
from backend.models import User
from backend.services.visibility_service import get_visibility_service


@dataclass
class AIPermissionContext:
    """
    Context passed to AI for permission-aware responses.

    This context MUST be created fresh for each AI request.
    """

    user_id: int
    user_role: str
    tenant_id: int
    visibility_mode: str
    visible_patient_ids: Set[int] = field(default_factory=set)
    can_view_other_history: bool = False

    @classmethod
    def from_user(
        cls, db: Session, user: User, tenant_id: int
    ) -> "AIPermissionContext":
        """
        Create context from user and database session.

        This method:
        1. Gets user permissions
        2. Pre-filters visible patients
        3. Returns ready-to-use context
        """
        visibility_service = get_visibility_service(db, user, tenant_id)

        return cls(
            user_id=user.id,
            user_role=user.role,
            tenant_id=tenant_id,
            visibility_mode=user.patient_visibility_mode or "all_assigned",
            visible_patient_ids=visibility_service.get_visible_patient_ids(),
            can_view_other_history=user.can_view_other_doctors_history or False,
        )

    def can_access_patient(self, patient_id: int) -> bool:
        """Check if AI can access data for a specific patient."""
        if self.user_role == "admin":
            return True
        return patient_id in self.visible_patient_ids

    def get_system_prompt_rules(self) -> str:
        """
        Get permission rules to inject into AI system prompt.

        CRITICAL: These rules MUST be included in every AI request.
        """
        return f"""
=== PERMISSION RULES (MANDATORY) ===
Role: {self.user_role}
Visibility Mode: {self.visibility_mode}
Allowed Patients: {len(self.visible_patient_ids)} patients

STRICT RULES:
1. You can ONLY answer questions about patients in your allowed list
2. If asked about a patient NOT in your list, respond: "ليس لدي صلاحية للوصول لهذه المعلومات"
3. NEVER reveal that other patients exist
4. NEVER aggregate data across all patients
5. NEVER guess or infer hidden information
6. If unsure about permission, REFUSE the request

{"ADMIN MODE: Full access to all data" if self.user_role == "admin" else "DOCTOR MODE: Limited to assigned/appointment patients only"}
=== END RULES ===
"""

    def filter_tool_results(self, patients: list) -> list:
        """
        Filter AI tool results to only allowed patients.

        This is a SAFETY NET - tools should also filter internally.
        """
        if self.user_role == "admin":
            return patients

        return [
            p for p in patients if getattr(p, "id", None) in self.visible_patient_ids
        ]

    def get_safe_error_response(self) -> str:
        """Standard response when permission is denied."""
        return "ليس لدي صلاحية للوصول لهذه المعلومات"


def create_ai_context(db: Session, user: User, tenant_id: int) -> AIPermissionContext:
    """
    Factory function to create AI context.

    Usage:
        context = create_ai_context(db, current_user, tenant_id)
        system_prompt = base_prompt + context.get_system_prompt_rules()
    """
    return AIPermissionContext.from_user(db, user, tenant_id)
