import logging
import datetime
from datetime import timezone
import json
import csv
import io
from typing import List, Literal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from backend.core.permissions import Permission, require_permission, Role  # noqa: F401 — used by guards below; explicit re-import is the regression guard for 2026-06-19 system_logs NameError on deployed staging

from backend.database import get_async_db
from backend import models, schemas
from ..schemas import system_log as schema_system
from ..auth import get_password_hash
from ..services.admin_service import AdminService
from ..services.security_service import SecurityService
from ..services.auth_service import AuthService
from .auth.dependencies import validate_password
from backend.core.response import success_response, StandardResponse
from backend.core.limiter import limiter


logger = logging.getLogger(__name__)


def require_super_admin(
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


router = APIRouter(
    prefix="/admin/system",
    tags=["System Admin"],
    responses={404: {"description": "Not found"}},
)


class LogContext(BaseModel):
    stack_trace: str | None = Field(default=None, max_length=12000)
    path: str | None = Field(default=None, max_length=2048)
    user_agent: str | None = Field(default=None, max_length=512)

    model_config = ConfigDict(extra="ignore")


class LogEntry(BaseModel):
    level: Literal["INFO", "WARNING", "ERROR", "CRITICAL"] = "ERROR"
    message: str = Field(min_length=1, max_length=4000)
    context: LogContext = Field(default_factory=LogContext)
    timestamp: str | None = Field(default=None, max_length=64)

    model_config = ConfigDict(extra="ignore")


class AdminProfileUpdate(BaseModel):
    username: str | None = Field(default=None, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=128)

    model_config = ConfigDict(extra="ignore")


@router.put("/profile", response_model=StandardResponse[schemas.User])
async def update_super_admin_profile(
    profile_data: AdminProfileUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    """Update Super Admin profile credentials (username, email, password)."""
    user = await db.get(models.User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    has_changes = False

    if profile_data.username and profile_data.username.strip():
        new_username = profile_data.username.strip()
        if new_username != user.username:
            stmt = select(models.User).where(models.User.username == new_username, models.User.id != user.id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=400, detail="اسم المستخدم مستخدم بالفعل")
            user.username = new_username
            has_changes = True

    if profile_data.email and profile_data.email.strip():
        new_email = profile_data.email.strip()
        if new_email != user.email:
            stmt = select(models.User).where(models.User.email == new_email, models.User.id != user.id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=400, detail="البريد الإلكتروني مستخدم بالفعل")
            user.email = new_email
            has_changes = True

    if profile_data.password and profile_data.password.strip():
        validate_password(profile_data.password.strip())
        user.hashed_password = get_password_hash(profile_data.password.strip())
        has_changes = True

    if not has_changes:
        raise HTTPException(status_code=400, detail="لم يتم تقديم أي بيانات صالحة للتحديث")

    await db.commit()
    await db.refresh(user)
    return success_response(data=schemas.User.model_validate(user), message="تم تحديث الملف الشخصي بنجاح")



from backend.core.logging_sanitizer import sanitize_text, sanitize_stack_trace

@router.post("/logs", response_model=StandardResponse[dict])
@limiter.limit("10/minute")
async def submit_frontend_log(
    log: LogEntry,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    """Receive logs from frontend and save to DB."""
    try:
        level = log.level.upper() if log.level else "ERROR"

        new_log = models.SystemError(
            level=level,
            source="FRONTEND",
            message=sanitize_text(log.message, max_length=4000) or "Frontend Log",
            stack_trace=sanitize_stack_trace(log.context.stack_trace, max_length=12000),
            path=sanitize_text(log.context.path, max_length=2048),
            user_agent=sanitize_text(request.headers.get("user-agent"), max_length=512),
            ip_address=request.client.host if request.client else None,
            created_at=datetime.datetime.now(timezone.utc),
        )

        db.add(new_log)
        await db.commit()

        return success_response(data={"status": "ok"})
    except Exception:
        logger.exception("[LOG_FAIL] Could not save log to DB")
        return success_response(success=False, message="Log could not be saved")


@router.get("/logs", response_model=StandardResponse[List[schema_system.SystemError]])
async def get_system_logs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Retrieve system logs from Database."""
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    stmt = (
        select(models.SystemError)
        .order_by(models.SystemError.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    logs = list(res.scalars().all())

    return success_response(data=logs)


@router.delete("/logs/clear", response_model=StandardResponse[dict])
async def clear_system_logs(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Delete all system logs."""
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.execute(delete(models.SystemError))
    await db.commit()
    return success_response(message="All system logs cleared successfully")


@router.delete("/logs/{log_id}", response_model=StandardResponse[dict])
async def delete_system_log(
    log_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Delete a specific system log."""
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    res = await db.execute(select(models.SystemError).where(models.SystemError.id == log_id))
    log = res.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    await db.delete(log)
    await db.commit()
    return success_response(message="Log deleted successfully")


@router.get("/logs/export")
async def export_system_logs(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Export system logs as CSV."""
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    stmt = select(models.SystemError).order_by(models.SystemError.created_at.desc())
    res = await db.execute(stmt)
    logs = list(res.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID", "Level", "Source", "Message", "Path", "Method",
        "User ID", "Tenant ID", "IP Address", "User Agent", "Created At", "Stack Trace"
    ])

    # Data
    for log in logs:
        writer.writerow([
            log.id,
            log.level,
            log.source,
            log.message,
            log.path,
            log.method,
            log.user_id,
            log.tenant_id,
            log.ip_address,
            log.user_agent,
            log.created_at.isoformat() if log.created_at else "",
            log.stack_trace
        ])

    output.seek(0)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"system_logs_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.put("/profile", response_model=StandardResponse[dict])
async def update_profile(
    profile_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    res = await db.execute(select(models.User).where(models.User.id == current_user.id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    if "username" in profile_data and profile_data["username"]:
        user.username = profile_data["username"]
    if "email" in profile_data and profile_data["email"]:
        user.email = profile_data["email"]
    if "password" in profile_data and profile_data["password"]:
        user.hashed_password = get_password_hash(profile_data["password"])

    await db.commit()
    return success_response(
        data={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        },
        message="Profile updated successfully",
    )


@router.get("/backup")
async def download_backup(
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
    db: AsyncSession = Depends(get_async_db),
):
    raise HTTPException(
        status_code=410,
        detail="Cross-tenant raw database export over HTTP has been permanently disabled for security. Use clinic-scoped JSON export.",
    )


@router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    raise HTTPException(
        status_code=410,
        detail="Raw database restore over HTTP has been permanently disabled for security. Use clinic-scoped JSON restore or guarded CLI tools.",
    )


# --- Tenant Management Endpoints ---


@router.delete("/tenants/{tenant_id}", response_model=StandardResponse[dict])
async def archive_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    service = AdminService(db)
    tenant = await service.archive_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return success_response(message="Tenant archived successfully")


@router.post("/tenants/{tenant_id}/restore", response_model=StandardResponse[dict])
async def restore_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    service = AdminService(db)
    tenant = await service.restore_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return success_response(message="Tenant restored successfully")


@router.delete("/tenants/{tenant_id}/permanent", response_model=StandardResponse[dict])
async def permanently_delete_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    service = AdminService(db)
    try:
        success = await service.permanently_delete_tenant(tenant_id)
        if not success:
            raise HTTPException(status_code=404, detail="Tenant not found")
    except Exception as e:
        logger.error("Delete failed: %s", e)
        raise HTTPException(status_code=400, detail=f"Cannot delete tenant: {str(e)}")

    return success_response(message="Tenant permanently deleted")


@router.post("/tenants/{tenant_id}/assign-plan", response_model=StandardResponse[dict])
async def assign_tenant_plan(
    tenant_id: int,
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    service = AdminService(db)

    res = await db.execute(
        select(models.SubscriptionPlan)
        .where(models.SubscriptionPlan.id == plan_id)
    )
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    tenant = await service.update_tenant(tenant_id, plan=plan.name, plan_id=plan.id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return success_response(
        data={"tenant": tenant.name}, message="Plan updated successfully"
    )


# --- User Management (Super Admin) ---
@router.get("/tenants/{tenant_id}/users", response_model=StandardResponse[dict])
async def get_tenant_users(
    tenant_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Get all users for a specific tenant (Super Admin only)."""
    logger.debug("[get_tenant_users] tenant_id=%d, role=%s", tenant_id, current_user.role)

    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    res_tenant = await db.execute(
        select(models.Tenant)
        .where(models.Tenant.id == tenant_id, models.Tenant.is_deleted == False)  # noqa: E712
    )
    tenant = res_tenant.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=404,
            detail=f"Tenant with ID {tenant_id} not found or has been deleted",
        )

    res_users = await db.execute(
        select(models.User)
        .where(models.User.tenant_id == tenant_id, models.User.is_deleted == False)  # noqa: E712
    )
    users = list(res_users.scalars().all())

    logger.debug("[get_tenant_users] Found %d users for tenant %d", len(users), tenant_id)

    result = {
        "users": [
            {
                "id": u.id,
                "username": u.username
                or (u.email.split("@")[0] if u.email else f"User#{u.id}"),
                "email": u.email or "no-email",
                "role": u.role,
                "is_active": u.is_active,
                "failed_login_attempts": u.failed_login_attempts or 0,
                "account_locked_until": str(u.account_locked_until)
                if u.account_locked_until
                else None,
            }
            for u in users
        ]
    }
    return success_response(data=result)


@router.post("/users/{user_id}/reset-password", response_model=StandardResponse[dict])
async def reset_user_password(
    user_id: int,
    password_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Reset password for any user (Super Admin only)."""
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    new_password = password_data.get("new_password")
    if not new_password:
        raise HTTPException(status_code=400, detail="Password is required")

    validate_password(new_password)

    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(new_password)

    revoked_count = await AuthService.revoke_all_user_sessions(db, user.id)
    if revoked_count > 0:
        import logging
        logger = logging.getLogger("smart_clinic")
        logger.info(f"Super admin {current_user.username} revoked {revoked_count} sessions for user {user.username} after password reset")

    user.failed_login_attempts = 0
    user.account_locked_until = None
    user.last_failed_login = None
    user.is_active = True

    await db.commit()

    return success_response(
        data={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "tenant_id": user.tenant_id,
        },
        message=f"Password reset successfully for user: {user.username}",
    )


@router.get("/search", response_model=StandardResponse[List[dict]])
async def global_admin_search(
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Global search for Super Admin Command Palette."""
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    service = AdminService(db)
    results = await service.global_search(q)
    return success_response(data=results)


@router.get("/security/stats", response_model=StandardResponse[dict])
async def get_security_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    stats = await SecurityService.get_security_stats(db)
    return success_response(data=stats)


@router.get("/security/chart", response_model=StandardResponse[List[dict]])
async def get_security_chart(
    days: int = 7,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    chart = await SecurityService.get_login_attempts_chart(db, days)
    return success_response(data=chart)


@router.get("/audit-logs", response_model=StandardResponse[dict])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    tenant_id: int = None,
    user_id: int = None,
    action: str = None,
    entity_type: str = None,
    start_date: datetime.datetime = None,
    end_date: datetime.datetime = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    filters = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "start_date": start_date,
        "end_date": end_date
    }
    logs = await SecurityService.get_audit_logs(db, skip, limit, filters)
    return success_response(data=logs)


@router.get("/audit-logs/export")
async def export_audit_logs(
    tenant_id: int = None,
    user_id: int = None,
    action: str = None,
    entity_type: str = None,
    start_date: datetime.datetime = None,
    end_date: datetime.datetime = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    filters = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "start_date": start_date,
        "end_date": end_date,
    }
    logs_data = await SecurityService.get_audit_logs(db, skip=0, limit=10000, filters=filters)
    logs = logs_data["logs"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Action", "Entity", "Performed By", "Tenant", "Date", "Details"])

    for log in logs:
        writer.writerow([
            log["id"],
            log["action"],
            f"{log['entity_type']} #{log['entity_id']}",
            log["performed_by_username"],
            log["tenant_id"] if log["tenant_id"] is not None else "Global",
            log["created_at"].isoformat() if log["created_at"] else "",
            log["details"]
        ])

    output.seek(0)
    filename = f"audit_logs_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

