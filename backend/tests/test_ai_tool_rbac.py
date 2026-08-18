from types import SimpleNamespace

from backend.ai.executor import ToolExecutor


def _executor(role: str):
    user = SimpleNamespace(id=10, role=role, tenant_id=7)
    return ToolExecutor(db=object(), user=user)


def test_doctor_ai_cannot_create_payment_without_financial_write():
    denied = _executor("doctor")._permission_error("create_payment")
    assert denied is not None
    assert denied["error_code"] == "permission_denied"


def test_nurse_ai_cannot_read_expenses_without_financial_read():
    denied = _executor("nurse")._permission_error("get_expenses")
    assert denied is not None
    assert denied["error_code"] == "permission_denied"


def test_receptionist_ai_can_create_payment_per_rbac_matrix():
    assert _executor("receptionist")._permission_error("create_payment") is None


def test_doctor_ai_can_write_clinical_data_per_rbac_matrix():
    assert _executor("doctor")._permission_error("record_medical_note") is None
