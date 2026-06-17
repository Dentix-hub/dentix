"""
Expenses Router
Handles expense tracking.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas, crud
from backend.database import get_async_db
from backend.core.permissions import Permission, require_permission
from ..utils.audit_logger import log_admin_action
from backend.core.response import success_response

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("")
async def get_expenses(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get all expenses for current tenant."""
    data = await crud.get_expenses(db, current_user.tenant_id, skip=skip, limit=limit)
    return success_response(data)


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
