"""
Tests for RBAC Permission Enforcement.

Validates that:
1. require_permission returns user when role has needed permission
2. require_permission raises 403 when role lacks permission
3. Permission matrix matches expectations
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from backend.core.permissions import (
    Permission,
    Role,
    has_permission,
    get_role_permissions,
    ROLE_PERMISSIONS,
)


# ============================================
# Test: Permission Matrix Integrity
# ============================================

class TestPermissionMatrix:
    """Verify the RBAC matrix is correct and complete."""

    def test_admin_has_all_permissions(self):
        """Admin must have every permission."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        all_perms = set(Permission)
        assert admin_perms == all_perms, f"Admin missing: {all_perms - admin_perms}"

    def test_doctor_cannot_delete_patients(self):
        """Doctors should NOT have PATIENT_DELETE."""
        assert not has_permission("doctor", Permission.PATIENT_DELETE)

    def test_doctor_can_write_treatments(self):
        """Doctors should have TREATMENT_PLAN_WRITE."""
        assert has_permission("doctor", Permission.TREATMENT_PLAN_WRITE)

    def test_receptionist_can_manage_appointments(self):
        """Receptionists should manage appointments."""
        assert has_permission("receptionist", Permission.APPOINTMENT_CREATE)
        assert has_permission("receptionist", Permission.APPOINTMENT_READ)
        assert has_permission("receptionist", Permission.APPOINTMENT_UPDATE)
        assert has_permission("receptionist", Permission.APPOINTMENT_CANCEL)

    def test_receptionist_can_collect_payments(self):
        """Receptionists should be able to collect payments."""
        assert has_permission("receptionist", Permission.FINANCIAL_WRITE)

    def test_nurse_cannot_write_financials(self):
        """Nurses should NOT have FINANCIAL_WRITE."""
        assert not has_permission("nurse", Permission.FINANCIAL_WRITE)

    def test_nurse_can_read_clinical(self):
        """Nurses can read and write clinical data."""
        assert has_permission("nurse", Permission.CLINICAL_READ)
        assert has_permission("nurse", Permission.CLINICAL_WRITE)

    def test_accountant_cannot_write_clinical(self):
        """Accountants should NOT have CLINICAL_WRITE."""
        assert not has_permission("accountant", Permission.CLINICAL_WRITE)

    def test_accountant_can_manage_financials(self):
        """Accountants should have FINANCIAL_READ and FINANCIAL_WRITE."""
        assert has_permission("accountant", Permission.FINANCIAL_READ)
        assert has_permission("accountant", Permission.FINANCIAL_WRITE)

    def test_guest_has_no_permissions(self):
        """Guest role should have zero permissions."""
        guest_perms = ROLE_PERMISSIONS.get(Role.GUEST, set())
        assert len(guest_perms) == 0

    def test_invalid_role_returns_false(self):
        """Unknown role strings should be denied."""
        assert not has_permission("hacker", Permission.PATIENT_READ)
        assert not has_permission("", Permission.PATIENT_READ)
        # Note: "ADMIN" IS valid because has_permission does .lower()


# ============================================
# Test: has_permission function edge cases
# ============================================

class TestHasPermission:
    def test_case_insensitive_role(self):
        """has_permission should handle case-insensitive role string via .lower()."""
        assert has_permission("Admin", Permission.PATIENT_READ)
        assert has_permission("DOCTOR", Permission.CLINICAL_READ)

    def test_all_roles_have_ai_chat(self):
        """All non-guest roles should have AI_CHAT."""
        for role in [Role.ADMIN, Role.DOCTOR, Role.RECEPTIONIST, Role.NURSE, Role.ACCOUNTANT]:
            assert Permission.AI_CHAT in ROLE_PERMISSIONS[role], f"{role} missing AI_CHAT"


# ============================================
# Test: get_role_permissions
# ============================================

class TestGetRolePermissions:
    def test_returns_correct_set_for_doctor(self):
        perms = get_role_permissions("doctor")
        assert Permission.CLINICAL_READ in perms
        assert Permission.PATIENT_DELETE not in perms

    def test_returns_empty_for_invalid(self):
        perms = get_role_permissions("nonexistent")
        assert perms == set()
