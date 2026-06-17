from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from ..core.response import success_response, error_response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import List
import os
import json
from datetime import datetime

from backend import models, schemas
from backend.database import get_async_db
from backend.core.permissions import Role
from backend.utils.audit_logger import log_admin_action
from backend.core.permissions import Permission, require_permission
from backend.services.backup_service import run_backup_task
from backend.services.auth_service import AuthService

router = APIRouter(
    prefix="/admin",
    tags=["System Admin"],
    responses={404: {"description": "Not found"}},
)

# Lazy import to avoid circular dependency with main.py
_drive_client = None

def get_drive_client():
    global _drive_client
    if _drive_client is None:
        from backend.main import drive_client

        _drive_client = drive_client
    return _drive_client


# Dependency
def require_super_admin(current_user: models.User = Depends(require_permission(Permission.SYSTEM_CONFIG))):
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


# --- Global User Management ---
@router.get("/users", response_model=List[schemas.UserAdminView])
async def get_global_users(
    search_query: str = None,
    role: str = None,
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    stmt = (
        select(models.User)
        .where(models.User.is_deleted == False)  # noqa: E712
        .options(joinedload(models.User.tenant))
    )

    if search_query:
        search = f"%{search_query}%"
        stmt = stmt.join(models.Tenant, isouter=True).where(
            (models.User.username.ilike(search))
            | (models.User.email.ilike(search))
            | (models.Tenant.name.ilike(search))
        )

    if role and role != "all":
        stmt = stmt.where(models.User.role == role)

    stmt = stmt.offset(skip).limit(limit)
    res = await db.execute(stmt)
    users = list(res.scalars().all())

    result = []
    for u in users:
        u_schema = schemas.UserAdminView.model_validate(u)
        if u.tenant:
            u_schema.tenant_name = u.tenant.name
        else:
            u_schema.tenant_name = "System / No Clinic"
        result.append(u_schema)

    return result


@router.post("/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    res = await db.execute(select(models.User).where(models.User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")

    new_status = not user.is_active
    user.is_active = new_status

    # REVOKE ALL SESSIONS when user is disabled
    if not new_status:
        revoked_count = await AuthService.revoke_all_user_sessions(db, user.id)
        if revoked_count > 0:
            import logging
            logger = logging.getLogger("smart_clinic")
            logger.info(f"Admin {current_user.username} revoked {revoked_count} sessions for disabled user {user.username}")

    log_admin_action(
        db,
        current_user,
        "update",
        "user",
        user.id,
        details=f"{'Enabled' if new_status else 'Disabled'} user {user.username}",
        target_user_id=user.id,
        new_value={"is_active": new_status},
    )

    await db.commit()
    return success_response({
        "message": f"User {'enabled' if new_status else 'disabled'} successfully",
        "is_active": new_status,
    })


# --- System Settings ---
@router.get("/settings", response_model=List[schemas.SystemSetting])
async def get_system_settings(
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    res = await db.execute(select(models.SystemSetting))
    return list(res.scalars().all())


@router.put("/settings/{key}", response_model=schemas.SystemSetting)
async def update_system_setting(
    key: str,
    setting_update: schemas.SystemSetting,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    res = await db.execute(
        select(models.SystemSetting).where(models.SystemSetting.key == key)
    )
    setting = res.scalar_one_or_none()
    if not setting:
        setting = models.SystemSetting(key=key, value=setting_update.value)
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
        return setting

    setting.value = setting_update.value
    await db.commit()
    await db.refresh(setting)
    return setting


@router.get("/system/backup/google-status")
async def get_google_drive_status(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
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

    return success_response({
        "connected": bool(setting and setting.value),
        "last_backup": {
            "status": last_status.value if last_status else None,
            "message": last_message.value if last_message else None,
            "date": last_run.value if last_run else None,
        },
    })


@router.get("/system/backup/google-auth")
async def get_system_google_auth_url(
    current_user: models.User = Depends(require_super_admin),
):
    auth_url = get_drive_client().get_auth_url(state="super_admin")
    return success_response(data={"url": auth_url})


@router.post("/system/backup/google-upload", status_code=202)
async def upload_to_google_drive(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
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
    db_url = os.getenv("DATABASE_URL")

    background_tasks.add_task(run_backup_task, refresh_token, db_url)

    return success_response({
        "success": True,
        "message": "Backup started in background.",
        "status": "processing",
    })


@router.delete("/system/backup/google-auth")
async def disconnect_google_drive(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_super_admin),
):
    """Disconnect the Google Drive account."""
    res_setting = await db.execute(
        select(models.SystemSetting)
        .where(models.SystemSetting.key == "google_refresh_token_super_admin")
    )
    setting = res_setting.scalar_one_or_none()
    if setting:
        await db.delete(setting)
        await db.commit()
        return success_response(data={"success": True, "message": "Google Drive disconnected successfully"})
    else:
        return success_response(data={"success": True, "message": "Google Drive was not connected"})


@router.get("/backup")
async def download_backup(
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Download system JSON backup."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"smart_clinic_json_backup_{timestamp}.json"

    async def iter_json(db_session: AsyncSession):
        yield "{\n"
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


# --- Security Management (Sessions & IP Blocking) ---
@router.get("/security/sessions")
async def get_global_sessions(
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """List all active user sessions across all tenants."""
    from backend.services.security_service import SecurityService
    service = SecurityService(db)
    sessions = await service.get_active_sessions()
    return success_response(sessions)


@router.delete("/security/sessions/{session_id}")
async def terminate_session(
    session_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Terminate a specific user session."""
    from backend.services.security_service import SecurityService
    service = SecurityService(db)
    if await service.terminate_session(session_id):
        return success_response({"message": "Session terminated successfully"})
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/security/blocked-ips")
async def get_blocked_ips(
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Get list of all blocked IP addresses."""
    res = await db.execute(select(models.BlockedIP))
    blocked = list(res.scalars().all())
    return success_response([
        {
            "id": b.id,
            "ip_address": b.ip_address,
            "reason": b.reason,
            "blocked_by": b.blocked_by,
            "created_at": b.created_at,
            "expires_at": b.expires_at
        }
        for b in blocked
    ])


@router.post("/security/ip-block")
async def block_ip(
    block_data: dict,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Block an IP address."""
    from backend.services.security_service import SecurityService
    ip = block_data.get("ip_address")
    reason = block_data.get("reason", "Administrative block")

    if not ip:
        raise HTTPException(status_code=400, detail="IP address required")

    await SecurityService.block_ip(db, ip, reason, current_user.username)
    return success_response({"message": f"IP {ip} blocked successfully"})


@router.delete("/security/ip-block/{ip_address}")
async def unblock_ip(
    ip_address: str,
    current_user: models.User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Unblock an IP address."""
    from backend.services.security_service import SecurityService
    await SecurityService.unblock_ip(db, ip_address)
    return success_response({"message": f"IP {ip_address} unblocked successfully"})
