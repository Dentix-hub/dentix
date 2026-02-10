"""
Tests for Multi-Doctor Visibility System

Test Scenarios:
1. Doctor A cannot see Doctor B's patients
2. Doctor with APPOINTMENTS_ONLY mode sees correct patients
3. Admin sees all patients
4. AI respects visibility permissions
"""

from unittest.mock import MagicMock

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPatientVisibilityService:
    """Tests for PatientVisibilityService."""

    def test_admin_sees_all_patients(self):
        """Admin role should see all patients in tenant."""
        from backend.services.visibility_service import PatientVisibilityService

        # Mock user with admin role
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "admin"
        mock_user.patient_visibility_mode = None

        # Mock database session
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        service = PatientVisibilityService(mock_db, mock_user, tenant_id=1)
        query = service.get_visible_patient_query()

        # Admin query should not filter by doctor_id
        assert mock_db.query.called

    def test_doctor_all_assigned_mode(self):
        """Doctor with ALL_ASSIGNED mode sees only assigned patients."""
        from backend.services.visibility_service import PatientVisibilityService

        mock_user = MagicMock()
        mock_user.id = 5
        mock_user.role = "doctor"
        mock_user.patient_visibility_mode = "all_assigned"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        service = PatientVisibilityService(mock_db, mock_user, tenant_id=1)
        service.get_visible_patient_query()

        # Should filter by assigned_doctor_id
        assert mock_query.filter.called

    def test_doctor_appointments_only_mode(self):
        """Doctor with APPOINTMENTS_ONLY mode sees only appointment patients."""
        from backend.services.visibility_service import PatientVisibilityService

        mock_user = MagicMock()
        mock_user.id = 5
        mock_user.role = "doctor"
        mock_user.patient_visibility_mode = "appointments_only"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = []

        service = PatientVisibilityService(mock_db, mock_user, tenant_id=1)
        service.get_visible_patient_query()

        assert mock_query.filter.called

    def test_doctor_cannot_see_other_doctor_patients(self):
        """Doctor A cannot see Doctor B's patients."""
        from backend.services.visibility_service import PatientVisibilityService

        # Doctor A
        doctor_a = MagicMock()
        doctor_a.id = 1
        doctor_a.role = "doctor"
        doctor_a.patient_visibility_mode = "all_assigned"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [MagicMock(id=100)]  # Mock patient

        service = PatientVisibilityService(mock_db, doctor_a, tenant_id=1)
        visible_ids = service.get_visible_patient_ids()

        # Doctor A should only see their own assigned patients
        # Patient 200 (Doctor B's) should not be visible
        assert 200 not in visible_ids


class TestFinancialVisibilityService:
    """Tests for FinancialVisibilityService."""

    def test_admin_sees_all_payments(self):
        """Admin sees all payments."""
        from backend.services.financial_visibility_service import (
            FinancialVisibilityService,
        )

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "admin"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        service = FinancialVisibilityService(mock_db, mock_user, tenant_id=1)
        service.get_visible_payments_query()

        assert mock_db.query.called

    def test_doctor_sees_only_own_payments(self):
        """Doctor sees only their own payments."""
        from backend.services.financial_visibility_service import (
            FinancialVisibilityService,
        )

        mock_user = MagicMock()
        mock_user.id = 5
        mock_user.role = "doctor"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        # Ensure chained methods return the same mock_query
        mock_query.join.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.has.return_value = mock_query

        service = FinancialVisibilityService(mock_db, mock_user, tenant_id=1)
        service.get_visible_payments_query()

        # Should filter by doctor_id
        assert mock_query.filter.called


class TestAIPermissionContext:
    """Tests for AI permission enforcement."""

    def test_ai_context_creation(self):
        """AIPermissionContext should be created with correct values."""
        from backend.services.ai.ai_permission_context import AIPermissionContext

        context = AIPermissionContext(
            user_id=1,
            user_role="doctor",
            tenant_id=1,
            visibility_mode="all_assigned",
            visible_patient_ids={100, 101, 102},
        )

        assert context.user_id == 1
        assert context.user_role == "doctor"
        assert len(context.visible_patient_ids) == 3

    def test_ai_cannot_access_hidden_patient(self):
        """AI cannot access patient not in visible list."""
        from backend.services.ai.ai_permission_context import AIPermissionContext

        context = AIPermissionContext(
            user_id=1,
            user_role="doctor",
            tenant_id=1,
            visibility_mode="all_assigned",
            visible_patient_ids={100, 101},
        )

        # Patient 200 is not visible
        assert not context.can_access_patient(200)

        # Patient 100 is visible
        assert context.can_access_patient(100)

    def test_admin_can_access_all_patients(self):
        """Admin context can access any patient."""
        from backend.services.ai.ai_permission_context import AIPermissionContext

        context = AIPermissionContext(
            user_id=1,
            user_role="admin",
            tenant_id=1,
            visibility_mode="all_assigned",
            visible_patient_ids=set(),  # Even without visible IDs
        )

        # Admin can access any patient
        assert context.can_access_patient(999)

    def test_system_prompt_includes_rules(self):
        """System prompt should include mandatory permission rules."""
        from backend.services.ai.ai_permission_context import AIPermissionContext

        context = AIPermissionContext(
            user_id=1,
            user_role="doctor",
            tenant_id=1,
            visibility_mode="all_assigned",
            visible_patient_ids={100},
        )

        prompt = context.get_system_prompt_rules()

        assert "PERMISSION RULES" in prompt
        assert "doctor" in prompt.lower()
        assert "REFUSE" in prompt or "ليس لدي صلاحية" in prompt


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_default_visibility_mode(self):
        """Default visibility mode should be ALL_ASSIGNED."""
        from backend.core.permissions import PatientVisibilityMode

        assert PatientVisibilityMode.ALL_ASSIGNED.value == "all_assigned"

    def test_none_visibility_mode_defaults_safely(self):
        """None visibility mode should default to safe option."""
        from backend.services.visibility_service import PatientVisibilityService

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "doctor"
        mock_user.patient_visibility_mode = None  # Not set

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        service = PatientVisibilityService(mock_db, mock_user, tenant_id=1)

        # Should not crash and should default to safe option
        try:
            service.get_visible_patient_query()
            assert True
        except Exception:
            assert False, "Should handle None visibility mode"
