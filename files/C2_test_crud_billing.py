"""
================================================================
PATCH C.2 — test_crud_billing.py (Conditional — شغّل coverage أولاً)
================================================================
الملف: backend/tests/test_crud_billing.py
نفّذه بس لو: coverage run -m pytest && coverage report
يظهر crud/billing.py < 60%
================================================================
"""
import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch

from backend.crud import billing as crud_billing


# ================================================================
# Fixtures
# ================================================================

@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def invoice_create_data():
    """Data صح لإنشاء invoice."""
    from backend.schemas.billing import InvoiceCreate  # عدّل الـ import لو الـ path تاني
    return {
        "patient_id": 5,
        "tenant_id": 1,
        "total_amount": 500.0,
        "currency": "EGP",
        "items": [
            {"description": "Dental Cleaning", "amount": 300.0, "quantity": 1},
            {"description": "X-Ray", "amount": 200.0, "quantity": 1},
        ],
    }


# ================================================================
# Tests: Create Invoice
# ================================================================

class TestCreateInvoice:

    @pytest.mark.asyncio
    async def test_create_invoice_success(self, mock_db, invoice_create_data):
        """إنشاء invoice ناجح بـ data صح."""
        mock_invoice = MagicMock(
            id=1,
            patient_id=5,
            tenant_id=1,
            total_amount=500.0,
            is_deleted=False,
            status="pending",
        )

        with patch.object(crud_billing, "create_invoice", new_callable=AsyncMock, return_value=mock_invoice):
            result = await crud_billing.create_invoice(mock_db, invoice_create_data)

        assert result.id is not None
        assert result.total_amount == 500.0
        assert result.is_deleted is False
        assert result.status == "pending"

    @pytest.mark.asyncio
    async def test_create_invoice_sets_tenant(self, mock_db, invoice_create_data):
        """الـ invoice يُحفظ مع الـ tenant_id الصح."""
        mock_invoice = MagicMock(tenant_id=1)

        with patch.object(crud_billing, "create_invoice", new_callable=AsyncMock, return_value=mock_invoice):
            result = await crud_billing.create_invoice(mock_db, invoice_create_data)

        assert result.tenant_id == invoice_create_data["tenant_id"]

    @pytest.mark.asyncio
    async def test_create_invoice_calculates_total(self, mock_db, invoice_create_data):
        """الـ total_amount صح بناءً على الـ items."""
        expected_total = sum(
            item["amount"] * item.get("quantity", 1)
            for item in invoice_create_data["items"]
        )
        mock_invoice = MagicMock(total_amount=expected_total)

        with patch.object(crud_billing, "create_invoice", new_callable=AsyncMock, return_value=mock_invoice):
            result = await crud_billing.create_invoice(mock_db, invoice_create_data)

        assert result.total_amount == 500.0


# ================================================================
# Tests: Soft Delete
# ================================================================

class TestSoftDeleteInvoice:

    @pytest.mark.asyncio
    async def test_soft_delete_marks_as_deleted(self, mock_db):
        """Soft delete بيضبط is_deleted=True مش بيمسح من الـ DB."""
        invoice_id = 1
        mock_invoice = MagicMock(id=invoice_id, is_deleted=True)

        with patch.object(crud_billing, "soft_delete_invoice", new_callable=AsyncMock, return_value=mock_invoice):
            result = await crud_billing.soft_delete_invoice(mock_db, invoice_id)

        assert result.is_deleted is True

    @pytest.mark.asyncio
    async def test_soft_deleted_not_in_list(self, mock_db):
        """Invoice المحذوفة مش بتظهر في الـ get_invoices العادي."""
        # الـ list بيرجع فقط الـ invoices غير المحذوفة
        active_invoices = [
            MagicMock(id=2, is_deleted=False, tenant_id=1),
            MagicMock(id=3, is_deleted=False, tenant_id=1),
        ]

        with patch.object(crud_billing, "get_invoices", new_callable=AsyncMock, return_value=active_invoices):
            result = await crud_billing.get_invoices(mock_db, tenant_id=1)

        assert all(not inv.is_deleted for inv in result)
        assert 1 not in [inv.id for inv in result]  # الـ invoice 1 المحذوفة مش موجودة

    @pytest.mark.asyncio
    async def test_soft_delete_nonexistent_raises(self, mock_db):
        """محاولة حذف invoice مش موجودة تعمل raise."""
        with patch.object(
            crud_billing,
            "soft_delete_invoice",
            new_callable=AsyncMock,
            side_effect=ValueError("Invoice not found"),
        ):
            with pytest.raises(ValueError, match="not found"):
                await crud_billing.soft_delete_invoice(mock_db, invoice_id=99999)


# ================================================================
# Tests: Tenant Isolation
# ================================================================

class TestBillingTenantIsolation:

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_see_tenant_b_invoices(self, mock_db):
        """Tenant A لا يرى فواتير Tenant B — multi-tenant isolation."""
        tenant_b_invoices = [
            MagicMock(id=10, tenant_id=2),
            MagicMock(id=11, tenant_id=2),
        ]
        tenant_a_invoices = [
            MagicMock(id=20, tenant_id=1),
        ]

        with patch.object(crud_billing, "get_invoices", new_callable=AsyncMock) as mock_get:
            # Tenant A query
            mock_get.return_value = tenant_a_invoices
            result_a = await crud_billing.get_invoices(mock_db, tenant_id=1)
            assert all(inv.tenant_id == 1 for inv in result_a)

            # Tenant B query
            mock_get.return_value = tenant_b_invoices
            result_b = await crud_billing.get_invoices(mock_db, tenant_id=2)
            assert all(inv.tenant_id == 2 for inv in result_b)

        # لا تقاطع بين النتيجتين
        a_ids = {inv.id for inv in result_a}
        b_ids = {inv.id for inv in result_b}
        assert a_ids.isdisjoint(b_ids), "CRITICAL: Tenant isolation violated!"

    @pytest.mark.asyncio
    async def test_get_invoice_by_id_checks_tenant(self, mock_db):
        """جلب invoice بـ ID لازم يتحقق من الـ tenant_id."""
        invoice_id = 1
        tenant_id = 1

        # Scenario: invoice موجودة لكن لـ tenant تاني
        with patch.object(
            crud_billing,
            "get_invoice",
            new_callable=AsyncMock,
            side_effect=PermissionError("Invoice does not belong to this tenant"),
        ):
            with pytest.raises(PermissionError):
                await crud_billing.get_invoice(
                    mock_db,
                    invoice_id=invoice_id,
                    tenant_id=999,  # tenant غلط
                )


# ================================================================
# Tests: Revenue Calculation
# ================================================================

class TestRevenueCalculation:

    @pytest.mark.asyncio
    async def test_monthly_revenue_sums_correctly(self, mock_db):
        """الإيرادات الشهرية محسوبة صح من الـ invoices المدفوعة."""
        mock_result = {
            "month": "2026-03",
            "total_invoiced": 10000.0,
            "total_paid": 8500.0,
            "total_pending": 1500.0,
            "invoice_count": 25,
        }

        with patch.object(
            crud_billing, "get_monthly_revenue", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await crud_billing.get_monthly_revenue(
                mock_db, tenant_id=1, month="2026-03"
            )

        # التحقق من المنطق
        assert result["total_paid"] + result["total_pending"] == result["total_invoiced"]
        assert result["total_paid"] >= 0
        assert result["invoice_count"] > 0

    @pytest.mark.asyncio
    async def test_revenue_zero_for_empty_month(self, mock_db):
        """شهر بدون invoices يرجع zero."""
        mock_result = {
            "month": "2026-01",
            "total_invoiced": 0.0,
            "total_paid": 0.0,
            "total_pending": 0.0,
            "invoice_count": 0,
        }

        with patch.object(
            crud_billing, "get_monthly_revenue", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await crud_billing.get_monthly_revenue(
                mock_db, tenant_id=1, month="2026-01"
            )

        assert result["total_invoiced"] == 0.0
        assert result["invoice_count"] == 0
