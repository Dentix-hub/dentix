"""
Settings Router
Handles backup and settings endpoints.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from .. import schemas, database, models
from ..core.permissions import Permission, Role, require_permission
from ..core.response import success_response, StandardResponse
from ..services.backup_service import run_backup_task
from ..services.import_service import restore_tenant_from_json
from ..services.export_service import export_tenant_to_json
from .auth import get_db

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency with main.py
_drive_client = None


def get_drive_client():
    """Get drive client via lazy initialization."""
    global _drive_client
    if _drive_client is None:
        from ..main import drive_client

        _drive_client = drive_client
    return _drive_client


router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/backup/status", response_model=StandardResponse[dict])
def get_backup_status(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Get backup status for the current tenant.
    """
    if not current_user.tenant:
        return success_response(
            data={
                "connected": False,
                "frequency": "weekly",
                "last_backup": None,
            },
            message="User has no tenant assigned",
        )

    tenant = current_user.tenant
    is_connected = bool(tenant.google_refresh_token)

    return success_response(
        data={
            "connected": is_connected,
            "frequency": tenant.backup_frequency,
            "last_backup": tenant.last_backup_at,
        },
        message="Google Drive connected" if is_connected else "Not connected",
    )


@router.get("/backup/auth", response_model=StandardResponse[dict])
def get_backup_auth_url(
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Get Google Drive authentication URL.
    Encodes user_id in state so callback can identify the user.
    """
    state = f"user_{current_user.id}"
    auth_url = get_drive_client().get_auth_url(state=state)
    return success_response(data={"url": auth_url}, message="Redirecting...")


@router.post("/backup/callback", response_model=StandardResponse[dict])
def backup_auth_callback_post(
    code: str = Form(...),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Handle Google OAuth callback (POST from frontend).
    Exchanges code for refresh token and saves it to Tenant.
    """
    try:
        token_data = get_drive_client().fetch_token(code=code)

        # Save refresh token to tenant
        tenant = current_user.tenant
        if token_data.get("refresh_token"):
            tenant.google_refresh_token = token_data["refresh_token"]
            db.commit()
            return success_response(message="تم ربط Google Drive بنجاح")
        else:
            return success_response(
                success=False,
                message="لم يتم استلام refresh token. يرجى إعادة المحاولة.",
            )

    except Exception as e:
        logger.error("Auth Error: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/backup/callback")
def backup_auth_callback_get(
    code: str,
    state: str = None,
    db: Session = Depends(get_db),
):
    """
    Handle Google OAuth callback (GET redirect from Google).
    Decodes user_id from state instead of requiring auth token.
    """
    try:
        # 1. Exchange Code
        logger.debug("Processing OAuth Callback code=%.10s... state=%s", code, state)
        token_data = get_drive_client().fetch_token(code=code)

        status = "success"
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            logger.warning("No refresh token in OAuth response.")
            status = "no_refresh_token"

        # 2. Decode user from state and save token
        if status == "success" and state:
            if state == "super_admin":
                setting = (
                    db.query(models.SystemSetting)
                    .filter(
                        models.SystemSetting.key == "google_refresh_token_super_admin"
                    )
                    .first()
                )
                if not setting:
                    setting = models.SystemSetting(
                        key="google_refresh_token_super_admin", value=refresh_token
                    )
                    db.add(setting)
                else:
                    setting.value = refresh_token
                db.commit()
            elif state.startswith("user_"):
                try:
                    user_id = int(state.split("_")[1])
                    user = (
                        db.query(models.User).filter(models.User.id == user_id).first()
                    )
                    if user and user.tenant:
                        user.tenant.google_refresh_token = refresh_token
                        db.commit()
                    elif user and user.role == "super_admin":
                        setting = (
                            db.query(models.SystemSetting)
                            .filter(
                                models.SystemSetting.key
                                == "google_refresh_token_super_admin"
                            )
                            .first()
                        )
                        if not setting:
                            setting = models.SystemSetting(
                                key="google_refresh_token_super_admin",
                                value=refresh_token,
                            )
                            db.add(setting)
                        else:
                            setting.value = refresh_token
                        db.commit()
                    else:
                        status = "no_tenant"
                except (ValueError, IndexError):
                    status = "invalid_state"

        # 3. Redirect back to frontend
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

        if state == "super_admin":
            target_url = f"{frontend_url}/admin/system?backup_status={status}"
        else:
            target_url = f"{frontend_url}/settings?backup_status={status}"

        return RedirectResponse(url=target_url)

    except Exception as e:
        logger.exception("Auth Callback Error", exc_info=True)
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=f"{frontend_url}/settings?error={str(e)}")


@router.post("/backup/now", response_model=StandardResponse[dict])
def trigger_manual_backup(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Trigger a manual backup to Google Drive.
    Uses JSON export for tenant data.
    """
    if not current_user.tenant:
        raise HTTPException(status_code=400, detail="User has no tenant assigned")

    # Check if Google Drive is connected for this tenant
    tenant = current_user.tenant
    if not tenant.google_refresh_token:
        raise HTTPException(
            status_code=400, detail="Google Drive not connected for this clinic"
        )

    # Get DB URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(
            status_code=500, detail="DATABASE_URL configuration missing"
        )

    # Dispatch background task for backup with tenant info
    background_tasks.add_task(
        run_backup_task, tenant.google_refresh_token, db_url, tenant.id, tenant.name
    )

    return success_response(
        message="Manual backup started in background. Please check Google Drive in a few minutes.",
    )


@router.put("/backup/schedule", response_model=StandardResponse[dict])
def update_backup_schedule(
    frequency: str = Form(...),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Update backup schedule frequency.
    """
    tenant = current_user.tenant
    tenant.backup_frequency = frequency
    db.commit()

    return success_response(
        data={"frequency": frequency},
        message=f"تم تحديث جدول النسخ الاحتياطي إلى: {frequency}",
    )


@router.get("/backup/download")
def download_backup(
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Download full database backup (SQL format).
    Restricted to Super Admin only.
    For tenant backup, use /backup/export instead.
    """
    # Only Super Admin can download full SQL backup
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can download full SQL backup. Use /settings/backup/export for tenant JSON backup.",
        )

    db_url = database.SQLALCHEMY_DATABASE_URL

    # 1. SQLite Handling
    if "sqlite" in db_url:
        # Extract path from URL (sqlite:///./clinic.db -> ./clinic.db)
        db_path = db_url.replace("sqlite:///", "")
        if not os.path.exists(db_path):
            # Fallback for some OS paths
            if db_path.startswith("/"):
                db_path = db_path  # Absolute path
            else:
                db_path = os.path.join(database.BACKEND_DIR, db_path.replace("./", ""))

        if not os.path.exists(db_path):
            raise HTTPException(
                status_code=404, detail="Database file not found on server"
            )

        return FileResponse(
            path=db_path,
            filename="clinic_backup.db",
            media_type="application/octet-stream",
        )

    # 2. PostgreSQL Handling
    elif "postgres" in db_url:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backup_{timestamp}.sql"
            filepath = os.path.join("/tmp", filename)

            # Normalize URL
            dump_url = db_url.replace("postgresql://", "postgres://", 1)

            # Execute pg_dump
            process = subprocess.Popen(
                ["pg_dump", "--dbname", dump_url, "-f", filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate(timeout=60)

            if process.returncode != 0:
                raise Exception(f"PG dump failed: {stderr.decode()}")

            return FileResponse(
                path=filepath,
                filename=filename,
                media_type="application/sql",
                background=None,  # TODO: Add cleanup task if desired
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    else:
        raise HTTPException(status_code=500, detail="Unsupported database type")


@router.post("/backup/upload", response_model=StandardResponse[dict])
async def upload_backup(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Restore database from backup.
    - Super Admin: Full SQL restore (pg_dump format)
    - Tenant Admin: JSON restore (tenant data only)
    """
    db_url = database.SQLALCHEMY_DATABASE_URL

    # Check file extension to determine restore type
    filename = file.filename.lower() if file.filename else ""

    # JSON restore for tenants
    if filename.endswith(".json"):
        if not current_user.tenant:
            raise HTTPException(
                status_code=400, detail="No tenant associated with user"
            )

        # Read file content
        content = await file.read()
        json_content = content.decode("utf-8")

        result = restore_tenant_from_json(db, current_user.tenant.id, json_content)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return success_response(
            data={
                "deleted": result["deleted"],
                "imported": result["imported"],
                "backup_date": result["backup_date"],
            },
            message="Tenant data restored successfully",
        )

    # SQL restore for Super Admin only
    if filename.endswith(".sql"):
        if current_user.role != Role.SUPER_ADMIN.value:
            raise HTTPException(
                status_code=403,
                detail="Only Super Admin can restore SQL backups. Use JSON backup for tenant restore.",
            )

        # PostgreSQL restore using psql
        if "postgres" in db_url:
            # Save uploaded file to temp
            with tempfile.NamedTemporaryFile(delete=False, suffix=".sql") as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            try:
                # Normalize URL
                restore_url = db_url.replace("postgresql://", "postgres://", 1)

                # Execute psql to restore
                process = subprocess.Popen(
                    ["psql", restore_url, "-f", tmp_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = process.communicate(timeout=300)

                if process.returncode != 0:
                    error_msg = stderr.decode()[:500]
                    raise HTTPException(
                        status_code=500, detail=f"Restore failed: {error_msg}"
                    )

                return success_response(message="Database restored successfully from SQL backup.")
            finally:
                # Cleanup temp file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        # SQLite restore
        elif "sqlite" in db_url:
            db_path = db_url.replace("sqlite:///", "")

            temp_path = f"{db_path}.restore"
            content = await file.read()
            with open(temp_path, "wb") as buffer:
                buffer.write(content)

            try:
                backup_path = f"{db_path}.bak"
                if os.path.exists(backup_path):
                    os.remove(backup_path)

                shutil.copy(db_path, backup_path)
                shutil.move(temp_path, db_path)

                return success_response(
                    message="Backup restored successfully. Please restart server if needed."
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")

    raise HTTPException(
        status_code=400,
        detail="Unsupported file format. Use .json for tenant restore or .sql for full system restore.",
    )


@router.get("/backup/export")
def export_tenant_backup(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Export tenant data as JSON.
    This exports only the current tenant's data for backup purposes.
    """
    if not current_user.tenant:
        raise HTTPException(status_code=400, detail="No tenant associated with user")

    tenant_id = current_user.tenant.id
    tenant_name = current_user.tenant.name or f"tenant_{tenant_id}"

    json_content = export_tenant_to_json(db, tenant_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{tenant_name}_backup_{timestamp}.json"

    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tenant", response_model=StandardResponse[dict])
def get_tenant_settings(
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Get current tenant settings.
    """
    if not current_user.tenant:
        return success_response(data={})
    return success_response(data=current_user.tenant)


@router.put("/tenant", response_model=StandardResponse[dict])
def update_tenant_settings(
    config: schemas.TenantUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """
    Update tenant settings.
    """
    tenant = current_user.tenant
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if config.doctor_name is not None:
        tenant.doctor_name = config.doctor_name
    if config.doctor_title is not None:
        tenant.doctor_title = config.doctor_title
    if config.clinic_address is not None:
        tenant.clinic_address = config.clinic_address
    if config.clinic_phone is not None:
        tenant.clinic_phone = config.clinic_phone
    if config.print_header_image is not None:
        tenant.print_header_image = config.print_header_image
    if config.print_footer_image is not None:
        tenant.print_footer_image = config.print_footer_image

    db.commit()
    db.refresh(tenant)
    return success_response(data=tenant, message="Tenant settings updated")
