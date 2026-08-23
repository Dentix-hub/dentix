"""
Settings Router
Handles backup and settings endpoints.
"""

import logging
import os
import shutil
import tempfile
import uuid
import asyncio
from datetime import datetime, timedelta, timezone

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
from starlette.background import BackgroundTask
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .. import schemas, database, models
from ..auth import ALGORITHM, SECRET_KEY
from ..core.permissions import Permission, Role, require_permission
from ..core.response import success_response, StandardResponse
from ..services.backup_service import (
    build_pg_dump_command,
    build_psql_command,
    create_secure_temp_file,
    run_backup_task,
)
from ..services.import_service import restore_tenant_from_json
from ..services.export_service import export_tenant_to_json
from ..services.secret_service import (
    GOOGLE_SUPER_ADMIN_TOKEN_KEY,
    encrypt_secret,
)
from .auth import get_async_db

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency with main.py
_drive_client = None
_BACKUP_OAUTH_STATE_TTL_MINUTES = 10
_BACKUP_OAUTH_STATE_PURPOSE = "google_drive_backup"


def get_drive_client():
    """Get drive client via lazy initialization."""
    global _drive_client
    if _drive_client is None:
        from ..main import drive_client

        _drive_client = drive_client
    return _drive_client


def _create_backup_oauth_state(current_user: schemas.User) -> str:
    """Create a short-lived signed OAuth state bound to one Dentix identity."""
    payload = {
        "purpose": _BACKUP_OAUTH_STATE_PURPOSE,
        "user_id": current_user.id,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id,
        "nonce": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_BACKUP_OAUTH_STATE_TTL_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_backup_oauth_state(state: str) -> dict:
    """Validate callback state before exchanging or persisting OAuth tokens."""
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")
    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from exc

    if payload.get("purpose") != _BACKUP_OAUTH_STATE_PURPOSE:
        raise HTTPException(status_code=400, detail="Invalid OAuth state purpose")
    if not payload.get("user_id") or not payload.get("nonce"):
        raise HTTPException(status_code=400, detail="Invalid OAuth state payload")
    return payload


router = APIRouter(prefix="/settings", tags=["Settings"])


def _delete_temp_file(filepath: str) -> None:
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        logger.exception("Failed to remove temporary backup file")


@router.get("/backup/status", response_model=StandardResponse[dict])
async def get_backup_status(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Get backup status for the current tenant."""
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
async def get_backup_auth_url(
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Get a Google Drive authorization URL with signed CSRF state."""
    if current_user.role != Role.SUPER_ADMIN.value and not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant assigned")
    state = _create_backup_oauth_state(current_user)
    auth_url = get_drive_client().get_auth_url(state=state)
    return success_response(data={"url": auth_url}, message="Redirecting...")


@router.post("/backup/callback", response_model=StandardResponse[dict])
async def backup_auth_callback_post(
    code: str = Form(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Handle the authenticated frontend OAuth callback for a tenant."""
    if not current_user.tenant:
        raise HTTPException(status_code=400, detail="User has no tenant assigned")
    try:
        token_data = get_drive_client().fetch_token(code=code)
        if token_data.get("refresh_token"):
            current_user.tenant.google_refresh_token = token_data["refresh_token"]
            await db.commit()
            return success_response(message="تم ربط Google Drive بنجاح")
        return success_response(
            success=False,
            message="لم يتم استلام refresh token. يرجى إعادة المحاولة.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Auth Error: %s", type(e).__name__, exc_info=True)
        raise HTTPException(status_code=400, detail="Google Drive authorization failed")


@router.get("/backup/callback")
async def backup_auth_callback_get(
    code: str,
    state: str = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Handle Google OAuth redirect using signed, identity-bound state."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    destination = "/settings"
    try:
        state_payload = _decode_backup_oauth_state(state)
        user_id = int(state_payload["user_id"])
        state_role = state_payload.get("role")
        state_tenant_id = state_payload.get("tenant_id")
        if state_role == Role.SUPER_ADMIN.value:
            destination = "/admin/system"

        stmt_user = (
            select(models.User)
            .where(models.User.id == user_id)
            .options(selectinload(models.User.tenant))
        )
        user = (await db.execute(stmt_user)).scalars().first()
        if not user:
            raise HTTPException(status_code=400, detail="OAuth user no longer exists")
        if user.role != state_role or user.tenant_id != state_tenant_id:
            raise HTTPException(status_code=400, detail="OAuth identity context changed")

        token_data = get_drive_client().fetch_token(code=code)
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            return RedirectResponse(
                url=f"{frontend_url}{destination}?backup_status=no_refresh_token"
            )

        if user.role == Role.SUPER_ADMIN.value:
            setting = (
                await db.execute(
                    select(models.SystemSetting).where(
                        models.SystemSetting.key == GOOGLE_SUPER_ADMIN_TOKEN_KEY
                    )
                )
            ).scalars().first()
            if not setting:
                setting = models.SystemSetting(
                    key=GOOGLE_SUPER_ADMIN_TOKEN_KEY,
                    value=encrypt_secret(refresh_token),
                )
                db.add(setting)
            else:
                setting.value = encrypt_secret(refresh_token)
        elif user.tenant:
            user.tenant.google_refresh_token = refresh_token
        else:
            raise HTTPException(status_code=400, detail="OAuth user has no tenant")

        await db.commit()
        return RedirectResponse(url=f"{frontend_url}{destination}?backup_status=success")
    except HTTPException as exc:
        logger.warning("Rejected backup OAuth callback: %s", exc.detail)
        return RedirectResponse(
            url=f"{frontend_url}{destination}?backup_status=invalid_state"
        )
    except Exception:
        logger.exception("Auth Callback Error", exc_info=True)
        return RedirectResponse(
            url=f"{frontend_url}{destination}?backup_status=error"
        )


@router.post("/backup/now", response_model=StandardResponse[dict])
async def trigger_manual_backup(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Trigger a manual tenant backup to Google Drive."""
    if not current_user.tenant:
        raise HTTPException(status_code=400, detail="User has no tenant assigned")

    tenant = current_user.tenant
    if not tenant.google_refresh_token:
        raise HTTPException(
            status_code=400, detail="Google Drive not connected for this clinic"
        )

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(
            status_code=500, detail="DATABASE_URL configuration missing"
        )

    background_tasks.add_task(
        run_backup_task, tenant.google_refresh_token, db_url, tenant.id, tenant.name
    )

    return success_response(
        message="Manual backup started in background. Please check Google Drive in a few minutes.",
    )


@router.put("/backup/schedule", response_model=StandardResponse[dict])
async def update_backup_schedule(
    frequency: str = Form(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Update tenant backup schedule frequency.

    HIGH-12 honesty contract: no persistent scheduler consumes this value yet,
    so only 'off' is accepted. Promising automated backups that would never
    run is a silent data-loss risk; re-enable schedules when a durable
    scheduler with due-at/status/heartbeat exists.
    """
    tenant = current_user.tenant
    if not tenant:
        raise HTTPException(status_code=400, detail="User has no tenant assigned")

    normalized = (frequency or "").strip().lower()
    if normalized not in {"off", "daily", "weekly", "monthly"}:
        raise HTTPException(status_code=400, detail="Invalid backup frequency")
    if normalized != "off":
        raise HTTPException(
            status_code=501,
            detail="النسخ الاحتياطي التلقائي غير مفعّل بعد. استخدم النسخ اليدوي حتى إطلاق المجدول.",
        )

    tenant.backup_frequency = "off"
    await db.commit()

    return success_response(
        data={"frequency": "off"},
        message="النسخ الاحتياطي التلقائي متوقف؛ يعتمد النظام حالياً على النسخ اليدوي.",
    )


@router.get("/backup/download")
async def download_backup(
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Download a full database backup. Restricted to Super Admin."""
    if current_user.role != Role.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can download full SQL backup. Use /settings/backup/export for tenant JSON backup.",
        )

    db_url = database.SQLALCHEMY_DATABASE_URL

    if "sqlite" in db_url:
        db_path = db_url.replace("sqlite:///", "")
        if not os.path.exists(db_path):
            if not db_path.startswith("/"):
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

    elif "postgres" in db_url:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backup_{timestamp}.sql"
            filepath = create_secure_temp_file(prefix="dentix_download_", suffix=".sql")
            command, process_env = build_pg_dump_command(db_url, filepath)

            process = await asyncio.create_subprocess_exec(
                *command,
                env=process_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
            except TimeoutError:
                process.kill()
                await process.communicate()
                raise RuntimeError("Database backup timed out")

            if process.returncode != 0:
                logger.error("pg_dump failed: %s", stderr.decode(errors="replace")[:1000])
                raise RuntimeError("Database backup command failed")

            return FileResponse(
                path=filepath,
                filename=filename,
                media_type="application/sql",
                background=BackgroundTask(_delete_temp_file, filepath),
            )
        except Exception as exc:
            if "filepath" in locals():
                _delete_temp_file(filepath)
            logger.exception("Full database backup download failed")
            raise HTTPException(
                status_code=500, detail="Database backup could not be created"
            ) from exc

    raise HTTPException(status_code=500, detail="Unsupported database type")


@router.post("/backup/upload", response_model=StandardResponse[dict])
async def upload_backup(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Restore tenant JSON backups or Super Admin SQL backups."""
    db_url = database.SQLALCHEMY_DATABASE_URL
    filename = file.filename.lower() if file.filename else ""

    if filename.endswith(".json"):
        if not current_user.tenant:
            raise HTTPException(
                status_code=400, detail="No tenant associated with user"
            )

        content = await file.read()
        json_content = content.decode("utf-8")
        result = await restore_tenant_from_json(db, current_user.tenant.id, json_content)

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

    if filename.endswith(".sql"):
        if current_user.role != Role.SUPER_ADMIN.value:
            raise HTTPException(
                status_code=403,
                detail="Only Super Admin can restore SQL backups. Use JSON backup for tenant restore.",
            )

        if "postgres" in db_url:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".sql") as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            try:
                command, process_env = build_psql_command(db_url, tmp_path)
                process = await asyncio.create_subprocess_exec(
                    *command,
                    env=process_env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    _, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
                except TimeoutError:
                    process.kill()
                    await process.communicate()
                    raise HTTPException(status_code=504, detail="Database restore timed out")

                if process.returncode != 0:
                    logger.error(
                        "psql restore failed: %s",
                        stderr.decode(errors="replace")[:1000],
                    )
                    raise HTTPException(
                        status_code=500, detail="Database restore failed"
                    )

                return success_response(message="Database restored successfully from SQL backup.")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

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
async def export_tenant_backup(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Export only the current tenant's data as JSON."""
    if not current_user.tenant:
        raise HTTPException(status_code=400, detail="No tenant associated with user")

    tenant_id = current_user.tenant.id
    tenant_name = current_user.tenant.name or f"tenant_{tenant_id}"
    json_content = await export_tenant_to_json(db, tenant_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{tenant_name}_backup_{timestamp}.json"

    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tenant", response_model=StandardResponse[schemas.Tenant])
async def get_tenant_settings(
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Get current tenant settings."""
    if not current_user.tenant:
        return success_response(data=None)
    return success_response(data=current_user.tenant)


@router.get("/features", response_model=StandardResponse[dict])
async def get_tenant_features(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Get active feature keys for the current clinic."""
    if not current_user.tenant:
        return success_response(data={"features": []})

    stmt_features = select(models.TenantFeature).filter(
        models.TenantFeature.tenant_id == current_user.tenant.id,
        models.TenantFeature.is_enabled == True,  # noqa: E712
    )
    res_features = await db.execute(stmt_features)
    tenant_features = res_features.scalars().all()

    feature_keys = [f.feature_key for f in tenant_features]
    return success_response(data={"features": feature_keys})


@router.put("/tenant", response_model=StandardResponse[schemas.Tenant])
async def update_tenant_settings(
    config: schemas.TenantUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Update tenant settings."""
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

    await db.commit()
    await db.refresh(tenant)
    return success_response(data=tenant, message="Tenant settings updated")
