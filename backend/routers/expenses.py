"""
Expenses Router
Handles expense tracking.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas, crud
from backend.database import get_async_db
from backend.core.permissions import Permission, require_permission
from ..utils.audit_logger import log_admin_action
from backend.core.response import success_response

router = APIRouter(prefix="/expenses", tags=["Expenses"])


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
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get expenses for current tenant with standardized filtering and pagination (§15 MASTER_SPEC, GEMINI_REPAIR_PLAN R5)."""
    # Normalize pagination parameters
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
        current_user.tenant_id,
        skip=effective_skip,
        limit=effective_limit,
        search=search,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    total = await crud.count_expenses(
        db,
        current_user.tenant_id,
        search=search,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    return success_response({
        "items": data,
        "total": total,
        "skip": effective_skip,
        "limit": effective_limit,
    })


@router.post("")
async def create_expense(
    expense: schemas.ExpenseCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
):
    """Create a new expense record."""
    result = await crud.create_expense(db=db, expense=expense, tenant_id=current_user.tenant_id)
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="create",
        entity_type="expense",
        entity_id=result.id if hasattr(result, 'id') else None,
        details=f"Expense: {expense.item_name} - {expense.cost}",
    )
    return success_response(result)


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
):
    """Delete an expense record."""
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="delete",
        entity_type="expense",
        entity_id=expense_id,
        details=f"Deleted expense #{expense_id}",
    )
    data = await crud.delete_expense(db, expense_id, current_user.tenant_id)
    return success_response(data, message="Deleted successfully")


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get financial statistics (expenses vs payments)."""
    # Use the comprehensive stats from crud
    data = await crud.get_financial_stats(db, current_user.tenant_id)
    return success_response(data)
