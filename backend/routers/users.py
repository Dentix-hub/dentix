"""
Users Router
Handles user management within a tenant.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, crud, auth
from .auth import get_db
from .auth.dependencies import validate_password
from ..core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=StandardResponse[List[schemas.User]])
def get_users(
    skip: int = 0,
    limit: int = 100,
    role: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Get users for current tenant (Admin sees all, Staff see doctors)."""
    # Permission.SYSTEM_CONFIG already ensures only Admin/Manager can access this.
    # We will let everyone with SYSTEM_CONFIG see all users.
    query_role = role

    users = crud.get_users(
        db, current_user.tenant_id, skip=skip, limit=limit, role=query_role
    )
    data = [schemas.User.model_validate(u) for u in users]
    return success_response(data=data)


@router.post("/register/", response_model=StandardResponse[schemas.User])
def register_user(
    username: str,
    password: str,
    role: str = "doctor",
    permissions: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Register a new user (admin only)."""
    if crud.get_user(db, username):
        raise HTTPException(status_code=400, detail="Username already registered")

    # --- User Limit Check (Seat-based) ---
    # Get tenant's subscription plan
    tenant = (
        db.query(models.Tenant)
        .filter(models.Tenant.id == current_user.tenant_id)
        .first()
    )
    if tenant and tenant.subscription_plan:
        max_users = tenant.subscription_plan.max_users
        if max_users is not None:  # None means unlimited
            current_user_count = (
                db.query(models.User)
                .filter(models.User.tenant_id == current_user.tenant_id)
                .count()
            )
            if current_user_count >= max_users:
                raise HTTPException(
                    status_code=400,
                    detail=f"لقد وصلت للحد الأقصى من المستخدمين ({max_users}) في خطتك الحالية. يرجى الترقية لإضافة المزيد.",
                )
    # --- End User Limit Check ---

    # Validate password strength reusing central logic
    validate_password(password)

    hashed_password = auth.get_password_hash(password)
    user_in = schemas.User(username=username, role=role)
    if permissions:
        user_in.permissions = permissions

    user = crud.create_user(db, user_in, hashed_password, current_user.tenant_id)
    return success_response(data=user, message="User registered")


@router.put("/{user_id}", response_model=StandardResponse[schemas.User])
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Update a user (admin only)."""
    user = crud.get_user_by_id(db, user_id, current_user.tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user = crud.update_user(db, user_id, user_update, current_user.tenant_id)
    return success_response(data=schemas.User.model_validate(updated_user), message="User updated")


@router.delete("/{user_id}", response_model=StandardResponse[dict])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Delete a user (admin only)."""
    crud.delete_user(db, user_id, current_user.tenant_id)
    return success_response(message="User deleted")

