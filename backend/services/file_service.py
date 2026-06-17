"""
Centralized File Handling Service — Validates, stores, and serves files securely.

Security measures:
- File size limits (10 MB default)
- MIME type allowlist (medical-safe types only)
- Extension allowlist
- Magic bytes verification
- Tenant-scoped storage paths
- UUID filenames (prevent path traversal)
"""

import os
import uuid
import logging
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException

logger = logging.getLogger("smart_clinic.file_service")

# === CONFIGURATION ===
MAX_FILE_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Allowed MIME types for a dental clinic application
ALLOWED_MIME_TYPES = {
    # Images (X-rays, photos, scans)
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
    # Documents
    "application/pdf",
    # DICOM (dental imaging standard)
    "application/dicom",
    # Office documents
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif",
    ".pdf", ".dcm",
    ".doc", ".docx", ".xls", ".xlsx",
}

# Dangerous extensions that MUST be blocked regardless
BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js",
    ".msi", ".dll", ".scr", ".com", ".pif", ".hta",
    ".php", ".py", ".rb", ".pl", ".cgi",
    ".svg",  # SVG can contain scripts
}

# Magic bytes signatures for common file types
MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # Partial — WebP starts with RIFF
    b"%PDF": "application/pdf",
    b"PK": "application/zip",  # docx/xlsx are ZIP archives
    b"\xd0\xcf\x11\xe0": "application/msword",  # OLE2 (doc/xls)
}


def _get_upload_root() -> Path:
    """Get the root upload directory."""
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "uploads"


def validate_file(file: UploadFile) -> tuple[str, str]:
    """
    Validate an uploaded file for security.

    Returns:
        Tuple of (safe_filename, validated_content_type)

    Raises:
        HTTPException 400 if validation fails
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="اسم الملف مطلوب")

    # 1. Check extension
    original_ext = os.path.splitext(file.filename)[1].lower()

    if original_ext in BLOCKED_EXTENSIONS:
        logger.warning(
            "[FILE_SECURITY] Blocked dangerous file extension: %s (filename: %s)",
            original_ext, file.filename
        )
        raise HTTPException(
            status_code=400,
            detail=f"نوع الملف '{original_ext}' غير مسموح به لأسباب أمنية"
        )

    if original_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"نوع الملف '{original_ext}' غير مدعوم. الأنواع المسموحة: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 2. Check MIME type
    content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    if content_type not in ALLOWED_MIME_TYPES:
        # Be lenient with MIME types — browsers sometimes send wrong ones
        # But log it for monitoring
        guessed = mimetypes.guess_type(file.filename)[0]
        if guessed and guessed in ALLOWED_MIME_TYPES:
            content_type = guessed
            logger.info("[FILE] Corrected MIME type from '%s' to '%s'", file.content_type, content_type)
        else:
            logger.warning(
                "[FILE_SECURITY] Rejected MIME type: %s for file: %s",
                content_type, file.filename
            )
            raise HTTPException(
                status_code=400,
                detail=f"نوع المحتوى '{content_type}' غير مسموح به"
            )

    # 3. Check file size (read first chunk to verify)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"حجم الملف ({file_size // (1024*1024)} MB) يتجاوز الحد الأقصى ({MAX_FILE_SIZE_MB} MB)"
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="الملف فارغ")

    # 4. Verify magic bytes (basic check)
    header = file.file.read(16)
    file.file.seek(0)

    _verify_magic_bytes(header, original_ext, content_type)

    # 5. Generate safe filename (UUID + original extension)
    safe_filename = f"{uuid.uuid4()}{original_ext}"

    return safe_filename, content_type


def _verify_magic_bytes(header: bytes, extension: str, content_type: str):
    """Verify that file header matches expected type (defense against renamed executables)."""
    if not header:
        return

    # Check known signatures
    for magic, expected_mime in MAGIC_BYTES.items():
        if header.startswith(magic):
            # If we found a match, verify it's consistent
            if content_type.startswith("image/") and not expected_mime.startswith("image/"):
                logger.warning(
                    "[FILE_SECURITY] Magic bytes mismatch: header says '%s' but MIME is '%s'",
                    expected_mime, content_type
                )
                raise HTTPException(
                    status_code=400,
                    detail="محتوى الملف لا يتطابق مع نوع الملف المُعلن"
                )
            return

    # For images, we should have found a magic byte match
    if extension in {".jpg", ".jpeg", ".png"} and not any(header.startswith(m) for m in MAGIC_BYTES):
        logger.warning(
            "[FILE_SECURITY] No magic bytes match for supposed image file: %s",
            extension
        )
        # Don't block — some valid image formats may have unusual headers
        # But log for monitoring


def save_file_locally(
    file: UploadFile,
    safe_filename: str,
    tenant_id: Optional[int] = None,
) -> str:
    """
    Save a validated file to the local filesystem.

    Args:
        file: The validated upload file
        safe_filename: UUID-based safe filename from validate_file()
        tenant_id: Tenant ID for scoped storage

    Returns:
        Relative path for DB storage (e.g., "tenant_5/abc123.jpg")
    """
    upload_root = _get_upload_root()

    # Tenant-scoped subdirectory
    if tenant_id:
        tenant_dir = upload_root / f"tenant_{tenant_id}"
    else:
        tenant_dir = upload_root / "system"

    tenant_dir.mkdir(parents=True, exist_ok=True)

    # Write file
    target_path = tenant_dir / safe_filename

    try:
        file.file.seek(0)
        with open(target_path, "wb") as f:
            # Read in chunks to handle large files
            while chunk := file.file.read(8192):
                f.write(chunk)
    except Exception as e:
        logger.error("[FILE] Failed to save file: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="فشل في حفظ الملف")

    # Return relative path for DB storage
    if tenant_id:
        return f"tenant_{tenant_id}/{safe_filename}"
    return f"system/{safe_filename}"


def get_file_path(relative_path: str) -> Path:
    """
    Resolve a relative file path to an absolute path, with path traversal protection.

    Args:
        relative_path: The path stored in the database

    Returns:
        Absolute path to the file

    Raises:
        HTTPException 404 if file doesn't exist
        HTTPException 400 if path traversal detected
    """
    upload_root = _get_upload_root()

    # Normalize and resolve to prevent path traversal
    resolved = (upload_root / relative_path).resolve()

    # Verify the resolved path is still under upload_root
    if not str(resolved).startswith(str(upload_root.resolve())):
        logger.warning("[FILE_SECURITY] Path traversal attempt: %s", relative_path)
        raise HTTPException(status_code=400, detail="مسار ملف غير صالح")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="الملف غير موجود")

    return resolved
