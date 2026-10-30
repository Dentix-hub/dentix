"""
Users Router
Handles user management within a tenant.
"""

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from .. import models, schemas, crud, auth
from backend.database import get_async_db
from .auth.dependencies import validate_password, get_current_user
from ..core.permissions import Permission, require_permission
from ..core.tenant_context import require_tenant_id
from ..services.auth_service import AuthService
from backend.core.response import success_response, StandardResponse

router = APIRouter(prefix="/users", tags=["Users"])


def _require_tenant_user_admin(current_user: models.User) -> int:
    """Enforce the same admin-only boundary as the `/users` application route."""
    tenant_id = require_tenant_id(current_user)
    if current_user.role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return tenant_id


def _validate_tenant_role(role: str | None) -> None:
    """Platform super-admin is never a tenant-managed role."""
    if role == "super_admin":
        raise HTTPException(
            status_code=403,
            detail="super_admin is a platform role and cannot be assigned from tenant user management",
        )


# --- User Profile ---
@router.put("/me", response_model=StandardResponse[schemas.User])
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update current user profile (email, password)."""

    stmt = select(models.User).where(models.User.id == current_user.id)
    user = (await db.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    password_changed = False

    if "email" in user_update.model_fields_set:
        email_owner = await crud.get_user_by_email(db, user_update.email)
        if email_owner and email_owner.id != user.id:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = user_update.email

    if user_update.password:
        validate_password(user_update.password, username=user.username)
        user.hashed_password = auth.get_password_hash(user_update.password)
        password_changed = True

    await db.commit()

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
    """Get users for the current clinic tenant."""
    tenant_id = _require_tenant_user_admin(current_user)
    users = await crud.get_users(db, tenant_id, skip=skip, limit=limit, role=role)
    data = [schemas.User.model_validate(u) for u in users]
    return success_response(data=data)


@router.get("/doctors", response_model=StandardResponse[List[dict]])
async def list_doctors(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get active doctors for dropdowns. Available to authenticated tenant users."""
    tenant_id = require_tenant_id(current_user)
    stmt = (
        select(models.User)
        .where(
            models.User.tenant_id == tenant_id,
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
    payload: Optional[schemas.UserRegisterRequest] = Body(default=None),
    username: Optional[str] = Query(
        default=None,
        deprecated=True,
        description="Deprecated fallback: pass username in JSON body instead.",
    ),
    password: Optional[str] = Query(
        default=None,
        deprecated=True,
        description="Deprecated fallback: pass password in JSON body instead.",
    ),
    full_name: Optional[str] = Query(default=None, deprecated=True),
    role: Optional[str] = Query(default=None, deprecated=True),
    permissions: Optional[str] = Query(default=None, deprecated=True),
    patient_visibility_mode: Optional[str] = Query(default=None, deprecated=True),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Register a new user in the current tenant."""
    tenant_id = _require_tenant_user_admin(current_user)

    raw_username = (
        payload.username
        if (payload is not None and payload.username is not None)
        else username
    )
    raw_password = (
        payload.password
        if (payload is not None and payload.password is not None)
        else password
    )
    effective_full_name = (
        payload.full_name
        if (payload is not None and payload.full_name is not None)
        else full_name
    )
    effective_role = (
        payload.role
        if (payload is not None and payload.role is not None)
        else role
    ) or "doctor"
    effective_permissions = (
        payload.permissions
        if (payload is not None and payload.permissions is not None)
        else permissions
    )
    effective_visibility_mode = (
        payload.patient_visibility_mode
        if (payload is not None and payload.patient_visibility_mode is not None)
        else patient_visibility_mode
    ) or "all_assigned"

    _validate_tenant_role(effective_role)
    clean_display_username = crud.validate_and_trim_username(raw_username)

    if await crud.get_user(db, clean_display_username):
        raise HTTPException(status_code=400, detail="Username already registered")

    new_email = payload.email if payload is not None else None
    if await crud.get_user_by_email(db, new_email):
        raise HTTPException(status_code=400, detail="Email already registered")

    stmt = select(models.Tenant).where(models.Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalars().first()
    if tenant and tenant.subscription_plan:
        max_users = tenant.subscription_plan.max_users
        if max_users is not None:
            stmt_count = select(func.count()).select_from(models.User).where(models.User.tenant_id == tenant_id)
            res_count = await db.execute(stmt_count)
            current_user_count = res_count.scalar() or 0
            if current_user_count >= max_users:
                raise HTTPException(
                    status_code=400,
                    detail=f"لقد وصلت للحد الأقصى من المستخدمين ({max_users}) في خطتك الحالية. يرجى الترقية لإضافة المزيد.",
                )

    validate_password(raw_password or "", username=clean_display_username)

    hashed_password = auth.get_password_hash(raw_password)
    user_in = schemas.User(
        username=clean_display_username,
        email=new_email,
        full_name=effective_full_name,
        role=effective_role,
        patient_visibility_mode=effective_visibility_mode,
    )
    if effective_permissions:
        user_in.permissions = effective_permissions

    user = await crud.create_user(db, user_in, hashed_password, tenant_id)
    return success_response(data=user, message="User registered")


@router.put("/{user_id}", response_model=StandardResponse[schemas.User])
async def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Update a user in the current tenant."""
    tenant_id = _require_tenant_user_admin(current_user)
    _validate_tenant_role(user_update.role)

    user = await crud.get_user_by_id(db, user_id, tenant_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "super_admin":
        raise HTTPException(status_code=403, detail="Platform users cannot be managed here")

    if "username" in user_update.model_fields_set or user_update.username is not None:
        trimmed_username = crud.validate_and_trim_username(user_update.username)
        existing_user = await crud.get_user(db, trimmed_username)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Username already registered")
        user_update.username = trimmed_username

    if "email" in user_update.model_fields_set:
        email_owner = await crud.get_user_by_email(db, user_update.email)
        if email_owner and email_owner.id != user_id:
            raise HTTPException(status_code=400, detail="Email already registered")

    password_changed = False
    if user_update.password:
        validate_password(user_update.password, username=user_update.username or user.username)
        password_changed = True

    updated_user = await crud.update_user(db, user_id, user_update, tenant_id)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

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
    """Delete a user in the current tenant."""
    tenant_id = _require_tenant_user_admin(current_user)
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own active account")

    deleted_user = await crud.delete_user(db, user_id, tenant_id)
    if not deleted_user:
        raise HTTPException(status_code=404, detail="User not found")
    return success_response(data={"user_id": user_id}, message="User deleted")
