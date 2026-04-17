import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import os
import shutil
import uuid

from .. import schemas, crud
from .auth import get_db
from backend.core.permissions import Permission, require_permission

import cloudinary

logger = logging.getLogger(__name__)
import cloudinary.uploader

# Cloudinary Configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

router = APIRouter(prefix="/upload", tags=["Uploads"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=schemas.Attachment)
def upload_file(
    patient_id: int,
    file: UploadFile = File(...),
    note: str = Query(None),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(require_permission(Permission.PATIENT_UPDATE)),
):
    """
    Upload a file for a patient.
    Supports Cloudinary (preferred) or Local Storage (fallback).
    """
    # 1. Verify Patient & Access
    patient = crud.get_patient(db, patient_id, current_user.tenant_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    file_path_db = ""

    # 2. Try Cloudinary Upload
    try:
        if os.getenv("CLOUDINARY_CLOUD_NAME"):
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file.file, folder="smart_clinic_uploads", resource_type="auto"
            )
            file_path_db = upload_result.get("secure_url")
            logger.info("Uploaded to Cloudinary: %s", file_path_db)
        else:
            raise Exception("Cloudinary not configured")

    except Exception as e:
        logger.warning("Cloudinary failed/skipped: %s — falling back to local storage.", e)

        # 3. Fallback: Local Save
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        local_path = os.path.join(UPLOAD_DIR, unique_filename)

        try:
            # Reset file pointer if it was read by cloudinary attempt
            file.file.seek(0)
            with open(local_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_path_db = f"uploads/{unique_filename}"
        except Exception as local_e:
            raise HTTPException(
                status_code=500, detail=f"File save failed: {str(local_e)}"
            )

    # 4. Create DB Record
    attachment_create = schemas.AttachmentCreate(
        patient_id=patient_id,
        filename=file.filename,
        file_path=file_path_db,
        file_type=file.content_type or "application/octet-stream",
    )

    return crud.create_attachment(db, attachment_create)
