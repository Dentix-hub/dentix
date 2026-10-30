"""File Upload Router — Secure file upload and retrieval endpoints."""

import logging
import os

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import cloudinary
import cloudinary.uploader

from .. import crud, models, schemas
from .auth import get_async_db
from backend.core.permissions import Permission, require_permission
from backend.services.file_service import get_file_path, save_file_locally, validate_file
from backend.services.visibility_service import get_visibility_service

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

router = APIRouter(prefix="/upload", tags=["Uploads"])

_CLOUDINARY_ENV_KEYS = (
    "CLOUDINARY_CLOUD_NAME",
    "CLOUDINARY_API_KEY",
    "CLOUDINARY_API_SECRET",
)


def _cloudinary_is_fully_configured() -> bool:
    """Return true only when every credential required by Cloudinary exists."""
    return all((os.getenv(key) or "").strip() for key in _CLOUDINARY_ENV_KEYS)


def _store_attachment_content(
    *,
    file: UploadFile,
    safe_filename: str,
    tenant_id: int,
) -> str:
    """Persist one validated upload, falling back safely to local storage.

    A partial Cloudinary configuration must never turn an otherwise valid
    patient upload into a database 500. Likewise, a provider response without
    a usable ``secure_url`` is treated as a storage failure rather than being
    persisted as a NULL file path.
    """
    try:
        if not _cloudinary_is_fully_configured():
            raise RuntimeError("Cloudinary not fully configured")

        file.file.seek(0)
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder=f"smart_clinic_uploads/tenant_{tenant_id}",
            resource_type="auto",
            public_id=safe_filename.rsplit(".", 1)[0],
        )
        secure_url = (upload_result or {}).get("secure_url")
        if not secure_url or not str(secure_url).strip():
            raise RuntimeError("Cloudinary response missing secure_url")

        logger.info("Uploaded patient attachment to configured cloud storage")
        return str(secure_url)
    except Exception as exc:
        logger.warning(
            "Cloud storage failed/skipped (%s); using tenant-scoped local storage",
            type(exc).__name__,
        )
        return save_file_locally(
            file=file,
            safe_filename=safe_filename,
            tenant_id=tenant_id,
        )


async def _authorize_attachment_file_access(
    db: AsyncSession,
    current_user: schemas.User,
    file_path: str,
):
    """Resolve a persisted attachment and enforce patient-level visibility.

    Tenant membership alone is not sufficient for doctor-scoped clinics: two
    patients in the same tenant can have different visibility. Requiring a DB
    attachment record also prevents the authenticated file endpoint from being
    used as a generic tenant-directory file server.
    """
    stmt = (
        select(models.Attachment)
        .join(models.Patient, models.Attachment.patient_id == models.Patient.id)
        .where(
            models.Attachment.file_path == file_path,
            models.Patient.is_deleted == False,  # noqa: E712
        )
    )
    if current_user.role != "super_admin":
        stmt = stmt.where(models.Patient.tenant_id == current_user.tenant_id)

    attachment = (await db.execute(stmt)).scalars().first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    if current_user.role != "super_admin":
        visibility = get_visibility_service(db, current_user, current_user.tenant_id)
        if not await visibility.can_view_patient(attachment.patient_id):
            raise HTTPException(status_code=404, detail="Attachment not found")

    return attachment


@router.post("", response_model=schemas.Attachment)
async def upload_file(
    patient_id: int,
    file: UploadFile = File(...),
    note: str = Query(None),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_UPDATE)),
):
    visibility = get_visibility_service(db, current_user, current_user.tenant_id)
    if not await visibility.can_view_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    patient = await crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    safe_filename, validated_content_type = validate_file(file)
    tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == current_user.tenant_id))).scalar_one()
    if validated_content_type.startswith("image/") and tenant.google_connection_status in {"connected", "needs_reconnect"}:
        from backend.services.clinic_drive_provider import DriveFailure
        from backend.services.drive_image_operations import stage_image_upload
        from backend.services.drive_image_processing import ImageValidationError
        import uuid
        if tenant.google_connection_status != "connected":
            raise HTTPException(status_code=400, detail="يرجى إعادة ربط Google Drive قبل رفع الصورة")
        try:
            file.file.seek(0)
            content = file.file.read()
            return await stage_image_upload(db, tenant=tenant, user=current_user, patient_id=patient_id,
                filename=file.filename, mime=validated_content_type, note=note, content=content,
                request_key=idempotency_key or str(uuid.uuid4()))
        except (ValueError, ImageValidationError, DriveFailure) as exc:
            await db.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    file_path_db = _store_attachment_content(
        file=file,
        safe_filename=safe_filename,
        tenant_id=current_user.tenant_id,
    )

    attachment_create = schemas.AttachmentCreate(
        patient_id=patient_id,
        filename=file.filename,
        file_path=file_path_db,
        file_type=validated_content_type,
        note=note,
    )
    return await crud.create_attachment(db, attachment_create, current_user.tenant_id)


@router.get("/file/{file_path:path}")
async def serve_file(
    file_path: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_VIEW)),
):
    if file_path.startswith("http"):
        raise HTTPException(status_code=400, detail="External URLs should be accessed directly")

    await _authorize_attachment_file_access(db, current_user, file_path)
    resolved_path = get_file_path(file_path)
    return FileResponse(path=str(resolved_path), filename=resolved_path.name)


@router.get('/drive/{storage_uuid}/content')
async def serve_drive_image(
    storage_uuid: str,
    request: Request,
    variant: str = Query('original', pattern='^(original|thumbnail)$'),
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(require_permission(Permission.PATIENT_VIEW)),
):
    """Authorize before cache access, conditionals, ranges and remote reads."""
    import os
    import re
    from fastapi.responses import Response
    from backend.core.permissions import has_permission
    from backend.services.clinic_drive_provider import ClinicDriveProvider, DriveFailure
    from backend.services.clinic_google_connection import drive_io, mark_needs_reconnect
    from backend.services.drive_image_cache import image_cache
    from backend.services.file_service import MAX_FILE_SIZE_BYTES

    async def authorize():
        attachment = (await db.execute(select(models.Attachment).join(
            models.Patient, models.Attachment.patient_id == models.Patient.id,
        ).where(
            models.Attachment.storage_uuid == storage_uuid,
            models.Attachment.tenant_id == current_user.tenant_id,
            models.Attachment.storage_provider == 'google_drive',
            models.Attachment.storage_status == 'ready',
            models.Patient.tenant_id == current_user.tenant_id,
            models.Patient.is_deleted.is_(False),
        ).execution_options(populate_existing=True))).scalars().first()
        if not attachment:
            raise HTTPException(status_code=404, detail='الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف')
        user = (await db.execute(select(models.User).where(
            models.User.id == current_user.id, models.User.tenant_id == current_user.tenant_id,
        ).execution_options(populate_existing=True))).scalar_one_or_none()
        if not user or not user.is_active or user.is_deleted or not has_permission(user.role, Permission.PATIENT_VIEW) or not await get_visibility_service(db, user, user.tenant_id).can_view_patient(attachment.patient_id):
            raise HTTPException(status_code=404, detail='الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف')
        tenant = (await db.execute(select(models.Tenant).where(
            models.Tenant.id == current_user.tenant_id,
        ).execution_options(populate_existing=True))).scalar_one()
        if tenant.google_connection_status != 'connected' or not tenant.google_refresh_token or not tenant.google_image_folder_id or tenant.google_account_sub != attachment.google_account_sub:
            raise HTTPException(status_code=503, detail='الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف')
        return attachment, tenant

    attachment, tenant = await authorize()
    generation = tenant.google_connection_generation
    file_id = attachment.drive_original_id if variant == 'original' else attachment.drive_thumbnail_id
    digest = attachment.original_sha256 if variant == 'original' else attachment.thumbnail_sha256
    if not file_id or not digest:
        raise HTTPException(status_code=404, detail='الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف')
    etag = f'"{digest}"'
    headers = {'Cache-Control': 'private, no-store', 'ETag': etag, 'Accept-Ranges': 'bytes', 'X-Content-Type-Options': 'nosniff'}
    if request.headers.get('if-none-match') == etag:
        return Response(status_code=304, headers=headers)
    refresh, folder, tenant_id = tenant.google_refresh_token, tenant.google_image_folder_id, tenant.id
    installation = os.getenv('DENTIX_INSTALLATION_ID', '').strip()
    if not installation:
        raise HTTPException(status_code=503, detail='الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف')
    key = (tenant_id, storage_uuid, digest, variant, generation)
    await db.commit()
    async def load():
        provider = await drive_io(ClinicDriveProvider, refresh)
        return await drive_io(provider.download_image, file_id=file_id, folder_id=folder, tenant_id=tenant_id,
                              installation_id=installation, storage_uuid=storage_uuid, variant=variant,
                              digest=digest, max_bytes=MAX_FILE_SIZE_BYTES if variant == 'original' else 8 * 1024 * 1024)
    try:
        content = await image_cache.get_or_load(key, load)
    except DriveFailure as exc:
        if exc.category == 'reconnect':
            await mark_needs_reconnect(db, tenant_id=tenant_id, generation=generation)
        raise HTTPException(status_code=503, detail='الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف') from None
    except Exception:
        raise HTTPException(status_code=503, detail='الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف') from None
    attachment, tenant = await authorize()
    if tenant.google_connection_generation != generation or (attachment.original_sha256 if variant == 'original' else attachment.thumbnail_sha256) != digest:
        raise HTTPException(status_code=503, detail='الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف')
    status = 200
    range_header = request.headers.get('range')
    if range_header:
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', range_header.strip())
        if not match or not any(match.groups()):
            return Response(status_code=416, headers={**headers, 'Content-Range': f'bytes */{len(content)}'})
        first, last = match.groups()
        if first:
            start, end = int(first), min(int(last), len(content) - 1) if last else len(content) - 1
        else:
            suffix = int(last)
            start, end = max(0, len(content) - suffix), len(content) - 1
        if start > end or start >= len(content):
            return Response(status_code=416, headers={**headers, 'Content-Range': f'bytes */{len(content)}'})
        headers['Content-Range'] = f'bytes {start}-{end}/{len(content)}'
        content = content[start:end + 1]
        status = 206
    image_cache.record_outbound(len(content))
    return Response(content=content, status_code=status, media_type=attachment.file_type if variant == 'original' else 'image/jpeg', headers=headers)


@router.get('/drive/{storage_uuid}/status')
async def drive_image_status(storage_uuid: str, db: AsyncSession = Depends(get_async_db), current_user: models.User = Depends(require_permission(Permission.PATIENT_VIEW))):
    attachment = (await db.execute(select(models.Attachment).where(
        models.Attachment.tenant_id == current_user.tenant_id,
        models.Attachment.storage_uuid == storage_uuid,
        models.Attachment.storage_provider == 'google_drive',
    ))).scalar_one_or_none()
    if not attachment or not await get_visibility_service(db, current_user, current_user.tenant_id).can_view_patient(attachment.patient_id):
        raise HTTPException(status_code=404, detail='الصورة غير متاحة')
    operation = (await db.execute(select(models.TenantDataOperation).where(
        models.TenantDataOperation.tenant_id == current_user.tenant_id,
        models.TenantDataOperation.id == storage_uuid,
        models.TenantDataOperation.kind == 'drive_image_upload',
    ))).scalar_one_or_none()
    messages = {'quota': 'مساحة Google Drive غير كافية', 'reconnect': 'يرجى إعادة ربط Google Drive',
                'rate_limit': 'طلبات Google Drive كثيرة، يرجى المحاولة لاحقًا',
                'transient': 'Google Drive غير متاح مؤقتًا'}
    from backend.core.response import success_response
    return success_response(data={'status': attachment.storage_status,
                                  'message': messages.get(operation.error_code) if operation else None})
