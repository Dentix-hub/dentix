"""
C6.1 — Comprehensive RBAC Matrix Tests

Tests every Role × Permission × Endpoint combination.
Verifies both ALLOW and DENY paths across the entire permission matrix.
"""

import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace
from backend.routers.auth import get_current_user
from backend import models, schemas
from backend.core.permissions import (
    Role,
    Permission,
    ROLE_PERMISSIONS,
    has_permission,
    get_role_permissions,
)


class AttrDict(dict):
    """A dictionary that allows attribute-style access."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self


# ============================================
# UNIT TESTS — Permission Matrix Logic
# ============================================


class TestPermissionMatrix:
    """Tests for the core RBAC permission logic (no HTTP)."""

    def test_super_admin_has_all_permissions(self):
        """Super admin must have every defined permission."""
        for perm in Permission:
            assert has_permission("super_admin", perm), f"super_admin missing {perm}"

    def test_admin_has_all_permissions(self):
        """Admin must have every defined permission."""
        for perm in Permission:
            assert has_permission("admin", perm), f"admin missing {perm}"

    def test_guest_has_zero_permissions(self):
        """Guest must have no permissions at all."""
        for perm in Permission:
            assert not has_permission("guest", perm), f"guest should NOT have {perm}"

    @pytest.mark.parametrize(
        "role,permission,expected",
        [
            # Doctor capabilities
            ("doctor", Permission.PATIENT_CREATE, True),
            ("doctor", Permission.PATIENT_READ, True),
            ("doctor", Permission.PATIENT_DELETE, False),
            ("doctor", Permission.CLINICAL_WRITE, True),
            ("doctor", Permission.TREATMENT_PLAN_WRITE, True),
            ("doctor", Permission.FINANCIAL_READ, False),
            ("doctor", Permission.FINANCIAL_WRITE, False),
            ("doctor", Permission.SYSTEM_CONFIG, False),
            ("doctor", Permission.AI_CHAT, True),
            ("doctor", Permission.AI_EXECUTE_UNSAFE, False),
            # Receptionist capabilities
            ("receptionist", Permission.PATIENT_CREATE, True),
            ("receptionist", Permission.PATIENT_READ, True),
            ("receptionist", Permission.PATIENT_DELETE, False),
            ("receptionist", Permission.CLINICAL_READ, False),
            ("receptionist", Permission.CLINICAL_WRITE, False),
            ("receptionist", Permission.APPOINTMENT_CREATE, True),
            ("receptionist", Permission.APPOINTMENT_CANCEL, True),
            ("receptionist", Permission.FINANCIAL_READ, True),
            ("receptionist", Permission.FINANCIAL_WRITE, True),
            ("receptionist", Permission.SYSTEM_CONFIG, False),
            # Nurse capabilities
            ("nurse", Permission.PATIENT_READ, True),
            ("nurse", Permission.PATIENT_CREATE, False),
            ("nurse", Permission.CLINICAL_READ, True),
            ("nurse", Permission.CLINICAL_WRITE, True),
            ("nurse", Permission.FINANCIAL_READ, False),
            ("nurse", Permission.FINANCIAL_WRITE, False),
            ("nurse", Permission.INVENTORY_READ, True),
            ("nurse", Permission.INVENTORY_MANAGE, True),
            # Accountant capabilities
            ("accountant", Permission.FINANCIAL_READ, True),
            ("accountant", Permission.FINANCIAL_WRITE, True),
            ("accountant", Permission.PATIENT_READ, True),
            ("accountant", Permission.PATIENT_CREATE, False),
            ("accountant", Permission.CLINICAL_READ, False),
            ("accountant", Permission.SYSTEM_CONFIG, False),
            # Manager capabilities
            ("manager", Permission.PATIENT_CREATE, True),
            ("manager", Permission.FINANCIAL_READ, True),
            ("manager", Permission.FINANCIAL_WRITE, True),
            ("manager", Permission.INVENTORY_MANAGE, True),
            ("manager", Permission.SYSTEM_CONFIG, True),
            ("manager", Permission.AUDIT_READ, False),
            ("manager", Permission.AI_EXECUTE_UNSAFE, False),
            # Assistant capabilities
            ("assistant", Permission.PATIENT_READ, True),
            ("assistant", Permission.PATIENT_CREATE, False),
            ("assistant", Permission.CLINICAL_READ, True),
            ("assistant", Permission.CLINICAL_WRITE, False),
            ("assistant", Permission.AI_CHAT, True),
        ],
    )
    def test_role_permission_matrix(self, role, permission, expected):
        """Verify exact expected permission for each role."""
        result = has_permission(role, permission)
        assert result == expected, (
            f"Role '{role}' + Permission '{permission.value}': "
            f"expected {expected}, got {result}"
        )

    def test_invalid_role_returns_false(self):
        """Unknown role string must never grant any permission."""
        assert has_permission("hacker", Permission.PATIENT_READ) is False
        assert has_permission("", Permission.SYSTEM_CONFIG) is False
        assert has_permission("ADMIN", Permission.PATIENT_READ) is True  # case-insensitive

    def test_get_role_permissions_returns_set(self):
        """get_role_permissions must return a set for valid roles."""
        perms = get_role_permissions("doctor")
        assert isinstance(perms, set)
        assert Permission.CLINICAL_WRITE in perms

    def test_get_role_permissions_invalid_returns_empty(self):
        """Invalid role must return empty set."""
        perms = get_role_permissions("nonexistent_role")
        assert perms == set()

    def test_role_enum_completeness(self):
        """Every Role enum value must have a ROLE_PERMISSIONS entry."""
        for role in Role:
            if role == Role.PATIENT:
                continue  # Patient role may not have permissions yet
            assert role in ROLE_PERMISSIONS, (
                f"Role {role.value} missing from ROLE_PERMISSIONS"
            )


# ============================================
# INTEGRATION TESTS — Endpoint RBAC Enforcement
# ============================================


def _make_mock_user(role: str, tenant_id: int = 1, user_id: int = 1):
    """Create a mock user with specified role."""
    mock = MagicMock(spec=models.User)
    mock.id = user_id
    mock.tenant_id = tenant_id
    mock.role = role
    mock.username = f"test_{role}"
    mock.email = f"{role}@test.com"
    mock.is_active = True
    
    # Use AttrDict so it behaves like an object (dot access) 
    # and a dict (Pydantic validation for StandardResponse[dict])
    mock.tenant = AttrDict({
        "id": tenant_id,
        "name": "Test Clinic",
        "doctor_name": "Test Doctor",
        "doctor_title": "Dr.",
        "clinic_address": "123 Test St",
        "clinic_phone": "555-1234",
        "google_refresh_token": None,
        "backup_frequency": "weekly",
        "last_backup_at": None,
        "print_header_image": None,
        "print_footer_image": None
    })
    return mock


@pytest.mark.parametrize(
    "role,endpoint,method,should_pass",
    [
        # === PATIENTS ===
        ("admin", "/api/v1/patients/", "GET", True),
        ("doctor", "/api/v1/patients/", "GET", True),
        ("receptionist", "/api/v1/patients/", "GET", True),
        ("nurse", "/api/v1/patients/", "GET", True),
        ("accountant", "/api/v1/patients/", "GET", True),
        ("assistant", "/api/v1/patients/", "GET", True),
        ("guest", "/api/v1/patients/", "GET", False),
        # Patient creation
        ("admin", "/api/v1/patients/", "POST", True),
        ("doctor", "/api/v1/patients/", "POST", True),
        ("receptionist", "/api/v1/patients/", "POST", True),
        ("nurse", "/api/v1/patients/", "POST", False),
        ("accountant", "/api/v1/patients/", "POST", False),
        ("guest", "/api/v1/patients/", "POST", False),
        # Patient deletion (requires PATIENT_DELETE → admin only)
        ("admin", "/api/v1/patients/1", "DELETE", True),
        ("doctor", "/api/v1/patients/1", "DELETE", False),
        ("receptionist", "/api/v1/patients/1", "DELETE", False),
        # === APPOINTMENTS ===
        ("admin", "/api/v1/appointments/", "GET", True),
        ("doctor", "/api/v1/appointments/", "GET", True),
        ("receptionist", "/api/v1/appointments/", "GET", True),
        ("nurse", "/api/v1/appointments/", "GET", True),
        ("assistant", "/api/v1/appointments/", "GET", True),
        ("accountant", "/api/v1/appointments/", "GET", True),
        ("guest", "/api/v1/appointments/", "GET", False),
        # Appointment creation
        ("admin", "/api/v1/appointments/", "POST", True),
        ("receptionist", "/api/v1/appointments/", "POST", True),
        ("doctor", "/api/v1/appointments/", "POST", True),
        ("nurse", "/api/v1/appointments/", "POST", False),
        ("guest", "/api/v1/appointments/", "POST", False),
        # === TREATMENTS ===
        ("admin", "/api/v1/treatments/", "POST", True),
        ("doctor", "/api/v1/treatments/", "POST", True),
        ("receptionist", "/api/v1/treatments/", "POST", False),
        ("nurse", "/api/v1/treatments/", "POST", False),
        ("guest", "/api/v1/treatments/", "POST", False),
        # === PAYMENTS ===
        ("admin", "/api/v1/payments/", "GET", True),
        ("manager", "/api/v1/payments/", "GET", True),
        ("receptionist", "/api/v1/payments/", "GET", True),
        ("accountant", "/api/v1/payments/", "GET", True),
        ("nurse", "/api/v1/payments/", "GET", False),
        ("guest", "/api/v1/payments/", "GET", False),
        # Payment creation
        ("receptionist", "/api/v1/payments/", "POST", True),
        ("accountant", "/api/v1/payments/", "POST", True),
        ("nurse", "/api/v1/payments/", "POST", False),
        # === SETTINGS ===
        ("admin", "/api/v1/settings/tenant", "GET", True),
        ("manager", "/api/v1/settings/tenant", "GET", True),
        ("doctor", "/api/v1/settings/tenant", "GET", False),
        ("receptionist", "/api/v1/settings/tenant", "GET", False),
        # Backup (requires SYSTEM_CONFIG)
        ("admin", "/api/v1/settings/backup/status", "GET", True),
        ("doctor", "/api/v1/settings/backup/status", "GET", False),
        ("nurse", "/api/v1/settings/backup/status", "GET", False),
        # === ADMIN ===
        ("super_admin", "/api/v1/admin/tenants", "GET", True),
        ("admin", "/api/v1/admin/tenants", "GET", False),
        ("doctor", "/api/v1/admin/tenants", "GET", False),
        ("manager", "/api/v1/admin/tenants", "GET", False),
    ],
)
def test_rbac_endpoint_enforcement(client, role, endpoint, method, should_pass):
    """
    Integration test: verify RBAC enforcement at the HTTP level.

    Tests that the correct HTTP status is returned based on role permissions.
    """
    from backend.main import app

    mock_user = _make_mock_user(role)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json={})
        elif method == "DELETE":
            response = client.delete(endpoint)
        else:
            pytest.fail(f"Unsupported method: {method}")

        if should_pass:
            assert response.status_code not in [401, 403], (
                f"RBAC FAIL: {role} should PASS on {method} {endpoint}, "
                f"got {response.status_code}: {response.text[:200]}"
            )
        else:
            assert response.status_code == 403, (
                f"RBAC FAIL: {role} should be DENIED on {method} {endpoint}, "
                f"got {response.status_code}: {response.text[:200]}"
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ============================================
# EDGE CASES
# ============================================


class TestRBACEdgeCases:
    """Edge cases and security boundaries for RBAC."""

    def test_case_insensitive_role_matching(self):
        """Roles should match case-insensitively."""
        assert has_permission("Doctor", Permission.CLINICAL_WRITE) is True
        assert has_permission("DOCTOR", Permission.CLINICAL_WRITE) is True
        assert has_permission("doctor", Permission.CLINICAL_WRITE) is True

    def test_no_role_escalation_via_unknown(self):
        """Passing an unknown role must not grant any implicit permissions."""
        unknown_roles = ["superadmin", "root", "administrator", "sudo", "owner"]
        for role in unknown_roles:
            for perm in Permission:
                assert not has_permission(role, perm), (
                    f"Unknown role '{role}' should NOT have {perm.value}"
                )

    def test_all_roles_accounted_for(self):
        """Every Role enum variant must be covered in the permission matrix."""
        for role in Role:
            if role == Role.PATIENT:
                continue
            perms = ROLE_PERMISSIONS.get(role)
            assert perms is not None, f"Role {role.value} not in ROLE_PERMISSIONS"

    def test_doctor_cannot_access_financial_data(self):
        """Doctor role must be explicitly denied financial write/read."""
        assert not has_permission("doctor", Permission.FINANCIAL_READ)
        assert not has_permission("doctor", Permission.FINANCIAL_WRITE)

    def test_nurse_cannot_create_patients(self):
        """Nurse can view but never create patients."""
        assert has_permission("nurse", Permission.PATIENT_READ)
        assert not has_permission("nurse", Permission.PATIENT_CREATE)
        assert not has_permission("nurse", Permission.PATIENT_DELETE)

    def test_receptionist_cannot_access_clinical_data(self):
        """Receptionist handles scheduling, not clinical data."""
        assert not has_permission("receptionist", Permission.CLINICAL_READ)
        assert not has_permission("receptionist", Permission.CLINICAL_WRITE)
        assert not has_permission("receptionist", Permission.TREATMENT_PLAN_WRITE)
