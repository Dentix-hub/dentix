"""File Upload Router — Secure file upload and retrieval endpoints."""

import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

import cloudinary
import cloudinary.uploader

from .. import crud, schemas
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
    file_path_db = ""
    try:
        if os.getenv("CLOUDINARY_CLOUD_NAME"):
            file.file.seek(0)
            upload_result = cloudinary.uploader.upload(
                file.file,
                folder=f"smart_clinic_uploads/tenant_{current_user.tenant_id}",
                resource_type="auto",
                public_id=safe_filename.rsplit(".", 1)[0],
            )
            file_path_db = upload_result.get("secure_url")
            logger.info("Uploaded patient attachment to configured cloud storage")
        else:
            raise RuntimeError("Cloudinary not configured")
    except Exception as exc:
        logger.warning(
            "Cloud storage failed/skipped (%s); using tenant-scoped local storage",
            type(exc).__name__,
        )
        file_path_db = save_file_locally(
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
    resolved_path = get_file_path(file_path)
    if current_user.role != "super_admin":
        expected_prefix = f"tenant_{current_user.tenant_id}"
        if not file_path.startswith(expected_prefix):
            logger.warning(
                "[FILE_SECURITY] Tenant %s attempted cross-tenant file access",
                current_user.tenant_id,
            )
            raise HTTPException(status_code=403, detail="غير مصرح بالوصول لهذا الملف")
    return FileResponse(path=str(resolved_path), filename=resolved_path.name)
