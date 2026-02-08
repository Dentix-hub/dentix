"""
Users Router
Handles user management within a tenant.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, crud, auth
from .auth import get_current_user, get_db
from ..constants import ROLES

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[schemas.User])
def get_users(
    skip: int = 0,
    limit: int = 100,
    role: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get users for current tenant (Admin sees all, Staff see doctors)."""
    is_admin = current_user.role in ROLES.ADMIN_ROLES
    is_staff = current_user.role in ROLES.STAFF_ROLES
    
    if not is_admin and not is_staff:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Security: Non-admins can ONLY fetch the doctor list
    query_role = role
    if not is_admin:
        query_role = ROLES.DOCTOR
        
    users = crud.get_users(db, current_user.tenant_id, skip=skip, limit=limit, role=query_role)
    return [schemas.User.model_validate(u) for u in users]


@router.post("/register/", response_model=schemas.User)
def register_user(
    username: str,
    password: str,
    role: str = "doctor",
    permissions: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Register a new user (admin only)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if crud.get_user(db, username):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # --- User Limit Check (Seat-based) ---
    # Get tenant's subscription plan
    tenant = db.query(models.Tenant).filter(models.Tenant.id == current_user.tenant_id).first()
    if tenant and tenant.subscription_plan:
        max_users = tenant.subscription_plan.max_users
        if max_users is not None:  # None means unlimited
            current_user_count = db.query(models.User).filter(
                models.User.tenant_id == current_user.tenant_id
            ).count()
            if current_user_count >= max_users:
                raise HTTPException(
                    status_code=400,
                    detail=f"لقد وصلت للحد الأقصى من المستخدمين ({max_users}) في خطتك الحالية. يرجى الترقية لإضافة المزيد."
                )
    # --- End User Limit Check ---
    
    # Validate password strength
    if len(password) < 6 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تحتوي على 6 أحرف على الأقل، مع حرف ورقم")
    
    hashed_password = auth.get_password_hash(password)
    user_in = schemas.User(username=username, role=role)
    if permissions:
        user_in.permissions = permissions
        
    return crud.create_user(
        db, 
        user_in,
        hashed_password, 
        current_user.tenant_id
    )


@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update a user (admin only)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    user = crud.get_user_by_id(db, user_id, current_user.tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    updated_user = crud.update_user(db, user_id, user_update, current_user.tenant_id)
    return schemas.User.model_validate(updated_user)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a user (admin only)."""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud.delete_user(db, user_id, current_user.tenant_id)
