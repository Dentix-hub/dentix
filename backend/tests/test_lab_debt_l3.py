"""Tests for Slice L3: Stop the double counting (manual expense guard).

Verifies:
1. POST /api/v1/expenses with category "Laboratory" (case-insensitive, trimmed) is rejected
   with Arabic message "مدفوعات المعامل تتسجل من صفحة المعامل، مش من المصروفات"
2. Variations tested: "Laboratory", "laboratory", "  Laboratory  ", "LABORATORY"
3. PUT /api/v1/expenses/{id} updating category to "Laboratory" is rejected with the same message
4. Other categories ("Supplies", "Utilities", "Rent", "Maintenance", "Salaries", "Other") succeed
5. Pre-existing Expense rows with category="Laboratory" are NOT deleted or broken:
   - Listed in GET /api/v1/expenses
   - Counted in finance summary deductions.expenses
   - Filterable by category="Laboratory"
6. Schema-level validation: ExpenseCreate and ExpenseUpdate reject "Laboratory"
7. ExpenseService create and update paths reject "Laboratory"
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from backend import models, schemas
from backend.main import app
from backend.services.expense_service import ExpenseService
from backend.services.finance_summary_service import FinanceSummaryService


FORBIDDEN_LAB_MESSAGE = "مدفوعات المعامل تتسجل من صفحة المعامل، مش من المصروفات"


@pytest.fixture
def auth_client(admin_user, admin_headers):
    client = TestClient(app)
    client.headers.update(admin_headers)
    return client


# ---------------------------------------------------------------------------
# 1. Schema-level rejection
# ---------------------------------------------------------------------------
def test_expense_create_schema_rejects_laboratory():
    for variant in ["Laboratory", "laboratory", "  Laboratory  ", "LABORATORY", "  laboratory\t"]:
        with pytest.raises(ValueError) as excinfo:
            schemas.ExpenseCreate(
                item_name="Lab Work",
                cost=Decimal("150.00"),
                category=variant,
                date=date(2026, 8, 10),
            )
        assert FORBIDDEN_LAB_MESSAGE in str(excinfo.value)


def test_expense_update_schema_rejects_laboratory():
    for variant in ["Laboratory", "laboratory", "  Laboratory  ", "LABORATORY"]:
        with pytest.raises(ValueError) as excinfo:
            schemas.ExpenseUpdate(category=variant)
        assert FORBIDDEN_LAB_MESSAGE in str(excinfo.value)


# ---------------------------------------------------------------------------
# 2. Endpoint: POST /api/v1/expenses rejects "Laboratory" variants
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("category_variant", [
    "Laboratory",
    "laboratory",
    "  Laboratory  ",
    "LABORATORY",
])
def test_create_expense_endpoint_rejects_laboratory(auth_client, category_variant):
    payload = {
        "item_name": "Zirconia Crown Charge",
        "cost": 350.0,
        "category": category_variant,
        "date": "2026-08-10",
        "notes": "Attempted manual lab expense",
    }
    response = auth_client.post("/api/v1/expenses", json=payload)
    assert response.status_code in (400, 422), f"Expected 400 or 422, got {response.status_code}"
    assert FORBIDDEN_LAB_MESSAGE in response.text


# ---------------------------------------------------------------------------
# 3. Endpoint: PUT /api/v1/expenses/{id} rejects updating to "Laboratory"
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_update_expense_endpoint_rejects_laboratory(async_db_session, admin_user, auth_client):
    tenant_id = admin_user.tenant_id
    expense = models.Expense(
        tenant_id=tenant_id,
        item_name="Cleaning Supplies",
        cost=Decimal("120.00"),
        category="Supplies",
        date=date(2026, 8, 10),
    )
    async_db_session.add(expense)
    await async_db_session.commit()
    await async_db_session.refresh(expense)

    for variant in ["Laboratory", "laboratory", "  Laboratory  "]:
        response = auth_client.put(
            f"/api/v1/expenses/{expense.id}",
            json={"category": variant},
        )
        assert response.status_code in (400, 422), f"Expected 400 or 422 for variant {variant!r}, got {response.status_code}"
        assert FORBIDDEN_LAB_MESSAGE in response.text


# ---------------------------------------------------------------------------
# 4. Other legitimate categories succeed
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("category", [
    "Supplies",
    "Utilities",
    "Rent",
    "Maintenance",
    "Salaries",
    "Other",
])
def test_create_expense_legitimate_categories_succeed(auth_client, category):
    payload = {
        "item_name": f"Regular {category} Expense",
        "cost": 150.0,
        "category": category,
        "date": "2026-08-15",
    }
    response = auth_client.post("/api/v1/expenses", json=payload)
    assert response.status_code == 200, f"Failed for legitimate category {category}: {response.text}"
    data = response.json()["data"]
    assert data["category"] == category
    assert data["cost"] == 150.0


# ---------------------------------------------------------------------------
# 5. Pre-existing Expense rows with category="Laboratory" are untouched & listed
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_legacy_laboratory_expense_rows_are_preserved_and_listed(
    async_db_session, admin_user, auth_client
):
    tenant_id = admin_user.tenant_id
    # Simulate a historical expense recorded under category "Laboratory" before L3
    old_expense = models.Expense(
        tenant_id=tenant_id,
        item_name="Old Historical Lab Expense",
        cost=Decimal("500.00"),
        category="Laboratory",
        date=date(2026, 7, 15),
        notes="Pre-L3 row that must remain untouched",
    )
    async_db_session.add(old_expense)
    await async_db_session.commit()
    await async_db_session.refresh(old_expense)

    # 1. Listed in GET /api/v1/expenses
    res = auth_client.get("/api/v1/expenses?category=Laboratory")
    assert res.status_code == 200
    items = res.json()["data"]["items"]
    assert any(item["id"] == old_expense.id for item in items)
    matched = next(item for item in items if item["id"] == old_expense.id)
    assert matched["category"] == "Laboratory"
    assert matched["cost"] == 500.0

    # 2. Counted in Finance Summary deductions.expenses
    summary_svc = FinanceSummaryService(async_db_session, tenant_id)
    summary = await summary_svc.get_summary(
        start_date="2026-07-01",
        end_date="2026-07-31",
    )
    assert summary["deductions"]["expenses"] >= 500.0


# ---------------------------------------------------------------------------
# 6. Service layer guards (create_expense & update_expense)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_expense_service_guards_reject_laboratory(async_db_session, admin_user):
    tenant_id = admin_user.tenant_id
    service = ExpenseService(async_db_session, tenant_id)

    dummy = schemas.ExpenseCreate(
        item_name="Direct Lab Call",
        cost=Decimal("200.00"),
        category="Supplies",
        date=date(2026, 8, 1),
    )
    object.__setattr__(dummy, "category", "Laboratory")
    with pytest.raises(ValueError) as exc:
        await service.create_expense(dummy)
    assert FORBIDDEN_LAB_MESSAGE in str(exc.value)

    expense = await service.create_expense(
        schemas.ExpenseCreate(
            item_name="Valid Expense",
            cost=Decimal("100.00"),
            category="Supplies",
            date=date(2026, 8, 1),
        )
    )
    dummy_up = schemas.ExpenseUpdate()
    object.__setattr__(dummy_up, "category", "Laboratory")
    with pytest.raises(ValueError) as exc:
        await service.update_expense(expense.id, dummy_up)
    assert FORBIDDEN_LAB_MESSAGE in str(exc.value)
