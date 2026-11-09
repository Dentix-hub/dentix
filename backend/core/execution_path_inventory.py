"""
DENTIX Execution Path Inventory.

Documents all registered endpoints, AI executors, background jobs, and compatibility
routes across DENTIX modules, mapping each to its canonical commercial capability key,
operation class, RBAC permissions, patient visibility constraints, and existing test suites.

Compiled for PR-02 (Canonical Commercial Decision Foundation).
"""

from dataclasses import dataclass, field
from typing import List, Optional
from backend.core.commercial_registry import CapabilityKey, OperationClass


@dataclass(frozen=True)
class ExecutionPathEntry:
    module: str
    capability_key: str
    operation_class: str
    route: str
    method: str
    auth_required: bool
    rbac_roles_or_permissions: List[str]
    patient_visibility_constrained: bool
    rollout_flag_key: Optional[str] = None
    compatibility_aliases: List[str] = field(default_factory=list)
    existing_tests: List[str] = field(default_factory=list)
    enforcement_phase: str = "PR-02 (Foundation)"
    notes: str = ""


EXECUTION_PATH_INVENTORY: List[ExecutionPathEntry] = [
    # =========================================================================
    # 1. CLINICAL & APPOINTMENTS (Enforcement in PR-09A)
    # =========================================================================
    ExecutionPathEntry(
        module="patients",
        capability_key=CapabilityKey.CLINICAL.value,
        operation_class=OperationClass.READ_HISTORY.value,
        route="/api/v1/patients/{patient_id}",
        method="GET",
        auth_required=True,
        rbac_roles_or_permissions=["doctor", "receptionist", "admin", "super_admin", "clinic_owner"],
        patient_visibility_constrained=True,
        existing_tests=["backend/tests/test_patients.py", "backend/tests/test_patient_visibility.py"],
        enforcement_phase="PR-09A",
        notes="Clinical read invariant permanently permitted. Doctor patient visibility enforced via PatientVisibilityService.",
    ),
    ExecutionPathEntry(
        module="patients",
        capability_key=CapabilityKey.CLINICAL.value,
        operation_class=OperationClass.WRITE_BUSINESS.value,
        route="/api/v1/patients",
        method="POST",
        auth_required=True,
        rbac_roles_or_permissions=["receptionist", "admin", "clinic_owner", "super_admin"],
        patient_visibility_constrained=False,
        existing_tests=["backend/tests/test_patients.py"],
        enforcement_phase="PR-09A",
        notes="Creating new patient records is subject to active subscription write mode.",
    ),
    ExecutionPathEntry(
        module="appointments",
        capability_key=CapabilityKey.CLINICAL.value,
        operation_class=OperationClass.READ_HISTORY.value,
        route="/api/v1/appointments",
        method="GET",
        auth_required=True,
        rbac_roles_or_permissions=["doctor", "receptionist", "admin", "clinic_owner", "super_admin"],
        patient_visibility_constrained=True,
        existing_tests=["backend/tests/test_appointments.py", "backend/tests/test_ai_agent_authorization.py"],
        enforcement_phase="PR-09A",
        notes="Doctor sees only appointments for canonically visible patients.",
    ),
    ExecutionPathEntry(
        module="appointments",
        capability_key=CapabilityKey.CLINICAL.value,
        operation_class=OperationClass.WRITE_BUSINESS.value,
        route="/api/v1/appointments",
        method="POST",
        auth_required=True,
        rbac_roles_or_permissions=["receptionist", "admin", "clinic_owner", "doctor", "super_admin"],
        patient_visibility_constrained=True,
        existing_tests=["backend/tests/test_appointments.py"],
        enforcement_phase="PR-09A",
        notes="Appointment booking blocked if subscription is expired.",
    ),
    ExecutionPathEntry(
        module="treatments",
        capability_key=CapabilityKey.CLINICAL.value,
        operation_class=OperationClass.READ_HISTORY.value,
        route="/api/v1/treatments/patient/{patient_id}",
        method="GET",
        auth_required=True,
        rbac_roles_or_permissions=["doctor", "admin", "clinic_owner", "super_admin"],
        patient_visibility_constrained=True,
        existing_tests=["backend/tests/test_treatments.py", "backend/tests/test_clinical_workspace_snapshot.py"],
        enforcement_phase="PR-09A",
        notes="Clinical history read invariant: permanent access even after subscription expiry.",
    ),
    ExecutionPathEntry(
        module="treatment_plans",
        capability_key=CapabilityKey.CLINICAL.value,
        operation_class=OperationClass.READ_HISTORY.value,
        route="/api/v1/treatment-plans/patient/{patient_id}",
        method="GET",
        auth_required=True,
        rbac_roles_or_permissions=["doctor", "admin", "clinic_owner", "super_admin"],
        patient_visibility_constrained=True,
        compatibility_aliases=["/treatment-plans/patient/{patient_id}"],
        existing_tests=["backend/tests/test_treatment_plans.py"],
        enforcement_phase="PR-09A",
        notes="Dual registered in main.py (/api/v1 and unprefixed).",
    ),
    ExecutionPathEntry(
        module="care_sessions",
        capability_key=CapabilityKey.CLINICAL.value,
        operation_class=OperationClass.WRITE_BUSINESS.value,
        route="/api/v1/care-sessions",
        method="POST",
        auth_required=True,
        rbac_roles_or_permissions=["doctor", "super_admin"],
        patient_visibility_constrained=True,
        rollout_flag_key="clinical_vnext_native_writes",
        compatibility_aliases=["/care-sessions"],
        existing_tests=["backend/tests/services/test_care_session_service.py"],
        enforcement_phase="PR-09A",
        notes="Dual registered. Behind clinical rollout flag.",
    ),
    ExecutionPathEntry(
        module="prescriptions",
        capability_key=CapabilityKey.CLINICAL.value,
        operation_class=OperationClass.READ_HISTORY.value,
        route="/api/v1/prescriptions/patient/{patient_id}",
        method="GET",
        auth_required=True,
        rbac_roles_or_permissions=["doctor", "admin", "clinic_owner", "super_admin"],
        patient_visibility_constrained=True,
        existing_tests=["backend/tests/test_prescriptions.py"],
        enforcement_phase="PR-09A",
        notes="Clinical history invariant applies.",
    ),

    # =========================================================================
    # 2. BILLING & FINANCIALS (Enforcement in PR-09B)
    # =========================================================================
    ExecutionPathEntry(
        module="payments",
        capability_key=CapabilityKey.BILLING.value,
        operation_class=OperationClass.WRITE_BUSINESS.value,
        route="/api/v1/payments",
        method="POST",
        auth_required=True,
        rbac_roles_or_permissions=["accountant", "clinic_owner", "admin", "receptionist", "super_admin"],
        patient_visibility_constrained=True,
        existing_tests=["backend/tests/test_payments.py"],
        enforcement_phase="PR-09B",
        notes="Receptionist can record patient payments; admin/accountant can refund.",
    ),
    ExecutionPathEntry(
        module="expenses",
        capability_key=CapabilityKey.BILLING.value,
        operation_class=OperationClass.WRITE_BUSINESS.value,
        route="/api/v1/expenses",
        method="POST",
        auth_required=True,
        rbac_roles_or_permissions=["accountant", "clinic_owner", "admin", "super_admin"],
        patient_visibility_constrained=False,
        existing_tests=["backend/tests/test_expenses.py"],
        enforcement_phase="PR-09B",
        notes="Restricted to financial administrative roles.",
    ),
    ExecutionPathEntry(
        module="accounting",
        capability_key=CapabilityKey.BILLING.value,
        operation_class=OperationClass.READ_HISTORY.value,
        route="/api/v1/accounting/general-ledger",
        method="GET",
        auth_required=True,
        rbac_roles_or_permissions=["accountant", "clinic_owner", "super_admin"],
        patient_visibility_constrained=False,
        existing_tests=["backend/tests/test_accounting.py"],
        enforcement_phase="PR-09B",
        notes="Clinic-wide ledger access.",
    ),
    ExecutionPathEntry(
        module="financials",
        capability_key=CapabilityKey.BILLING.value,
        operation_class=OperationClass.READ_HISTORY.value,
        route="/api/v1/financials/summary",
        method="GET",
        auth_required=True,
        rbac_roles_or_permissions=["clinic_owner", "super_admin"],
        patient_visibility_constrained=False,
        existing_tests=["backend/tests/test_financials.py"],
        enforcement_phase="PR-09B",
        notes="Sensitive clinic revenue figures.",
    ),

    # =========================================================================
    # 3. LABORATORIES & INVENTORY (Enforcement in PR-09C)
    # =========================================================================
    ExecutionPathEntry(
        module="laboratories",
        capability_key=CapabilityKey.LABORATORIES.value,
        operation_class=OperationClass.WRITE_BUSINESS.value,
        route="/api/v1/laboratories/orders",
        method="POST",
        auth_required=True,
        rbac_roles_or_permissions=["doctor", "admin", "clinic_owner", "receptionist", "super_admin"],
        patient_visibility_constrained=True,
        existing_tests=["backend/tests/test_laboratories.py", "backend/tests/services/test_lab_handoff_service.py"],
        enforcement_phase="PR-09C",
        notes="External laboratory prosthetic work items.",
    ),
    ExecutionPathEntry(
        module="inventory",
        capability_key=CapabilityKey.INVENTORY.value,
        operation_class=OperationClass.WRITE_BUSINESS.value,
        route="/api/v1/inventory/stock-movements",
        method="POST",
        auth_required=True,
        rbac_roles_or_permissions=["admin", "clinic_owner", "super_admin"],
        patient_visibility_constrained=False,
        existing_tests=["backend/tests/test_inventory.py"],
        enforcement_phase="PR-09C",
        notes="Stock batch adjustments.",
    ),

    # =========================================================================
    # 4. EXPORT & REPORTS (Enforcement in PR-09B / PR-09C)
    # =========================================================================
    ExecutionPathEntry(
        module="dashboard",
        capability_key=CapabilityKey.EXPORT_REPORTS.value,
        operation_class=OperationClass.READ_HISTORY.value,
        route="/api/v1/dashboard/stats",
        method="GET",
        auth_required=True,
        rbac_roles_or_permissions=["clinic_owner", "admin", "doctor", "accountant", "super_admin"],
        patient_visibility_constrained=False,
        existing_tests=["backend/tests/test_dashboard.py"],
        enforcement_phase="PR-09B",
        notes="Role-filtered dashboard metrics.",
    ),
    ExecutionPathEntry(
        module="finance_exports",
        capability_key=CapabilityKey.EXPORT_REPORTS.value,
        operation_class=OperationClass.EXPORT_DATA.value,
        route="/api/v1/finance/export/csv",
        method="GET",
        auth_required=True,
        rbac_roles_or_permissions=["clinic_owner", "accountant", "super_admin"],
        patient_visibility_constrained=False,
        existing_tests=["backend/tests/test_finance_exports.py"],
        enforcement_phase="PR-09B",
        notes="Export blocked if commercial export_reports capability is disabled.",
    ),

    # =========================================================================
    # 5. AI ASSISTANT & EXECUTORS (Enforcement in PR-08)
    # =========================================================================
    ExecutionPathEntry(
        module="ai",
        capability_key=CapabilityKey.AI_INSIGHTS.value,
        operation_class=OperationClass.EXECUTE_AI.value,
        route="/api/v1/ai/chat",
        method="POST",
        auth_required=True,
        rbac_roles_or_permissions=["AI_CHAT"],
        patient_visibility_constrained=True,
        existing_tests=["backend/tests/test_ai_agent_authorization.py", "backend/tests/test_ai_service.py"],
        enforcement_phase="PR-08",
        notes="Provider-backed conversational queries. Consumes 1 unit of daily quota.",
    ),
    ExecutionPathEntry(
        module="ai_assist",
        capability_key=CapabilityKey.AI_INSIGHTS.value,
        operation_class=OperationClass.EXECUTE_AI.value,
        route="/api/v1/ai-assist/suggest",
        method="POST",
        auth_required=True,
        rbac_roles_or_permissions=["AI_CHAT"],
        patient_visibility_constrained=True,
        existing_tests=["backend/tests/test_ai_agent_authorization.py"],
        enforcement_phase="PR-08",
        notes="Context-aware suggestions.",
    ),
    ExecutionPathEntry(
        module="analytics_ai_v2",
        capability_key=CapabilityKey.AI_INSIGHTS.value,
        operation_class=OperationClass.EXECUTE_AI.value,
        route="/api/v1/admin/ai/analyze-clinic",
        method="POST",
        auth_required=True,
        rbac_roles_or_permissions=["AI_CHAT", "REPORT_READ"],
        patient_visibility_constrained=False,
        existing_tests=["backend/tests/test_ai_agent_authorization.py"],
        enforcement_phase="PR-08",
        notes="Requires both AI_CHAT and REPORT_READ (verified in PR-01).",
    ),

    # =========================================================================
    # 6. TENANT BACKUPS & ARCHIVES (Enforcement in PR-09C)
    # =========================================================================
    ExecutionPathEntry(
        module="tenant_backups",
        capability_key=CapabilityKey.TENANT_BACKUPS.value,
        operation_class=OperationClass.EXPORT_DATA.value,
        route="/api/v1/tenant-backups/snapshot",
        method="POST",
        auth_required=True,
        rbac_roles_or_permissions=["clinic_owner", "super_admin"],
        patient_visibility_constrained=False,
        existing_tests=["backend/tests/test_tenant_backup.py"],
        enforcement_phase="PR-09C",
        notes="Clinic-wide snapshot creation.",
    ),

    # =========================================================================
    # 7. BACKGROUND JOBS & WORKERS (Enforcement in PR-06 / PR-09)
    # =========================================================================
    ExecutionPathEntry(
        module="subscription_checker",
        capability_key=CapabilityKey.CLINICAL.value,
        operation_class=OperationClass.READ_HISTORY.value,
        route="worker:check_expired_subscriptions",
        method="JOB",
        auth_required=False,
        rbac_roles_or_permissions=["SYSTEM_PRINCIPAL"],
        patient_visibility_constrained=False,
        existing_tests=["backend/tests/test_entitlement_service.py"],
        enforcement_phase="PR-06",
        notes="Marks expired subscriptions; never mutates is_active = False.",
    ),
]


def get_paths_for_capability(capability_key: str) -> List[ExecutionPathEntry]:
    """Retrieve all execution paths associated with a given capability."""
    return [e for e in EXECUTION_PATH_INVENTORY if e.capability_key == capability_key]
