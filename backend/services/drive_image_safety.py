"""Coordinate business snapshots with unfinished remote image work."""
from sqlalchemy import select

from backend import models
from backend.services.tenant_archive import ArchiveError


async def ensure_no_active_image_operations(db, tenant_id):
    active = (await db.execute(select(models.TenantDataOperation.id).where(
        models.TenantDataOperation.tenant_id == tenant_id,
        models.TenantDataOperation.kind.in_(['drive_image_upload', 'drive_image_delete', 'drive_image_cleanup']),
        models.TenantDataOperation.status.in_(['queued', 'running']),
    ).limit(1))).first()
    if active:
        raise ArchiveError('انتظر اكتمال عمليات صور Google Drive قبل النسخ أو الاستعادة')
    incomplete = (await db.execute(select(models.Attachment.id).where(
        models.Attachment.tenant_id == tenant_id,
        models.Attachment.storage_provider == 'google_drive',
        models.Attachment.storage_status.in_(['pending', 'deleting']),
    ).limit(1))).first()
    if incomplete:
        raise ArchiveError('انتظر اكتمال عمليات صور Google Drive قبل النسخ أو الاستعادة')
