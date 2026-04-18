from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from ..core.response import success_response, error_response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import List
import os
import json
from datetime import datetime

from backend import models, schemas
from backend.database import get_db
from backend.core.permissions import Role
from backend.utils.audit_logger import log_admin_action
from backend.core.permissions import Permission, require_permission
from backend.services.backup_service import run_backup_task

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
def get_global_users(
    search_query: str = None,
    role: str = None,
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    query = (
        db.query(models.User)
        .filter(models.User.is_deleted == False)
        .options(joinedload(models.User.tenant))
    )

    if search_query:
        search = f"%{search_query}%"
        query = query.join(models.Tenant, isouter=True).filter(
            (models.User.username.ilike(search))
            | (models.User.email.ilike(search))
            | (models.Tenant.name.ilike(search))
        )

    if role and role != "all":
        query = query.filter(models.User.role == role)

    users = query.offset(skip).limit(limit).all()

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
def toggle_user_status(
    user_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")

    new_status = not user.is_active
    user.is_active = new_status

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

    db.commit()
    return success_response({
        "message": f"User {'enabled' if new_status else 'disabled'} successfully",
        "is_active": new_status,
    })


# --- System Settings ---
@router.get("/settings", response_model=List[schemas.SystemSetting])
def get_system_settings(
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return db.query(models.SystemSetting).all()


@router.put("/settings/{key}", response_model=schemas.SystemSetting)
def update_system_setting(
    key: str,
    setting_update: schemas.SystemSetting,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    setting = (
        db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    )
    if not setting:
        setting = models.SystemSetting(key=key, value=setting_update.value)
        db.add(setting)
        db.commit()
        db.refresh(setting)
        return setting

    setting.value = setting_update.value
    db.commit()
    db.refresh(setting)
    return setting


@router.get("/system/backup/google-status")
def get_google_drive_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    setting = (
        db.query(models.SystemSetting)
        .filter(models.SystemSetting.key == "google_refresh_token_super_admin")
        .first()
    )

    # Fetch status
    last_status = (
        db.query(models.SystemSetting)
        .filter(models.SystemSetting.key == "backup_last_status")
        .first()
    )
    last_message = (
        db.query(models.SystemSetting)
        .filter(models.SystemSetting.key == "backup_last_message")
        .first()
    )
    last_run = (
        db.query(models.SystemSetting)
        .filter(models.SystemSetting.key == "backup_last_run")
        .first()
    )

    return success_response({
        "connected": bool(setting and setting.value),
        "last_backup": {
            "status": last_status.value if last_status else None,
            "message": last_message.value if last_message else None,
            "date": last_run.value if last_run else None,
        },
    })


@router.get("/system/backup/google-auth")
def get_system_google_auth_url(
    current_user: models.User = Depends(require_super_admin),
):
    auth_url = get_drive_client().get_auth_url(state="super_admin")
    return success_response(data={"url": auth_url})


@router.post("/system/backup/google-upload", status_code=202)
def upload_to_google_drive(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    setting = (
        db.query(models.SystemSetting)
        .filter(models.SystemSetting.key == "google_refresh_token_super_admin")
        .first()
    )
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
def disconnect_google_drive(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    """Disconnect the Google Drive account."""
    setting = (
        db.query(models.SystemSetting)
        .filter(models.SystemSetting.key == "google_refresh_token_super_admin")
        .first()
    )
    if setting:
        db.delete(setting)
        db.commit()
        return success_response(data={"success": True, "message": "Google Drive disconnected successfully"})
    else:
        return success_response(data={"success": True, "message": "Google Drive was not connected"})


@router.get("/backup")
def download_backup(
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Download system JSON backup."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"smart_clinic_json_backup_{timestamp}.json"

    def iter_json(db_session: Session):
        yield "{\n"
        yield '  "tenants": [\n'
        tenants = db_session.query(models.Tenant).all()
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
        users = db_session.query(models.User).all()
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
