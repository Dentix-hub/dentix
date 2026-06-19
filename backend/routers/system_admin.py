import logging
import os
import datetime
from datetime import timezone
import json
import csv
import io
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from backend.core.permissions import Permission, require_permission, Role  # noqa: F401 — used by guards below; explicit re-import is the regression guard for 2026-06-19 system_logs NameError on deployed staging
from backend.core import startup
from ..database import get_async_db
from .. import models
from ..schemas import system_log as schema_system
from ..auth import get_password_hash
import subprocess
import shutil
from ..services.backup_service import run_backup_task
from ..services.admin_service import AdminService
from ..services.security_service import SecurityService
from ..services.auth_service import AuthService
from .auth.dependencies import validate_password
from backend.core.response import success_response, StandardResponse


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


class LogEntry(BaseModel):
    level: str
    message: str
    context: dict = {}
    timestamp: str = None


@router.post("/logs", response_model=StandardResponse[dict])
async def submit_frontend_log(
    log: LogEntry,
    db: AsyncSession = Depends(get_async_db),
):
    """Receive logs from frontend and save to DB."""
    try:
        level = log.level.upper() if log.level else "ERROR"

        new_log = models.SystemError(
            level=level,
            source="FRONTEND",
            message=log.message,
            stack_trace=log.context.get("stack_trace"),
            path=log.context.get("path"),
            user_agent=log.context.get("user_agent"),
            created_at=datetime.datetime.now(timezone.utc),
        )

        db.add(new_log)
        await db.commit()

        return success_response(data={"status": "ok"})
    except Exception as e:
        logger.error("[LOG_FAIL] Could not save log to DB: %s", e)
        return success_response(success=False, message=str(e))


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
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Implementation of JSON Backup (Fallback for environments without pg_dump)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"smart_clinic_json_backup_{timestamp}.json"

    async def iter_json(db_session: AsyncSession):
        yield "{\n"

        # 1. Tenants
        yield '  "tenants": [\n'
        res_tenants = await db_session.execute(select(models.Tenant))
        tenants = list(res_tenants.scalars().all())
        for i, t in enumerate(tenants):
            data = {
                "id": t.id,
                "name": t.name,
                "domain": t.domain,
                "plan_id": t.subscription_plan_id,
                "is_active": t.is_active,
            }
            yield f"    {json.dumps(data)}" + (",\n" if i < len(tenants) - 1 else "\n")
        yield "  ],\n"

        # 2. Users (Sanitized)
        yield '  "users": [\n'
        res_users = await db_session.execute(select(models.User))
        users = list(res_users.scalars().all())
        for i, u in enumerate(users):
            data = {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "tenant_id": u.tenant_id,
                "is_active": u.is_active,
            }
            yield f"    {json.dumps(data)}" + (",\n" if i < len(users) - 1 else "\n")
        yield "  ]\n"

        yield "}"

    return StreamingResponse(
        iter_json(db),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...), current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    raise HTTPException(
        status_code=501,
        detail="File-based restore not supported in production (Postgres Only)",
    )


# --- Google Drive Backup (Super Admin) ---


@router.get("/backup/google-status", response_model=StandardResponse[dict])
async def get_google_drive_status(
    db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    res_setting = await db.execute(
        select(models.SystemSetting)
        .where(models.SystemSetting.key == "google_refresh_token_super_admin")
    )
    setting = res_setting.scalar_one_or_none()

    # Fetch status
    res_status = await db.execute(
        select(models.SystemSetting)
        .where(models.SystemSetting.key == "backup_last_status")
    )
    last_status = res_status.scalar_one_or_none()

    res_message = await db.execute(
        select(models.SystemSetting)
        .where(models.SystemSetting.key == "backup_last_message")
    )
    last_message = res_message.scalar_one_or_none()

    res_run = await db.execute(
        select(models.SystemSetting)
        .where(models.SystemSetting.key == "backup_last_run")
    )
    last_run = res_run.scalar_one_or_none()

    return success_response(
        data={
            "connected": bool(setting and setting.value),
            "last_backup": {
                "status": last_status.value if last_status else None,
                "message": last_message.value if last_message else None,
                "date": last_run.value if last_run else None,
            },
        }
    )


@router.get("/backup/google-auth", response_model=StandardResponse[dict])
def get_google_auth_url(current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    auth_url = startup.drive_client.get_auth_url(state="super_admin")
    return success_response(data={"url": auth_url})


@router.post("/backup/google-upload", status_code=202, response_model=StandardResponse[dict])
async def upload_to_google_drive(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    res_setting = await db.execute(
        select(models.SystemSetting)
        .where(models.SystemSetting.key == "google_refresh_token_super_admin")
    )
    setting = res_setting.scalar_one_or_none()
    if not setting or not setting.value:
        raise HTTPException(
            status_code=400, detail="Google Drive not connected. Please connect first."
        )

    refresh_token = setting.value

    try:
        check_process = subprocess.run(
            ["which", "pg_dump"], capture_output=True, timeout=5
        )
        if check_process.returncode != 0:
            raise HTTPException(
                status_code=503,
                detail="System tools (pg_dump) are initializing. Please wait 2 minutes and try again.",
            )
    except FileNotFoundError:
        try:
            if not shutil.which("pg_dump"):
                raise HTTPException(
                    status_code=503,
                    detail="System tools (pg_dump) are not available on this system.",
                )
        except Exception:
            raise HTTPException(
                status_code=503,
                detail="System tools (pg_dump) are not available on this system.",
            )

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(
            status_code=500, detail="DATABASE_URL configuration missing"
        )

    background_tasks.add_task(run_backup_task, refresh_token, db_url)

    return success_response(
        data={"status": "processing"},
        message="Backup started in background. Please check Google Drive in a few minutes.",
    )


@router.delete("/backup/google-auth", response_model=StandardResponse[dict])
async def disconnect_google_drive(
    db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))
):
    """Disconnect the Google Drive account."""
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    res_setting = await db.execute(
        select(models.SystemSetting)
        .where(models.SystemSetting.key == "google_refresh_token_super_admin")
    )
    setting = res_setting.scalar_one_or_none()
    if setting:
        await db.delete(setting)
        await db.commit()
        return success_response(message="Google Drive disconnected successfully")
    else:
        return success_response(message="Google Drive was not connected")


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
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")

    filters = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type
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
            log["tenant_id"],
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


