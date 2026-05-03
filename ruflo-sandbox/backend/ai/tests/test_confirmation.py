import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.ai_service import AIService
from backend.ai.agent.state_manager import state_manager
from backend.ai.policy.execution_policy import policy_engine


class TestConfirmationLayer(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_db = MagicMock()
        self.mock_user = MagicMock()
        self.mock_user.id = 999
        self.mock_user.tenant_id = 1
        self.mock_user.tenant.id = 1  # CRITICAL FIX for state_manager key
        self.mock_user.tenant.subscription_plan.is_ai_enabled = True
        self.mock_user.tenant.subscription_plan.ai_daily_limit = 100

        # Reset state manager
        state_manager._sessions = {}

        # Patch get_agent
        self.agent_patcher = patch("backend.services.ai_service.get_agent")
        self.mock_get_agent = self.agent_patcher.start()
        self.mock_agent = MagicMock()
        self.mock_get_agent.return_value = self.mock_agent

        # Service under test
        self.service = AIService(self.mock_db, self.mock_user)
        self.service.executor = AsyncMock()  # Mock the executor

    async def asyncTearDown(self):
        self.agent_patcher.stop()

    def test_policy_flag(self):
        """Verify policy correctly flags sensitive tools."""
        self.assertTrue(policy_engine.check_requires_confirmation("create_patient"))
        self.assertTrue(policy_engine.check_requires_confirmation("create_appointment"))
        self.assertFalse(policy_engine.check_requires_confirmation("response"))

    async def test_detect_confirmation_yes(self):
        """Verify 'Yes' triggers pending tool execution."""
        # 1. Setup Session with Pending Action
        state_manager.update_session(
            1,
            999,
            {
                "pending_confirmation": {
                    "tool": "create_patient",
                    "params": {"name": "Test Patient"},
                }
            },
        )

        # 2. Mock Executor Result
        self.service.executor.execute.return_value = {
            "success": True,
            "message": "Patient Created",
            "data": {"id": 1},
        }

        # 3. Process Confirmation
        response = await self.service._detect_confirmation("Yes, confirm please", [])

        # 4. Assertions
        self.assertIsNotNone(response)
        self.assertTrue(response.success)
        self.assertEqual(response.tool, "create_patient")
        self.service.executor.execute.assert_called_with(
            "create_patient", {"name": "Test Patient"}
        )

        # 5. Verify Pending Cleared
        session = state_manager.get_session(1, 999)
        self.assertIsNone(session.pending_confirmation)

    async def test_detect_confirmation_no(self):
        """Verify 'No' clears pending action without execution."""
        # 1. Setup Session
        state_manager.update_session(
            1,
            999,
            {
                "pending_confirmation": {
                    "tool": "create_patient",
                    "params": {"name": "Test Patient"},
                }
            },
        )

        # 2. Process Rejection
        response = await self.service._detect_confirmation("No, cancel it", [])

        # 3. Assertions
        self.assertIsNotNone(response)
        self.assertTrue(response.success)
        self.assertIn("تم إلغاء", response.message)
        self.service.executor.execute.assert_not_called()

        # 4. Verify Pending Cleared
        session = state_manager.get_session(1, 999)
        self.assertIsNone(session.pending_confirmation)

    async def test_detect_no_pending(self):
        """Verify nothing happens if no pending confirmation."""
        response = await self.service._detect_confirmation("Yes", [])
        self.assertIsNone(response)


if __name__ == "__main__":
    unittest.main()
