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


def supported_archive_revisions(current_revision):
    """Business formats that have the same version-one column allowlist."""
    return {current_revision, 'd42a71e9bc83', 'e82c19f5a406', 'f17a93c60e24', 'ab52d9c807a1', 'bc78a10d932e', 'e2b3c4d5e6f7'}
