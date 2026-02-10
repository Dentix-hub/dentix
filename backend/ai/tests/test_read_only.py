import sys
import os
import asyncio
import pytest  # Add missing import
from unittest.mock import MagicMock
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from backend.ai.executor import ToolExecutor
from backend.core.config import is_ai_read_only


@pytest.mark.asyncio
async def test_read_only_enforcement():
    print("Testing AI Read-Only Enforcement...")

    # 1. Enable Read-Only Mode
    os.environ["AI_READ_ONLY"] = "true"
    print(f"AI_READ_ONLY Flag is: {is_ai_read_only()}")

    # Mock Dependencies
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.tenant_id = 1

    executor = ToolExecutor(mock_db, mock_user)

    # 2. Test Safe Tool (e.g. search_patients)
    # We mock the handler execution to avoid real DB calls
    executor.patient.search_patients = MagicMock()
    executor.patient.search_patients.return_value = {
        "success": True,
        "message": "Mock Search",
    }

    # NOTE: The executor calls the handler, but the check happens BEFORE calling handler.
    # So we just need to see if it RETURNS error blindly.

    print("\n--- Test 1: Safe Tool (search_patients) ---")
    result_safe = await executor.execute("search_patients", {"q": "Ahmed"})
    print(f"Result: {result_safe}")

    if result_safe.get("error_code") == "read_only_mode":
        print("❌ FAILED: Safe tool was blocked!")
    else:
        print("✅ PASSED: Safe tool allowed.")

    # 3. Test Unsafe Tool (e.g. create_patient)
    print("\n--- Test 2: Unsafe Tool (create_patient) ---")
    result_unsafe = await executor.execute("create_patient", {"name": "Test"})
    print(f"Result: {result_unsafe}")

    if result_unsafe.get("error_code") == "read_only_mode":
        print("✅ PASSED: Unsafe tool blocked correctly.")
    else:
        print("❌ FAILED: Unsafe tool was allowed!")

    # Cleanup
    del os.environ["AI_READ_ONLY"]


if __name__ == "__main__":
    asyncio.run(test_read_only_enforcement())
