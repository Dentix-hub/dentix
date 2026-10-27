"""Bounded runtime settings for clinic backup archives."""
import os

from backend.services.tenant_archive import ArchiveError, DEFAULT_MAX_BYTES


def archive_max_bytes():
    try:
        value = int(os.getenv('TENANT_BACKUP_MAX_BYTES', str(DEFAULT_MAX_BYTES)))
    except ValueError as exc:
        raise ArchiveError('إعداد حجم النسخة الاحتياطية غير صالح') from exc
    if value < 1024 or value > DEFAULT_MAX_BYTES:
        raise ArchiveError('إعداد حجم النسخة الاحتياطية غير صالح')
    return value
