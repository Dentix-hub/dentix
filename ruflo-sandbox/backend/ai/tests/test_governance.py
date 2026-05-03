import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from backend.ai.policy.execution_policy import policy_engine
from backend.core.config import is_ai_read_only


def test_policy_engine():
    print("Testing Policy Engine...")

    # 1. Check patient registration allowed for doctor
    allowed = policy_engine.check_permission("patient_registration", "doctor")
    print(f"Doctor -> Register Patient: {allowed}")
    assert allowed is True

    # 2. Check patient registration denied for random role
    denied = policy_engine.check_permission("patient_registration", "visitor")
    print(f"Visitor -> Register Patient: {denied}")
    assert denied is False

    # 3. Check General Query allowed for everyone
    public = policy_engine.check_permission("general_query", "visitor")
    print(f"Visitor -> General Query: {public}")
    assert public is True

    # 4. Check Unknown Intent (Default Deny)
    unknown = policy_engine.check_permission("hack_main_frame", "admin")
    print(f"Admin -> Hack Mainframe: {unknown}")
    assert unknown is False


def test_read_only_config():
    print("\nTesting Read Only Config...")

    # Default (False)
    if "AI_READ_ONLY" in os.environ:
        del os.environ["AI_READ_ONLY"]
    assert is_ai_read_only() is False
    print("Default -> False (OK)")

    # Set True
    os.environ["AI_READ_ONLY"] = "true"
    assert is_ai_read_only() is True
    print("Env 'true' -> True (OK)")


if __name__ == "__main__":
    try:
        test_policy_engine()
        test_read_only_config()
        print("\n✅ All Governance Validations Passed")
    except Exception as e:
        print(f"\n❌ Validation Failed: {e}")
        exit(1)
