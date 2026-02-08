"""
Expenses Router
Handles expense tracking.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .. import schemas, crud
from ..models import Expense, Payment, Patient
from sqlalchemy import func
from .auth import get_current_user, get_db

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("/", response_model=List[schemas.Expense])
def get_expenses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get all expenses for current tenant."""
    return crud.get_expenses(db, current_user.tenant_id, skip=skip, limit=limit)


@router.post("/", response_model=schemas.Expense)
def create_expense(
    expense: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Create a new expense record."""
    return crud.create_expense(db=db, expense=expense, tenant_id=current_user.tenant_id)


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Delete an expense record."""
    return crud.delete_expense(db, expense_id, current_user.tenant_id)


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """Get financial statistics (expenses vs payments)."""
    # Use the comprehensive stats from crud
    return crud.get_financial_stats(db, current_user.tenant_id)
