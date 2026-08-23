"""Expenses Router — tenant-scoped manual expense tracking."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, schemas
from ..utils.audit_logger import log_admin_action
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response
from backend.core.tenant_context import require_tenant_id
from backend.database import get_async_db
from backend.services.expense_service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def _manual_expense_payload(expense) -> dict:
    """Serialize an Expense with explicit source/provenance metadata.

    Finance Summary treats this table strictly as manual operating expenses;
    laboratory and payroll costs come from their own authoritative sources.
    """
    return {
        "id": expense.id,
        "item_name": expense.item_name,
        "cost": expense.cost,
        "category": expense.category,
        "date": expense.date,
        "notes": expense.notes,
        "source": "manual_expense",
        "provenance": {
            "kind": "manual_expense",
            "source_table": "expenses",
            "source_id": expense.id,
        },
    }


@router.get("")
async def get_expenses(
    search: Optional[str] = Query(None, description="Search by expense item name or notes"),
    category: Optional[str] = Query(None, description="Filter by category"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    offset: Optional[int] = Query(None, ge=0),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.EXPENSE_READ)),
):
    tenant_id = require_tenant_id(current_user)
    effective_skip = skip
    effective_limit = min(limit, 200)
    if offset is not None:
        effective_skip = offset
    if page is not None:
        size = page_size if page_size is not None else effective_limit
        effective_limit = min(size, 200)
        effective_skip = (page - 1) * effective_limit

    data = await crud.get_expenses(
        db,
        tenant_id,
        skip=effective_skip,
        limit=effective_limit,
        search=search,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    total = await crud.count_expenses(
        db,
        tenant_id,
        search=search,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    return success_response(
        {
            "items": [_manual_expense_payload(expense) for expense in data],
            "total": total,
            "skip": effective_skip,
            "limit": effective_limit,
            "source": "manual_expense",
            "provenance": {
                "kind": "manual_expense_collection",
                "source_table": "expenses",
            },
        }
    )


@router.post("")
async def create_expense(
    expense: schemas.ExpenseCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.EXPENSE_MANAGE)),
):
    tenant_id = require_tenant_id(current_user)
    service = ExpenseService(db, tenant_id)
    try:
        result = await service.create_expense(expense, commit=False)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="create",
        entity_type="expense",
        entity_id=result.id if hasattr(result, "id") else None,
        details=f"Expense: {expense.item_name} - {expense.cost}",
    )
    await db.commit()
    await db.refresh(result)
    return success_response(_manual_expense_payload(result))


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.EXPENSE_MANAGE)),
):
    tenant_id = require_tenant_id(current_user)

    from backend import models
    from sqlalchemy import select

    existing = (
        await db.execute(
            select(models.Expense).where(
                models.Expense.id == expense_id,
                models.Expense.tenant_id == tenant_id,
            )
        )
    ).scalars().first()
    if not existing:
        raise HTTPException(status_code=404, detail="Expense not found")

    log_admin_action(
        db=db,
        admin_user=current_user,
        action="delete",
        entity_type="expense",
        entity_id=expense_id,
        details=f"Deleted expense #{expense_id}",
    )
    data = await crud.delete_expense(db, expense_id, tenant_id)
    return success_response(data, message="Deleted successfully")


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.EXPENSE_READ)),
):
    tenant_id = require_tenant_id(current_user)
    data = await crud.get_financial_stats(db, tenant_id)
    return success_response(data)
