import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Fix Arabic UnicodeEncodeError on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from backend.ai.utils.error_explainer import error_explainer
from backend.routers.ai_assist import ai_autocomplete
from backend.ai.agent.state_manager import state_manager


def test_error_explainer():
    print("Testing Error Explainer...")

    # 1. Quota
    err1 = "QuotaExceededError: Limit reached"
    msg1 = error_explainer.explain(err1)
    print(f"Error: {err1} -> Explained: {msg1}")
    assert "استنفدت الحد" in msg1

    # 2. Connection
    err2 = "requests.exceptions.ConnectTimeout"
    msg2 = error_explainer.explain(err2)
    print(f"Error: {err2} -> Explained: {msg2}")
    assert "مشكلة في الاتصال" in msg2

    print("✅ Error Explainer Passed")


def test_autocomplete_logic():
    print("\nTesting Autocomplete Logic (Mocked)...")

    # Mock dependencies
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 101
    tenant_id = 1

    # Mock session
    state_manager.update_session(
        tenant_id,
        mock_user.id,
        {"active_patient_id": 50, "active_patient_name": "Test Patient"},
    )

    # Mock DB query result
    mock_patient = MagicMock()
    mock_patient.id = 1
    mock_patient.name = "Ahmed Ali"
    mock_patient.phone = "0123456789"

    mock_query = MagicMock()
    mock_query.filter.return_value.limit.return_value.all.return_value = [mock_patient]
    mock_db.query.return_value = mock_query

    # Call function
    results = ai_autocomplete(
        q="Ah", context="test", db=mock_db, current_user=mock_user, tenant_id=tenant_id
    )

    print(f"Autocomplete Result: {results}")

    # Verify Suggestions (from State)
    assert len(results["suggestions"]) > 0
    assert "Test Patient" in results["suggestions"][0]["text"]

    # Verify Patients (from DB Mock)
    assert len(results["patients"]) == 1
    assert results["patients"][0]["name"] == "Ahmed Ali"

    print("✅ Autocomplete Passed")


if __name__ == "__main__":
    try:
        test_error_explainer()
        test_autocomplete_logic()
        print("\n✅ All Tests Passed")
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        exit(1)
