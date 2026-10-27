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
    Request,
)
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
import re
from urllib.parse import quote
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
from ..services.export_service import export_tenant_to_json
from ..services.excel_export_service import export_tenant_to_excel
from ..utils.audit_logger import log_admin_action
from ..services.secret_service import (
    GOOGLE_SUPER_ADMIN_TOKEN_KEY,
    encrypt_secret,
)
from .auth import get_async_db
from backend.routers.auth.dependencies import get_current_user
from backend.services.feature_service import FeatureFlagService
from backend.core.config import is_clinical_treatment_plans_enabled

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
    is_connected = bool(tenant.google_refresh_token and tenant.google_connection_status == "connected")

    return success_response(
        data={
            "connected": is_connected,
            "connection_status": tenant.google_connection_status,
            "account_email": tenant.google_account_email,
            "frequency": tenant.backup_frequency,
            "last_backup": tenant.last_backup_at,
        },
        message="Google Drive connected" if is_connected else "Not connected",
    )


@router.get("/backup/auth", response_model=StandardResponse[dict])
async def get_backup_auth_url(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Use browser-bound attempts for clinics; retain the platform flow."""
    if current_user.role != Role.SUPER_ADMIN.value:
        from backend.routers.clinic_google import start_connection
        return await start_connection(request=request, response=response, db=db, user=current_user)
    state = _create_backup_oauth_state(current_user)
    auth_url = get_drive_client().get_auth_url(state=state)
    return success_response(data={"url": auth_url}, message="Redirecting...")


@router.post("/backup/callback", response_model=StandardResponse[dict])
async def backup_auth_callback_post(
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Old code-only callbacks cannot prove browser-bound OAuth state."""
    raise HTTPException(status_code=409, detail="يرجى إعادة ربط Google باستخدام التطبيق المحدّث")


@router.get("/backup/callback")
async def backup_auth_callback_get(
    request: Request,
    code: str,
    state: str = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Dispatch opaque clinic state; retain signed platform callbacks."""
    if state and "." not in state:
        from backend.routers.clinic_google import connection_callback
        return await connection_callback(request=request, code=code, state=state)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    destination = "/settings"
    try:
        state_payload = _decode_backup_oauth_state(state)
        user_id = int(state_payload["user_id"])
        state_role = state_payload.get("role")
        state_tenant_id = state_payload.get("tenant_id")
        if state_role != Role.SUPER_ADMIN.value:
            raise HTTPException(status_code=400, detail="Clinic OAuth requires browser-bound state")
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

        # Commit existing read transaction so connection is not held across external HTTP fetch
        await db.commit()

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
    """Download a full database backup over HTTP is permanently disabled."""
    raise HTTPException(
        status_code=410,
        detail="Raw SQL and full database downloads over HTTP have been permanently disabled for security. Use /api/v1/settings/backup/export for clinic-scoped JSON export or guarded CLI tools.",
    )


@router.post("/backup/upload", response_model=StandardResponse[dict])
async def upload_backup(
    file: UploadFile = File(...),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Old clients must use the reviewed preview and confirmation flow."""
    if (file.filename or "").lower().endswith(".sql"):
        raise HTTPException(status_code=410, detail="Raw SQL restore over HTTP is permanently disabled for security.")
    raise HTTPException(
        status_code=409,
        detail="حدّث التطبيق لمعاينة النسخة وتأكيد الاستعادة قبل استبدال بيانات العيادة",
    )


def build_content_disposition(ascii_filename: str, utf8_filename: str) -> str:
    """Build RFC 5987 / RFC 6266 compliant Content-Disposition header with ASCII fallback."""
    safe_ascii = re.sub(r"[^a-zA-Z0-9_.-]+", "_", ascii_filename).strip("_") or "backup"
    encoded_utf8 = quote(utf8_filename, safe="")
    return f"attachment; filename=\"{safe_ascii}\"; filename*=UTF-8''{encoded_utf8}"


@router.get("/backup/export")
async def export_tenant_backup(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Export only the current tenant's data as JSON."""
    if not current_user.tenant:
        raise HTTPException(status_code=400, detail="No tenant associated with user")

    tenant_id = current_user.tenant.id
    try:
        tenant_name = current_user.tenant.name or f"tenant_{tenant_id}"
        json_content = await export_tenant_to_json(db, tenant_id)
        # Release DB connection immediately before formatting response
        await db.close()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", tenant_name.strip()).lower().strip("_") or f"tenant_{tenant_id}"
        ascii_filename = f"{slug}_backup_{timestamp}.json"
        utf8_filename = f"{tenant_name}_backup_{timestamp}.json"
        content_disposition = build_content_disposition(ascii_filename, utf8_filename)

        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": content_disposition},
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed exporting tenant backup JSON for tenant_id=%s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to export tenant backup")


@router.get("/backup/export-xlsx")
async def export_tenant_backup_xlsx(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Export the current tenant's data as an Excel (.xlsx) workbook."""
    tenant_id = getattr(current_user, "tenant_id", None) or (current_user.tenant.id if getattr(current_user, "tenant", None) else None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant associated with user")

    try:
        tenant_name = None
        if getattr(current_user, "tenant", None) and current_user.tenant.name:
            tenant_name = current_user.tenant.name
        else:
            tenant = await db.get(models.Tenant, tenant_id)
            if tenant and tenant.name:
                tenant_name = tenant.name
            else:
                tenant_name = f"tenant_{tenant_id}"

        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", tenant_name.strip()).lower().strip("_") or f"tenant_{tenant_id}"
        today = datetime.now().strftime("%Y-%m-%d")
        ascii_filename = f"dentix-backup-{slug}-{today}.xlsx"
        utf8_filename = f"dentix-backup-{tenant_name}-{today}.xlsx"
        content_disposition = build_content_disposition(ascii_filename, utf8_filename)

        buffer = await export_tenant_to_excel(db, tenant_id)

        log_admin_action(
            db,
            admin_user=current_user,
            action="export",
            entity_type="tenant_backup_xlsx",
            entity_id=tenant_id,
            details=f"Exported tenant backup to Excel (.xlsx): {ascii_filename}",
            tenant_id=tenant_id,
        )
        await db.commit()
        # Release DB connection before streaming so file transfer doesn't hold connection
        await db.close()

        def iterfile():
            while chunk := buffer.read(65536):
                yield chunk

        return StreamingResponse(
            iterfile(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": content_disposition},
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed exporting tenant backup XLSX for tenant_id=%s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to export tenant backup to Excel")


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
    current_user: models.User = Depends(get_current_user),
):
    """Get active feature keys for the current clinic."""
    tenant_id = current_user.tenant_id if current_user else None
    if not tenant_id:
        return success_response(data={"features": []})

    stmt_features = select(models.TenantFeature).filter(
        models.TenantFeature.tenant_id == tenant_id,
        models.TenantFeature.is_enabled == True,  # noqa: E712
    )
    res_features = await db.execute(stmt_features)
    tenant_features = res_features.scalars().all()

    feature_keys = set(f.feature_key for f in tenant_features)
    if is_clinical_treatment_plans_enabled() or await FeatureFlagService.is_feature_enabled(
        db, "clinical_treatment_plans", tenant_id
    ):
        feature_keys.add("clinical_treatment_plans")

    return success_response(data={"features": sorted(list(feature_keys))})



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
