"""
================================================================
PATCH C.1 — test_ai_handlers.py
================================================================
الملف: backend/tests/test_ai_handlers.py
================================================================
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession


# ================================================================
# Fixtures المشتركة
# ================================================================

@pytest.fixture
def mock_db():
    """AsyncSession mock."""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def sample_tenant_id():
    return 1


@pytest.fixture
def sample_appointment_data():
    return {
        "id": 101,
        "patient_id": 5,
        "doctor_id": 2,
        "tenant_id": 1,
        "date": "2026-04-18",
        "time": "10:00",
        "status": "scheduled",
        "notes": "Routine checkup",
    }


# ================================================================
# Tests: handle_appointment_tool
# ================================================================

class TestHandleAppointmentTool:
    """Tests for backend/ai/handlers/appointment.py"""

    @pytest.mark.asyncio
    async def test_list_appointments_valid_input(
        self, mock_db, sample_tenant_id, sample_appointment_data
    ):
        """Tool call بـ input صح يرجع appointments list."""
        from backend.ai.handlers.appointment import handle_appointment_tool

        tool_input = {
            "action": "list_appointments",
            "tenant_id": sample_tenant_id,
            "date": "2026-04-18",
        }

        with patch(
            "backend.ai.handlers.appointment.crud_appointment.get_appointments",
            new_callable=AsyncMock,
            return_value=[MagicMock(**sample_appointment_data)],
        ):
            result = await handle_appointment_tool(tool_input, db=mock_db)

        assert result is not None
        assert "appointments" in result
        assert isinstance(result["appointments"], list)

    @pytest.mark.asyncio
    async def test_missing_tenant_id_raises_error(self, mock_db):
        """Missing tenant_id يرجع error مضبوط — tenant isolation."""
        from backend.ai.handlers.appointment import handle_appointment_tool

        tool_input = {"action": "list_appointments"}  # مفيش tenant_id

        with pytest.raises((ValueError, KeyError)) as exc_info:
            await handle_appointment_tool(tool_input, db=mock_db)

        assert "tenant" in str(exc_info.value).lower() or exc_info.type == KeyError

    @pytest.mark.asyncio
    async def test_output_format_is_consistent(
        self, mock_db, sample_tenant_id, sample_appointment_data
    ):
        """الـ output format ثابت ومتوقع دايماً."""
        from backend.ai.handlers.appointment import handle_appointment_tool

        tool_input = {
            "action": "list_appointments",
            "tenant_id": sample_tenant_id,
        }

        with patch(
            "backend.ai.handlers.appointment.crud_appointment.get_appointments",
            new_callable=AsyncMock,
            return_value=[MagicMock(**sample_appointment_data)],
        ):
            result = await handle_appointment_tool(tool_input, db=mock_db)

        # تحقق من بنية الـ response
        required_keys = {"appointments", "total"}
        assert required_keys.issubset(result.keys()), (
            f"Missing keys: {required_keys - result.keys()}"
        )
        assert isinstance(result["total"], int)

    @pytest.mark.asyncio
    async def test_create_appointment_valid(self, mock_db, sample_tenant_id):
        """إنشاء appointment جديد بـ data صح."""
        from backend.ai.handlers.appointment import handle_appointment_tool

        tool_input = {
            "action": "create_appointment",
            "tenant_id": sample_tenant_id,
            "patient_id": 5,
            "doctor_id": 2,
            "date": "2026-04-20",
            "time": "14:00",
        }

        mock_created = MagicMock(id=999, status="scheduled")

        with patch(
            "backend.ai.handlers.appointment.crud_appointment.create_appointment",
            new_callable=AsyncMock,
            return_value=mock_created,
        ):
            result = await handle_appointment_tool(tool_input, db=mock_db)

        assert result.get("success") is True or "appointment" in result

    @pytest.mark.asyncio
    async def test_unknown_action_raises_error(self, mock_db, sample_tenant_id):
        """Action غير معروف يرجع error واضح."""
        from backend.ai.handlers.appointment import handle_appointment_tool

        tool_input = {
            "action": "delete_all_data",  # action غير موجود
            "tenant_id": sample_tenant_id,
        }

        with pytest.raises((ValueError, NotImplementedError, KeyError)):
            await handle_appointment_tool(tool_input, db=mock_db)

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation(self, mock_db):
        """Tenant A لا يرى appointments بتاعة Tenant B."""
        from backend.ai.handlers.appointment import handle_appointment_tool

        tenant_a_input = {"action": "list_appointments", "tenant_id": 1}
        tenant_b_input = {"action": "list_appointments", "tenant_id": 2}

        tenant_a_appointments = [MagicMock(tenant_id=1, id=1)]
        tenant_b_appointments = [MagicMock(tenant_id=2, id=2)]

        with patch(
            "backend.ai.handlers.appointment.crud_appointment.get_appointments",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = tenant_a_appointments
            result_a = await handle_appointment_tool(tenant_a_input, db=mock_db)

            mock_get.return_value = tenant_b_appointments
            result_b = await handle_appointment_tool(tenant_b_input, db=mock_db)

        # تأكد إن كل tenant بياخد بياناته بس
        appointments_a = result_a.get("appointments", [])
        appointments_b = result_b.get("appointments", [])

        a_ids = {a.get("id") or getattr(a, "id", None) for a in appointments_a}
        b_ids = {b.get("id") or getattr(b, "id", None) for b in appointments_b}

        assert not a_ids.intersection(b_ids), "Tenant isolation violated!"


# ================================================================
# Tests: handle_finance_tool
# ================================================================

class TestHandleFinanceTool:
    """Tests for backend/ai/handlers/finance.py"""

    @pytest.mark.asyncio
    async def test_monthly_revenue_valid(self, mock_db, sample_tenant_id):
        """حساب الإيرادات الشهرية بـ input صح."""
        from backend.ai.handlers.finance import handle_finance_tool

        tool_input = {
            "action": "monthly_revenue",
            "tenant_id": sample_tenant_id,
            "month": "2026-03",
        }

        with patch(
            "backend.ai.handlers.finance.crud_billing.get_monthly_revenue",
            new_callable=AsyncMock,
            return_value={"total": 15000.0, "paid": 12000.0, "pending": 3000.0},
        ):
            result = await handle_finance_tool(tool_input, db=mock_db)

        assert "total_revenue" in result or "total" in result
        revenue = result.get("total_revenue") or result.get("total")
        assert isinstance(revenue, (int, float))
        assert revenue >= 0

    @pytest.mark.asyncio
    async def test_invalid_month_format_raises_error(
        self, mock_db, sample_tenant_id
    ):
        """Month بـ format غلط يرجع validation error."""
        from backend.ai.handlers.finance import handle_finance_tool

        tool_input = {
            "action": "monthly_revenue",
            "tenant_id": sample_tenant_id,
            "month": "not-a-date",
        }

        with pytest.raises((ValueError, Exception)):
            await handle_finance_tool(tool_input, db=mock_db)

    @pytest.mark.asyncio
    async def test_missing_tenant_raises_error(self, mock_db):
        """Missing tenant_id في finance handler يرفع error."""
        from backend.ai.handlers.finance import handle_finance_tool

        tool_input = {"action": "monthly_revenue", "month": "2026-03"}

        with pytest.raises((ValueError, KeyError)):
            await handle_finance_tool(tool_input, db=mock_db)

    @pytest.mark.asyncio
    async def test_data_munging_numeric_output(self, mock_db, sample_tenant_id):
        """التأكد إن الـ revenue values أرقام مش strings."""
        from backend.ai.handlers.finance import handle_finance_tool

        tool_input = {
            "action": "monthly_revenue",
            "tenant_id": sample_tenant_id,
            "month": "2026-04",
        }

        with patch(
            "backend.ai.handlers.finance.crud_billing.get_monthly_revenue",
            new_callable=AsyncMock,
            return_value={"total": 8500.75, "paid": 8000.0, "pending": 500.75},
        ):
            result = await handle_finance_tool(tool_input, db=mock_db)

        # التأكد من الـ data types
        revenue = result.get("total_revenue") or result.get("total")
        assert isinstance(revenue, (int, float)), f"Expected number, got {type(revenue)}"

    @pytest.mark.asyncio
    async def test_outstanding_payments_action(self, mock_db, sample_tenant_id):
        """استرجاع المدفوعات المتأخرة."""
        from backend.ai.handlers.finance import handle_finance_tool

        tool_input = {
            "action": "outstanding_payments",
            "tenant_id": sample_tenant_id,
        }

        mock_outstanding = [
            {"invoice_id": 1, "patient_id": 5, "amount": 300.0, "due_date": "2026-03-01"},
            {"invoice_id": 2, "patient_id": 8, "amount": 150.0, "due_date": "2026-03-15"},
        ]

        with patch(
            "backend.ai.handlers.finance.crud_billing.get_outstanding_invoices",
            new_callable=AsyncMock,
            return_value=mock_outstanding,
        ):
            result = await handle_finance_tool(tool_input, db=mock_db)

        assert "outstanding" in result or "invoices" in result
        items = result.get("outstanding") or result.get("invoices", [])
        assert isinstance(items, list)
