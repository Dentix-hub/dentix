import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.core.permissions import Permission, has_permission
from backend.ai.policy.execution_policy import policy_engine
from backend.services.patient_service import PatientService
from backend.schemas.patient import PatientCreate, PatientUpdate
from backend.models import User


class TestGovernanceRegression(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Patch get_agent to avoid Groq initialization
        self.agent_patcher = patch("backend.services.ai_service.get_agent")
        self.mock_get_agent = self.agent_patcher.start()
        self.mock_agent = MagicMock()
        self.mock_get_agent.return_value = self.mock_agent

    async def asyncTearDown(self):
        self.agent_patcher.stop()

    def test_rbac_definitions(self):
        """Regression: Verify critical role permissions remain intact."""
        # Admin should have everything
        self.assertTrue(has_permission("admin", Permission.PATIENT_DELETE))

        # Doctor should have Clinical + Patient Access
        self.assertTrue(has_permission("doctor", Permission.PATIENT_READ))
        self.assertTrue(has_permission("doctor", Permission.CLINICAL_WRITE))

        # Receptionist should NOT have Clinical Write
        self.assertFalse(has_permission("receptionist", Permission.CLINICAL_WRITE))
        self.assertTrue(has_permission("receptionist", Permission.PATIENT_CREATE))

    def test_policy_engine_integrity(self):
        """Regression: Verify Policy Engine mappings."""
        # Patient Registration -> Requires Patient Create
        policy = policy_engine.get_policy("patient_registration")
        self.assertEqual(policy.required_permission, Permission.PATIENT_CREATE)
        self.assertTrue(policy.requires_confirmation)

        # Financial -> Requires Financial Write
        policy = policy_engine.get_policy("financial_record")
        self.assertEqual(policy.required_permission, Permission.FINANCIAL_WRITE)

    def test_service_layer_rbac_enforcement(self):
        """Regression: Verify PatientService enforces RBAC."""
        service = PatientService(db=MagicMock(), tenant_id=1)

        # 1. Test Create Patient
        # Doctor -> Allowed
        try:
            service.create_patient(
                PatientCreate(name="Test", phone="123", age=30), creator_role="doctor"
            )
        except PermissionError:
            self.fail("Doctor should be allowed to create patient")
        except:
            # Ignore other errors (DB mock)
            pass

        # Guest -> Denied
        with self.assertRaises(PermissionError):
            service.create_patient(
                PatientCreate(name="Test", phone="123", age=30), creator_role="guest"
            )

    async def test_kill_switch_enforcement(self):
        """Regression: Verify AI_GLOBAL_DISABLE blocks execution."""
        from backend.ai.executor import ToolExecutor

        # Setup
        exec = ToolExecutor(db=MagicMock(), user=MagicMock(spec=User))

        # Test ENABLED (Default)
        with patch("backend.core.config.is_ai_disabled", return_value=False):
            # We mock tools.get to return a dummy handler so it doesn't fail on 'unknown tool'
            exec._handlers["patient"] = MagicMock()
            exec._handlers["patient"].search_patients = AsyncMock(
                return_value={"success": True}
            )

            result = await exec.execute("search_patients", {})
            self.assertTrue(result["success"])

        # Test DISABLED
        with patch("backend.core.config.is_ai_disabled", return_value=True):
            result = await exec.execute("search_patients", {})
            self.assertFalse(result["success"])
            self.assertEqual(result["error_code"], "ai_disabled")

    def test_update_patient_rbac(self):
        """Regression: Verify Update Constraints."""
        service = PatientService(db=MagicMock(), tenant_id=1)

        # Receptionist trying to update notes (Sensitive) -> Should Fail?
        # Current Policy: update_patient allowed tools -> update_patient_record
        # PolicyRule says: allowed_fields=["phone", "age", "address", "notes"]
        # But required_permission is PATIENT_UPDATE.
        # Receptionist HAS PATIENT_UPDATE.
        # Wait, does Receptionist have PATIENT_UPDATE?
        # permissions.py: Role.RECEPTIONIST: {..., PATIENT_UPDATE, ...}
        # So Receptionist CAN update.

        # However, Policy Rule allows "notes".
        # Ideally, we should restrict "clinical_notes" vs "admin_notes".
        # Currently the system assumes "notes" are general.

        # Let's check a role WITHOUT update, e.g. Nurse (Permissions: READ ONLY for Patient?)
        # Role.NURSE: {PATIENT_READ, ...} NO PATIENT_UPDATE.

        with self.assertRaises(PermissionError):
            service.update_patient(
                patient_id=1,
                updates=PatientUpdate(name="New Name"),
                updater_role="nurse",
            )

    async def test_audit_log_persistence(self):
        """Regression: Verify Audit Log is created."""
        from backend.services.ai_service import AIService
        from backend.models.ai_audit import AIAuditLog

        # Setup
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.tenant_id = 1
        mock_user.tenant.subscription_plan.is_ai_enabled = True

        service = AIService(db=mock_db, user=mock_user)
        # Mock dependencies to reach log step
        service._check_subscription_quota = MagicMock(return_value=None)
        service._detect_confirmation = AsyncMock(return_value=None)
        service._detect_intent = MagicMock(return_value=None)
        service.executor = AsyncMock()
        service.agent = AsyncMock()
        service.agent.process = AsyncMock(
            return_value={"tool": "response", "message": "Hi", "success": True}
        )

        # Act
        await service.process_query("Hello")

        # Assert
        # Check that db.add was called with AIAuditLog instance
        calls = mock_db.add.call_args_list
        audit_log_verified = False
        for call in calls:
            arg = call[0][0]
            if isinstance(arg, AIAuditLog):
                audit_log_verified = True
                self.assertEqual(arg.intent, "response")
                self.assertEqual(arg.status, "SUCCESS")

        self.assertTrue(audit_log_verified, "AIAuditLog was not persisted.")

    def test_security_event_model(self):
        """Regression: Verify SecurityEvent model structure."""
        from backend.models.security_event import SecurityEvent

        event = SecurityEvent(
            event_type="AUTH_FAILURE",
            severity="HIGH",
            description="Failed login",
            details='{"ip": "1.1.1.1"}',
        )
        self.assertEqual(event.event_type, "AUTH_FAILURE")
        self.assertEqual(event.severity, "HIGH")


if __name__ == "__main__":
    unittest.main()
