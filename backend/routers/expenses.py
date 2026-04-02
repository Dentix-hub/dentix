"""
Expenses Router
Handles expense tracking.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .. import schemas, crud
from .auth import get_current_user, get_db
from backend.core.permissions import Permission, require_permission
from ..utils.audit_logger import log_admin_action

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("/", response_model=List[schemas.Expense])
def get_expenses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get all expenses for current tenant."""
    return crud.get_expenses(db, current_user.tenant_id, skip=skip, limit=limit)


@router.post("/", response_model=schemas.Expense)
def create_expense(
    expense: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.FINANCIAL_WRITE)),
):
    """Create a new expense record."""
    result = crud.create_expense(db=db, expense=expense, tenant_id=current_user.tenant_id)
    log_admin_action(
        db=db,
        admin_user=current_user,
        action="create",
        entity_type="expense",
        entity_id=result.id if hasattr(result, 'id') else None,
        details=f"Expense: {expense.description} - {expense.amount}",
    )
    return result


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
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
    return crud.delete_expense(db, expense_id, current_user.tenant_id)


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get financial statistics (expenses vs payments)."""
    # Use the comprehensive stats from crud
    return crud.get_financial_stats(db, current_user.tenant_id)
