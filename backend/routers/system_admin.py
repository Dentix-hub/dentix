from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from .. import models
from ..auth import get_password_hash
from .auth import get_current_user
from ..database import get_db
from ..constants import ROLES
import shutil
import os
import datetime
import logging


def get_drive_client():
    """Lazy import to avoid circular dependency."""
    from ..main import drive_client
    return drive_client

# Valid Log Levels
import logging
from pydantic import BaseModel

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

@router.post("/logs")
def submit_frontend_log(
    log: LogEntry,
    db: Session = Depends(get_db),
    # Optional authentication - generic logs might be anonymous
):
    """Receive logs from frontend and save to DB."""
    try:
        # Determine Source and Level
        # Frontend ensures uppercase, but safety first
        level = log.level.upper() if log.level else "ERROR"
        
        # Create Record
        new_log = models.SystemError(
            level=level,
            source="FRONTEND",
            message=log.message,
            stack_trace=log.context.get("stack_trace"),
            path=log.context.get("path"),
            user_agent=log.context.get("user_agent"),
            created_at=datetime.datetime.utcnow()
        )
        
        db.add(new_log)
        db.commit()
            
        return {"status": "ok"}
    except Exception as e:
        # Fallback to print if DB fails
        print(f"[LOG_FAIL] Could not save log to DB: {e}")
        return {"status": "error", "message": str(e)}

from typing import List
from ..schemas import system_log as schema_system

@router.get("/logs", response_model=List[schema_system.SystemError])
def get_system_logs(
    skip: int = 0, 
    limit: int = 50,
    current_user: models.User = Depends(get_current_user)
):
    """Retrieve system logs from Database."""
    if current_user.role != ROLES.SUPER_ADMIN:
         raise HTTPException(status_code=403, detail="Not authorized")
    
    logs = db.query(models.SystemError).order_by(models.SystemError.created_at.desc()).offset(skip).limit(limit).all()
    
    return logs



@router.put("/profile")
def update_profile(
    profile_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Query fresh user from THIS session to avoid detached instance error
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    if "username" in profile_data and profile_data["username"]:
        user.username = profile_data["username"]
    if "email" in profile_data and profile_data["email"]:
        user.email = profile_data["email"]
    if "password" in profile_data and profile_data["password"]:
        user.hashed_password = get_password_hash(profile_data["password"])
    
    db.commit()
    return {
        "message": "Profile updated successfully", 
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }

@router.get("/backup")
def download_backup(
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Implementation of JSON Backup (Fallback for environments without pg_dump)
    from datetime import datetime
    import json
    from fastapi.responses import StreamingResponse
    import io

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"smart_clinic_json_backup_{timestamp}.json"

    def iter_json(db_session: Session):
        yield "{\n"
        
        # 1. Tenants
        yield '  "tenants": [\n'
        tenants = db_session.query(models.Tenant).all()
        for i, t in enumerate(tenants):
            data = {
                "id": t.id, "name": t.name, "domain": t.domain, 
                "plan_id": t.subscription_plan_id, "is_active": t.is_active
            }
            yield f'    {json.dumps(data)}' + (",\n" if i < len(tenants)-1 else "\n")
        yield '  ],\n'

        # 2. Users (Sanitized)
        yield '  "users": [\n'
        users = db_session.query(models.User).all()
        for i, u in enumerate(users):
            data = {
                "id": u.id, "username": u.username, "email": u.email,
                "role": u.role, "tenant_id": u.tenant_id, "is_active": u.is_active
            }
            yield f'    {json.dumps(data)}' + (",\n" if i < len(users)-1 else "\n")
        yield '  ]\n'
        
        yield "}"

    db = next(get_db()) # Get session
    return StreamingResponse(
        iter_json(db),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    raise HTTPException(status_code=501, detail="File-based restore not supported in production (Postgres Only)")

# --- Google Drive Backup (Super Admin) ---

@router.get("/backup/google-status")
def get_google_drive_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "google_refresh_token_super_admin").first()
    
    # Fetch status
    last_status = db.query(models.SystemSetting).filter(models.SystemSetting.key == "backup_last_status").first()
    last_message = db.query(models.SystemSetting).filter(models.SystemSetting.key == "backup_last_message").first()
    last_run = db.query(models.SystemSetting).filter(models.SystemSetting.key == "backup_last_run").first()

    return {
        "connected": bool(setting and setting.value),
        "last_backup": {
            "status": last_status.value if last_status else None,
            "message": last_message.value if last_message else None,
            "date": last_run.value if last_run else None
        }
    }

@router.get("/backup/google-auth")
def get_google_auth_url(
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Pass state='super_admin' to identify this flow in the callback
    drive_client = get_drive_client()
    auth_url = drive_client.get_auth_url(state="super_admin")
    return {"url": auth_url}

@router.post("/backup/google-upload", status_code=202)
def upload_to_google_drive(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    # 1. Check if Google Drive is connected
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "google_refresh_token_super_admin").first()
    if not setting or not setting.value:
        raise HTTPException(status_code=400, detail="Google Drive not connected. Please connect first.")

    refresh_token = setting.value

    # 2. Check pg_dump availability (Fast check)
    try:
        import subprocess
        check_process = subprocess.run(["which", "pg_dump"], capture_output=True, timeout=5)
        if check_process.returncode != 0:
            raise HTTPException(status_code=503, detail="System tools (pg_dump) are initializing. Please wait 2 minutes and try again.")
    except FileNotFoundError:
        # On Windows or systems without 'which', try a different approach
        try:
            import shutil
            if not shutil.which("pg_dump"):
                raise HTTPException(status_code=503, detail="System tools (pg_dump) are not available on this system.")
        except:
            # If shutil.which is also not available, assume tools are not available
            raise HTTPException(status_code=503, detail="System tools (pg_dump) are not available on this system.")

    # 3. Get DB URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL configuration missing")

    # 4. Dispatch Background Task
    from ..services.backup_service import run_backup_task
    background_tasks.add_task(run_backup_task, refresh_token, db_url)

    return {
        "success": True,
        "message": "Backup started in background. Please check Google Drive in a few minutes.",
        "status": "processing"
    }

@router.delete("/backup/google-auth")
def disconnect_google_drive(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Disconnect the Google Drive account."""
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Find and delete the token setting
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "google_refresh_token_super_admin").first()
    if setting:
        db.delete(setting)
        db.commit()
        return {"success": True, "message": "Google Drive disconnected successfully"}
    else:
        # If already undefined, considering it success
        return {"success": True, "message": "Google Drive was not connected"}


# --- Tenant Management Endpoints ---

@router.delete("/tenants/{tenant_id}")
def archive_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from ..services.admin_service import AdminService
    service = AdminService(db)
    tenant = service.archive_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return {"success": True, "message": "Tenant archived successfully"}

@router.post("/tenants/{tenant_id}/restore")
def restore_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from ..services.admin_service import AdminService
    service = AdminService(db)
    tenant = service.restore_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return {"success": True, "message": "Tenant restored successfully"}

@router.delete("/tenants/{tenant_id}/permanent")
def permanently_delete_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from ..services.admin_service import AdminService
    service = AdminService(db)
    try:
        success = service.permanently_delete_tenant(tenant_id)
        if not success:
            raise HTTPException(status_code=404, detail="Tenant not found")
    except Exception as e:
        import logging
        logging.error(f"Delete failed: {e}")
        raise HTTPException(status_code=400, detail=f"Cannot delete tenant: {str(e)}")
    
    return {"success": True, "message": "Tenant permanently deleted"}

@router.post("/tenants/{tenant_id}/assign-plan")
def assign_tenant_plan(
    tenant_id: int,
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from ..services.admin_service import AdminService
    service = AdminService(db)
    
    # Get Plan Name/Object
    plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    tenant = service.update_tenant(tenant_id, plan=plan.name, plan_id=plan.id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return {"success": True, "message": "Plan updated successfully", "tenant": tenant.name}


# --- User Management (Super Admin) ---
@router.get("/tenants/{tenant_id}/users")
def get_tenant_users(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all users for a specific tenant (Super Admin only)."""
    print(f"[DEBUG get_tenant_users] Called with tenant_id={tenant_id}, current_user.role={current_user.role}")
    
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check if tenant exists first
    tenant = db.query(models.Tenant).filter(
        models.Tenant.id == tenant_id,
        models.Tenant.is_deleted == False
    ).first()

    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant with ID {tenant_id} not found or has been deleted")

    users = db.query(models.User).filter(
        models.User.tenant_id == tenant_id,
        models.User.is_deleted == False
    ).all()

    print(f"[DEBUG get_tenant_users] Found {len(users)} users for tenant {tenant_id}")
    for u in users:
        print(f"[DEBUG get_tenant_users] User id={u.id}, username='{u.username}', email='{u.email}'")

    result = {
        "users": [
            {
                "id": u.id,
                "username": u.username or (u.email.split('@')[0] if u.email else f"User#{u.id}"),
                "email": u.email or "no-email",
                "role": u.role,
                "is_active": u.is_active,
                "failed_login_attempts": u.failed_login_attempts or 0,
                "account_locked_until": str(u.account_locked_until) if u.account_locked_until else None
            }
            for u in users
        ]
    }
    print(f"[DEBUG get_tenant_users] Returning: {result}")
    return result


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    password_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Reset password for any user (Super Admin only)."""
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    new_password = password_data.get("new_password")
    if not new_password or len(new_password) < 6:
        raise HTTPException(
            status_code=400, 
            detail="Password must be at least 6 characters"
        )
    
    # Get user
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update password
    user.hashed_password = get_password_hash(new_password)
    
    # Reset login attempts and unlock account
    user.failed_login_attempts = 0
    user.account_locked_until = None
    user.last_failed_login = None
    
    # Ensure account is active
    user.is_active = True
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Password reset successfully for user: {user.username}",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "tenant_id": user.tenant_id
        }
    }

