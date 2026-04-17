from enum import Enum
from typing import Set, Dict


class Role(str, Enum):
    """
    Defines the roles available in the Smart Clinic system.
    """

    ADMIN = "admin"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"
    NURSE = "nurse"
    ACCOUNTANT = "accountant"
    PATIENT = "patient"
    GUEST = "guest"
    SUPER_ADMIN = "super_admin"
    MANAGER = "manager"
    ASSISTANT = "assistant"

# Role groups
DOCTOR_ROLES = [Role.DOCTOR.value, Role.ADMIN.value, Role.SUPER_ADMIN.value]
STAFF_ROLES = [Role.RECEPTIONIST.value, Role.ASSISTANT.value, Role.NURSE.value]
ADMIN_ROLES = [Role.ADMIN.value, Role.SUPER_ADMIN.value]


class PatientVisibilityMode(str, Enum):
    """
    Defines how doctors see patients (Multi-Doctor Support).
    """

    ALL_ASSIGNED = "all_assigned"  # Only patients assigned to this doctor
    APPOINTMENTS_ONLY = "appointments_only"  # Only patients with appointments
    MIXED = "mixed"  # Union of assigned and appointments


class Permission(str, Enum):
    """
    Defines granular permissions for system actions.
    Following the format: resource:action
    """

    # Patient Management
    PATIENT_CREATE = "patient:create"
    PATIENT_READ = "patient:read"
    PATIENT_UPDATE = "patient:update"
    PATIENT_DELETE = "patient:delete"
    PATIENT_SEARCH = "patient:search"

    # Clinical Data (Strictly regulated)
    CLINICAL_READ = "clinical:read"
    CLINICAL_WRITE = "clinical:write"  # Notes, diagnoses
    TREATMENT_PLAN_WRITE = "treatment:write"

    # Appointments
    APPOINTMENT_CREATE = "appointment:create"
    APPOINTMENT_READ = "appointment:read"
    APPOINTMENT_UPDATE = "appointment:update"
    APPOINTMENT_CANCEL = "appointment:cancel"

    # Financial
    FINANCIAL_READ = "financial:read"
    FINANCIAL_WRITE = "financial:write"  # Payments, invoices

    # Inventory
    INVENTORY_READ = "inventory:read"
    INVENTORY_MANAGE = "inventory:manage"

    # System
    SYSTEM_CONFIG = "system:config"
    AUDIT_READ = "audit:read"

    # AI Specific
    AI_CHAT = "ai:chat"
    AI_EXECUTE_UNSAFE = "ai:execute_unsafe"  # High risk AI actions


# RBAC Matrix: Defines which permissions each role holds.
# This is the Source of Truth for "Who can do What".
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: {p for p in Permission},  # Super Admin has all permissions
    Role.ADMIN: {p for p in Permission},  # Admin has all permissions
    Role.MANAGER: {
        Permission.PATIENT_CREATE,
        Permission.PATIENT_READ,
        Permission.PATIENT_UPDATE,
        Permission.PATIENT_SEARCH,
        Permission.APPOINTMENT_READ,
        Permission.APPOINTMENT_CREATE,
        Permission.APPOINTMENT_UPDATE,
        Permission.APPOINTMENT_CANCEL,
        Permission.FINANCIAL_READ,
        Permission.FINANCIAL_WRITE,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_MANAGE,
        Permission.SYSTEM_CONFIG,
        Permission.AI_CHAT,
    },
    Role.ASSISTANT: {
        Permission.PATIENT_READ,
        Permission.PATIENT_SEARCH,
        Permission.APPOINTMENT_READ,
        Permission.CLINICAL_READ,
        Permission.INVENTORY_READ,
        Permission.AI_CHAT,
    },
    Role.DOCTOR: {
        Permission.PATIENT_CREATE,
        Permission.PATIENT_READ,
        Permission.PATIENT_UPDATE,
        Permission.PATIENT_SEARCH,
        Permission.CLINICAL_READ,
        Permission.CLINICAL_WRITE,
        Permission.TREATMENT_PLAN_WRITE,
        Permission.APPOINTMENT_READ,
        Permission.APPOINTMENT_CREATE,
        Permission.INVENTORY_READ,
        Permission.AI_CHAT,
    },
    Role.RECEPTIONIST: {
        Permission.PATIENT_CREATE,
        Permission.PATIENT_READ,
        Permission.PATIENT_UPDATE,  # Contact info only (enforced by service layer field checks)
        Permission.PATIENT_SEARCH,
        Permission.APPOINTMENT_CREATE,
        Permission.APPOINTMENT_READ,
        Permission.APPOINTMENT_UPDATE,
        Permission.APPOINTMENT_CANCEL,
        Permission.FINANCIAL_READ,  # View balance
        Permission.FINANCIAL_WRITE,  # Collect payment
        Permission.INVENTORY_READ,
        Permission.AI_CHAT,
    },
    Role.NURSE: {
        Permission.PATIENT_READ,
        Permission.PATIENT_SEARCH,
        Permission.CLINICAL_READ,
        Permission.CLINICAL_WRITE,  # Vitals, basic notes
        Permission.APPOINTMENT_READ,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_MANAGE,
        Permission.AI_CHAT,
    },
    Role.ACCOUNTANT: {
        Permission.FINANCIAL_READ,
        Permission.FINANCIAL_WRITE,
        Permission.PATIENT_READ,  # Needs to see who paid
        Permission.APPOINTMENT_READ,
        Permission.AI_CHAT,
    },
    Role.GUEST: set(),
}


def has_permission(role: str, permission: Permission) -> bool:
    """
    Checks if a given role string has the specific permission.
    Gracefully handles invalid role strings by returning False.
    """
    try:
        role_enum = Role(role.lower())
    except ValueError:
        return False

    user_perms = ROLE_PERMISSIONS.get(role_enum, set())
    return permission in user_perms


def get_role_permissions(role: str) -> Set[Permission]:
    try:
        role_enum = Role(role.lower())
        return ROLE_PERMISSIONS.get(role_enum, set())
    except ValueError:
        return set()


# ============================================
# FastAPI Dependencies for RBAC Enforcement
# ============================================

def require_permission(*permissions: Permission):
    """
    FastAPI dependency that enforces RBAC permissions.

    Usage in routers:
        @router.delete("/patients/{id}")
        def delete_patient(
            user=Depends(require_permission(Permission.PATIENT_DELETE)),
            ...
        ):

    Multiple permissions (ANY must match):
        @router.post("/clinical")
        def write_clinical(
            user=Depends(require_permission(Permission.CLINICAL_WRITE, Permission.TREATMENT_PLAN_WRITE)),
            ...
        ):
    """
    from fastapi import Depends, HTTPException

    def _checker(current_user=Depends(_get_current_user_lazy())):
        user_role = getattr(current_user, "role", "guest")

        # Check if user has ANY of the required permissions
        for perm in permissions:
            if has_permission(user_role, perm):
                return current_user

        raise HTTPException(
            status_code=403,
            detail=f"Permission denied. Required: {[p.value for p in permissions]}",
        )

    return _checker


def _get_current_user_lazy():
    """Lazy import to avoid circular imports with auth module."""
    def _inner():
        from backend.routers.auth import get_current_user
        return get_current_user
    dep = _inner()
    return dep

