"""
Users Router
Handles user management within a tenant.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from .. import models, schemas, crud, auth
from backend.database import get_async_db
from .auth.dependencies import validate_password, get_current_user
from ..core.permissions import Permission, require_permission
from ..services.auth_service import AuthService
from backend.core.response import success_response, StandardResponse

router = APIRouter(prefix="/users", tags=["Users"])


# --- User Profile ---
@router.put("/me", response_model=StandardResponse[schemas.User])
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update current user profile (email, password)."""

    # Reload user to attach to session
    stmt = select(models.User).where(models.User.id == current_user.id)
    user = (await db.execute(stmt)).scalars().first()

    password_changed = False

    if user_update.email:
        user.email = user_update.email

    if user_update.password:
        validate_password(user_update.password)
        user.hashed_password = auth.get_password_hash(user_update.password)
        password_changed = True

    await db.commit()

    # REVOKE ALL SESSIONS if password was changed
    if password_changed:
        revoked_count = await AuthService.revoke_all_user_sessions(db, user.id)
        if revoked_count > 0:
            import logging
            logger = logging.getLogger("smart_clinic")
            logger.info(f"Revoked {revoked_count} sessions for user {user.username} after password change")

    await db.refresh(user)
    return success_response(
        data=schemas.User.model_validate(user), message="Profile updated"
    )


@router.post("/me/fcm-token", response_model=StandardResponse[dict])
async def update_fcm_token(
    token_data: schemas.FCMTokenUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Register/Update FCM token for push notifications."""
    current_user.fcm_token = token_data.token
    await db.commit()
    return success_response(message="FCM token updated successfully")


@router.get("/me", response_model=StandardResponse[schemas.User])
async def get_user_me(current_user: models.User = Depends(get_current_user)):
    """Get current user details."""
    return success_response(data=schemas.User.model_validate(current_user))


@router.get("", response_model=StandardResponse[List[schemas.User]])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    role: str = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Get users for current tenant (Admin sees all, Staff see doctors)."""
    # Permission.SYSTEM_CONFIG already ensures only Admin/Manager can access this.
    # We will let everyone with SYSTEM_CONFIG see all users.
    query_role = role

    users = await crud.get_users(
        db, current_user.tenant_id, skip=skip, limit=limit, role=query_role
    )
    data = [schemas.User.model_validate(u) for u in users]
    return success_response(data=data)


@router.get("/doctors", response_model=StandardResponse[List[dict]])
async def list_doctors(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get active doctors for dropdowns. Available to all authenticated users."""
    stmt = (
        select(models.User)
        .where(
            models.User.tenant_id == current_user.tenant_id,
            models.User.role == "doctor",
            models.User.is_active == True,  # noqa: E712
        )
    )
    result = await db.execute(stmt)
    doctors = result.scalars().all()
    return success_response(
        data=[{"id": d.id, "full_name": d.full_name or d.username} for d in doctors]
    )


@router.post("/register", response_model=StandardResponse[schemas.User])
async def register_user(
    username: str,
    password: str,
    full_name: str = None,
    role: str = "doctor",
    permissions: str = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Register a new user (admin only)."""
    if await crud.get_user(db, username):
        raise HTTPException(status_code=400, detail="Username already registered")

    # --- User Limit Check (Seat-based) ---
    # Get tenant's subscription plan
    stmt = select(models.Tenant).where(models.Tenant.id == current_user.tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalars().first()
    if tenant and tenant.subscription_plan:
        max_users = tenant.subscription_plan.max_users
        if max_users is not None:  # None means unlimited
            stmt_count = select(func.count()).select_from(models.User).where(models.User.tenant_id == current_user.tenant_id)
            res_count = await db.execute(stmt_count)
            current_user_count = res_count.scalar() or 0
            if current_user_count >= max_users:
                raise HTTPException(
                    status_code=400,
                    detail=f"لقد وصلت للحد الأقصى من المستخدمين ({max_users}) في خطتك الحالية. يرجى الترقية لإضافة المزيد.",
                )
    # --- End User Limit Check ---

    # Validate password strength reusing central logic
    validate_password(password)

    hashed_password = auth.get_password_hash(password)
    user_in = schemas.User(username=username, full_name=full_name, role=role)
    if permissions:
        user_in.permissions = permissions

    user = await crud.create_user(db, user_in, hashed_password, current_user.tenant_id)
    return success_response(data=user, message="User registered")


@router.put("/{user_id}", response_model=StandardResponse[schemas.User])
async def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Update a user (admin only)."""
    user = await crud.get_user_by_id(db, user_id, current_user.tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    password_changed = False

    # Check if password is being updated
    if user_update.password:
        validate_password(user_update.password)
        password_changed = True

    updated_user = await crud.update_user(db, user_id, user_update, current_user.tenant_id)

    # REVOKE ALL SESSIONS if admin changed the password
    if password_changed:
        revoked_count = await AuthService.revoke_all_user_sessions(db, user_id)
        if revoked_count > 0:
            import logging
            logger = logging.getLogger("smart_clinic")
            logger.info(f"Admin {current_user.username} revoked {revoked_count} sessions for user {user.username} after password change")

    return success_response(
        data=schemas.User.model_validate(updated_user), message="User updated"
    )


@router.delete("/{user_id}", response_model=StandardResponse[dict])
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Delete a user (admin only)."""
    await crud.delete_user(db, user_id, current_user.tenant_id)
    return success_response(message="User deleted")
