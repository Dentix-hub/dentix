"""Centralized File Handling Service — Validates, stores, and serves files securely.

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
    "image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff",
    "application/pdf", "application/dicom", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif",
    ".pdf", ".dcm", ".doc", ".docx", ".xls", ".xlsx",
}

BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js",
    ".msi", ".dll", ".scr", ".com", ".pif", ".hta",
    ".php", ".py", ".rb", ".pl", ".cgi", ".svg",
}

MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",
    b"%PDF": "application/pdf",
    b"PK": "application/zip",
    b"\xd0\xcf\x11\xe0": "application/msword",
}


def _get_upload_root() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "uploads"


def validate_file(file: UploadFile) -> tuple[str, str]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="اسم الملف مطلوب")

    original_ext = os.path.splitext(file.filename)[1].lower()
    if original_ext in BLOCKED_EXTENSIONS:
        logger.warning("[FILE_SECURITY] Blocked dangerous file extension: %s (filename: %s)", original_ext, file.filename)
        raise HTTPException(status_code=400, detail=f"نوع الملف '{original_ext}' غير مسموح به لأسباب أمنية")

    if original_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"نوع الملف '{original_ext}' غير مدعوم. الأنواع المسموحة: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
    if content_type not in ALLOWED_MIME_TYPES:
        guessed = mimetypes.guess_type(file.filename)[0]
        if guessed and guessed in ALLOWED_MIME_TYPES:
            content_type = guessed
            logger.info("[FILE] Corrected MIME type from '%s' to '%s'", file.content_type, content_type)
        else:
            logger.warning("[FILE_SECURITY] Rejected MIME type: %s for file: %s", content_type, file.filename)
            raise HTTPException(status_code=400, detail=f"نوع المحتوى '{content_type}' غير مسموح به")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"حجم الملف ({file_size // (1024*1024)} MB) يتجاوز الحد الأقصى ({MAX_FILE_SIZE_MB} MB)")
    if file_size == 0:
        raise HTTPException(status_code=400, detail="الملف فارغ")

    header = file.file.read(16)
    file.file.seek(0)
    _verify_magic_bytes(header, original_ext, content_type)
    return f"{uuid.uuid4()}{original_ext}", content_type


def _verify_magic_bytes(header: bytes, extension: str, content_type: str):
    if not header:
        return
    for magic, expected_mime in MAGIC_BYTES.items():
        if header.startswith(magic):
            if content_type.startswith("image/") and not expected_mime.startswith("image/"):
                logger.warning("[FILE_SECURITY] Magic bytes mismatch: header says '%s' but MIME is '%s'", expected_mime, content_type)
                raise HTTPException(status_code=400, detail="محتوى الملف لا يتطابق مع نوع الملف المُعلن")
            return
    if extension in {".jpg", ".jpeg", ".png"} and not any(header.startswith(m) for m in MAGIC_BYTES):
        logger.warning("[FILE_SECURITY] No magic bytes match for supposed image file: %s", extension)


def save_file_locally(file: UploadFile, safe_filename: str, tenant_id: Optional[int] = None) -> str:
    upload_root = _get_upload_root()
    tenant_dir = upload_root / f"tenant_{tenant_id}" if tenant_id else upload_root / "system"
    tenant_dir.mkdir(parents=True, exist_ok=True)
    target_path = tenant_dir / safe_filename
    try:
        file.file.seek(0)
        with open(target_path, "wb") as f:
            while chunk := file.file.read(8192):
                f.write(chunk)
    except Exception as e:
        logger.error("[FILE] Failed to save file: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="فشل في حفظ الملف")
    return f"tenant_{tenant_id}/{safe_filename}" if tenant_id else f"system/{safe_filename}"


def get_file_path(relative_path: str) -> Path:
    """Resolve an upload path while enforcing a component-aware root boundary."""
    upload_root = _get_upload_root().resolve()
    resolved = (upload_root / relative_path).resolve()

    try:
        resolved.relative_to(upload_root)
    except ValueError:
        logger.warning("[FILE_SECURITY] Path traversal attempt: %s", relative_path)
        raise HTTPException(status_code=400, detail="مسار ملف غير صالح")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="الملف غير موجود")
    return resolved
