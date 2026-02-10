import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from backend.ai.utils.normalization import normalizer
from backend.ai.agent.state_manager import state_manager


def test_normalization():
    print("Testing Arabic Normalization...")
    cases = [
        ("أحمد", "احمد"),
        ("إيمان", "ايمان"),
        ("مدرسة", "مدرسه"),
        ("علي", "علي"),  # No change
        ("منى", "مني"),  # Yeh normalization
        ("مَرْحَبًا", "مرحبا"),  # Tashkeel
    ]

    for input_txt, expected in cases:
        normalized = normalizer.normalize(input_txt)
        print(f"'{input_txt}' -> '{normalized}'")
        assert normalized == expected
    print("✅ Normalization Passed")


def test_state_manager():
    print("\nTesting State Manager...")
    tenant = 1
    user = 101

    # 1. Get empty session
    session = state_manager.get_session(tenant, user)
    assert session.active_patient_id is None
    print("Get Session: OK")

    # 2. Update session
    state_manager.update_session(
        tenant,
        user,
        {"active_patient_name": "Test Patient", "last_intent": "create_patient"},
    )

    # 3. Retrieve and verify
    session2 = state_manager.get_session(tenant, user)
    print(f"Updated Session: {session2.model_dump()}")
    assert session2.active_patient_name == "Test Patient"
    assert session2.last_intent == "create_patient"
    print("✅ State Manager Passed")


if __name__ == "__main__":
    try:
        test_normalization()
        test_state_manager()
        print("\n✅ All Tests Passed")
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        exit(1)
