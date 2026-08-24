"""File Upload Router — Secure file upload and retrieval endpoints."""

import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
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
    )
    return await crud.create_attachment(db, attachment_create)


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
