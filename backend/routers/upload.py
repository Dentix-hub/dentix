"""
File Upload Router — Secure file upload and retrieval endpoints.

All uploads go through validation (size, type, magic bytes) and are stored
in tenant-scoped directories. Files are served through authenticated endpoints,
NOT via public StaticFiles mounts.
"""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import cloudinary
import cloudinary.uploader

from .. import schemas, crud
from .auth import get_db
from backend.core.permissions import Permission, require_permission
from backend.services.file_service import validate_file, save_file_locally, get_file_path

logger = logging.getLogger(__name__)

# Cloudinary Configuration (optional — used when configured)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

router = APIRouter(prefix="/upload", tags=["Uploads"])


@router.post("", response_model=schemas.Attachment)
def upload_file(
    patient_id: int,
    file: UploadFile = File(...),
    note: str = Query(None),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_UPDATE)),
):
    """
    Upload a file for a patient.
    
    Security:
    - File validated (size, type, magic bytes)
    - Stored in tenant-scoped directory
    - Supports Cloudinary (preferred) or local storage (fallback)
    """
    # 1. Verify Patient & Access
    patient = crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # 2. Validate file security
    safe_filename, validated_content_type = validate_file(file)

    file_path_db = ""

    # 3. Try Cloudinary Upload
    try:
        if os.getenv("CLOUDINARY_CLOUD_NAME"):
            file.file.seek(0)
            upload_result = cloudinary.uploader.upload(
                file.file,
                folder=f"smart_clinic_uploads/tenant_{current_user.tenant_id}",
                resource_type="auto",
                public_id=safe_filename.rsplit(".", 1)[0],  # UUID without extension
            )
            file_path_db = upload_result.get("secure_url")
            logger.info("Uploaded to Cloudinary: %s", file_path_db)
        else:
            raise Exception("Cloudinary not configured")

    except Exception as e:
        logger.warning("Cloudinary failed/skipped: %s — falling back to local storage.", e)

        # 4. Fallback: Local Save (tenant-scoped)
        file_path_db = save_file_locally(
            file=file,
            safe_filename=safe_filename,
            tenant_id=current_user.tenant_id,
        )

    # 5. Create DB Record
    attachment_create = schemas.AttachmentCreate(
        patient_id=patient_id,
        filename=file.filename,  # Original filename for display
        file_path=file_path_db,
        file_type=validated_content_type,
    )

    return crud.create_attachment(db, attachment_create)


@router.get("/file/{file_path:path}")
def serve_file(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_VIEW)),
):
    """
    Serve an uploaded file through authenticated endpoint.
    
    This replaces the public StaticFiles mount. Files are only accessible
    to authenticated users with PATIENT_VIEW permission.
    """
    # Handle Cloudinary URLs (pass through)
    if file_path.startswith("http"):
        raise HTTPException(
            status_code=400,
            detail="External URLs should be accessed directly"
        )

    # Resolve and serve local file
    resolved_path = get_file_path(file_path)

    # Verify tenant access (file must be in the user's tenant directory)
    if current_user.role != "super_admin":
        expected_prefix = f"tenant_{current_user.tenant_id}"
        if not file_path.startswith(expected_prefix):
            logger.warning(
                "[FILE_SECURITY] Tenant %s attempted to access file: %s",
                current_user.tenant_id, file_path
            )
            raise HTTPException(status_code=403, detail="غير مصرح بالوصول لهذا الملف")

    return FileResponse(
        path=str(resolved_path),
        filename=resolved_path.name,
    )
