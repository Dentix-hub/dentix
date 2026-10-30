"""Bounded, read-only image-operation diagnostics for the clinic admin."""
from sqlalchemy import func, select

from backend import models

IMAGE_KINDS = ('drive_image_upload', 'drive_image_delete', 'drive_image_cleanup')
ACTIVE = ('queued', 'running')


async def image_backup_diagnostics(db, tenant_id):
    operation_filter = (
        models.TenantDataOperation.tenant_id == tenant_id,
        models.TenantDataOperation.kind.in_(IMAGE_KINDS),
        models.TenantDataOperation.status.in_(ACTIVE),
    )
    total = (await db.execute(select(func.count()).select_from(models.TenantDataOperation).where(*operation_filter))).scalar_one()
    # Never load encrypted image payloads, remote IDs, tokens or patient fields.
    rows = (await db.execute(select(
        models.TenantDataOperation.id, models.TenantDataOperation.kind,
        models.TenantDataOperation.status, models.TenantDataOperation.error_code,
        models.TenantDataOperation.attempts, models.TenantDataOperation.updated_at,
    ).where(*operation_filter).order_by(models.TenantDataOperation.created_at).limit(20))).all()
    ids = [row.id for row in rows]
    events = (await db.execute(select(
        models.DomainEvent.aggregate_id, models.DomainEvent.status,
        models.DomainEvent.attempts, models.DomainEvent.max_attempts,
    ).where(
        models.DomainEvent.tenant_id == tenant_id,
        models.DomainEvent.aggregate_type == 'tenant_data_operation',
        models.DomainEvent.aggregate_id.in_(ids),
        models.DomainEvent.event_type.in_(('tenant.image.upload', 'tenant.image.delete', 'tenant.image.cleanup')),
    ).order_by(models.DomainEvent.created_at.desc()).limit(100))).all() if ids else []
    incomplete = (await db.execute(select(func.count()).select_from(models.Attachment).where(
        models.Attachment.tenant_id == tenant_id,
        models.Attachment.storage_provider == 'google_drive',
        models.Attachment.storage_status.in_(('pending', 'deleting')),
    ))).scalar_one()
    safe_errors = {'quota', 'reconnect', 'rate_limit', 'transient', 'permission', 'not_found', 'cancelled', 'conflict'}
    return {
        'blocked': bool(total or incomplete), 'active_operation_count': total,
        'incomplete_attachment_count': incomplete, 'truncated': total > len(rows),
        'outbox_limit_reached': len(events) == 100,
        'operations': [{
            'operation_id': row.id, 'kind': row.kind, 'status': row.status,
            'error_code': row.error_code if row.error_code in safe_errors else ('unknown' if row.error_code else None),
            'attempts': row.attempts,
            'updated_at': row.updated_at.isoformat() if row.updated_at else None,
            'outbox': [{'status': event.status, 'attempts': event.attempts, 'max_attempts': event.max_attempts}
                       for event in events if event.aggregate_id == row.id],
        } for row in rows],
    }
