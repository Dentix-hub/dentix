from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List
from datetime import datetime, timezone
import os

from backend import models, schemas
from backend.database import get_db
from backend.routers.auth.dependencies import get_current_user
from backend.constants import ROLES
from backend.utils.audit_logger import log_admin_action
from backend.services.cache_service import cached

router = APIRouter(
    prefix="/admin",
    tags=["System Admin"],
    responses={404: {"description": "Not found"}},
)


# Dependency
def require_super_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


# --- Dashboard Stats ---
@router.get("/stats", response_model=schemas.AdminDashboardStats)
def get_admin_dashboard_stats(
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Get admin dashboard statistics (Cached 5 mins)."""
    return _get_admin_stats_logic(db)

@cached(key_prefix="admin_dashboard_stats", expire=300)
def _get_admin_stats_logic(db: Session):
    total_tenants = db.query(models.Tenant).count()
    active_tenants = (
        db.query(models.Tenant).filter(models.Tenant.is_active == True).count()
    )
    expired_tenants = (
        db.query(models.Tenant)
        .filter(models.Tenant.subscription_end_date < datetime.now(timezone.utc))
        .count()
    )

    total_revenue = db.query(func.sum(models.SubscriptionPayment.amount)).scalar() or 0

    recent_payments = (
        db.query(models.SubscriptionPayment)
        .order_by(models.SubscriptionPayment.payment_date.desc())
        .limit(10)
        .all()
    )

    plan_distribution = {}
    plans = (
        db.query(models.Tenant.plan, func.count(models.Tenant.id))
        .group_by(models.Tenant.plan)
        .all()
    )
    for plan_name, count in plans:
        plan_distribution[plan_name or "trial"] = count

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "expired_tenants": expired_tenants,
        "total_revenue": float(total_revenue),
        "monthly_revenue": {},
        "plan_distribution": plan_distribution,
        "recent_payments": recent_payments,
    }


# --- Audit Logs ---
@router.get("/audit-logs", response_model=List[schemas.AuditLog])
def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    tenant_id: int = None,
    user_id: int = None,
    action: str = None,
    start_date: str = None,
    end_date: str = None,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    query = db.query(models.AuditLog)

    if tenant_id:
        query = query.filter(models.AuditLog.tenant_id == tenant_id)
    if user_id:
        query = query.filter(models.AuditLog.performed_by_id == user_id)
    if action:
        query = query.filter(models.AuditLog.action == action)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(models.AuditLog.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        from datetime import timedelta

        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(models.AuditLog.created_at < end_dt)
        except ValueError:
            pass

    return (
        query.order_by(models.AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


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
    return {
        "message": f"User {'enabled' if new_status else 'disabled'} successfully",
        "is_active": new_status,
    }


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


# --- Backup & Google Drive ---
def get_drive_client():
    from backend.main import drive_client

    return drive_client


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

    return {
        "connected": bool(setting and setting.value),
        "last_backup": {
            "status": last_status.value if last_status else None,
            "message": last_message.value if last_message else None,
            "date": last_run.value if last_run else None,
        },
    }


@router.get("/system/backup/google-auth")
def get_system_google_auth_url(
    current_user: models.User = Depends(require_super_admin),
):
    auth_url = get_drive_client().get_auth_url(state="super_admin")
    return {"url": auth_url}


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

    from backend.services.backup_service import run_backup_task

    background_tasks.add_task(run_backup_task, refresh_token, db_url)

    return {
        "success": True,
        "message": "Backup started in background.",
        "status": "processing",
    }


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
        return {"success": True, "message": "Google Drive disconnected successfully"}
    else:
        return {"success": True, "message": "Google Drive was not connected"}


@router.get("/backup")
def download_backup(
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Download system JSON backup."""
    from fastapi.responses import StreamingResponse
    import json

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


# --- System Logs ---
@router.get("/system/logs", response_model=List[schemas.SystemError])
def get_system_logs(
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Retrieve system error logs."""
    return (
        db.query(models.SystemError)
        .order_by(models.SystemError.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
