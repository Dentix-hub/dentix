"""Provision a per-clinic Drive connection without replacing a healthy one early."""
import asyncio
import os
from sqlalchemy import select

from backend import models
from backend.core.tenancy import clear_tenant_context, set_current_tenant_id
from backend.database import AsyncSessionLocal, RlsContext
from backend.services.clinic_google_attempts import _active_admin
from backend.services.clinic_google_oauth import GoogleConnectionError

_DRIVE_CONCURRENCY = asyncio.Semaphore(4)


async def drive_io(call, *args, **kwargs):
    async with _DRIVE_CONCURRENCY:
        return await asyncio.to_thread(call, *args, **kwargs)


async def _identity(db, tenant_id, user_id):
    tenant = (await db.execute(select(models.Tenant).where(models.Tenant.id == tenant_id).with_for_update())).scalar_one_or_none()
    user = (await db.execute(select(models.User).where(models.User.tenant_id == tenant_id, models.User.id == user_id))).scalar_one_or_none()
    if not _active_admin(user, tenant):
        raise GoogleConnectionError('تغير حساب أو صلاحيات مدير العيادة أثناء الربط')
    return tenant


async def finish_google_connection(*, details, identity, provider):
    """Reuse durable folder IDs across retries; never hold DB during I/O."""
    tenant_id, user_id, generation = details['tenant_id'], details['user_id'], details['generation']
    installation = os.getenv('DENTIX_INSTALLATION_ID', '').strip()
    if not installation or len(installation) > 100:
        raise GoogleConnectionError('إعدادات بيئة النسخ الاحتياطي غير مكتملة')
    token = set_current_tenant_id(tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            tenant = await _identity(db, tenant_id, user_id)
            if tenant.google_connection_generation != generation:
                raise GoogleConnectionError('تغير اتصال Google أثناء الربط، يرجى المحاولة مجددًا')
            changing_account = bool(tenant.google_account_sub and tenant.google_account_sub != identity['sub'])
            if changing_account:
                image = (await db.execute(select(models.Attachment.id).where(
                    models.Attachment.tenant_id == tenant_id,
                    models.Attachment.storage_provider == 'google_drive',
                ).limit(1))).first()
                if image:
                    raise GoogleConnectionError('لا يمكن تغيير حساب Google لوجود صور مرتبطة بالحساب الحالي')
            existing = (None, None, None) if changing_account else (tenant.google_root_folder_id, tenant.google_backup_folder_id, tenant.google_image_folder_id)
            await db.commit()
        if all(existing):
            ids = existing
        else:
            proposed = await drive_io(provider.reserve_ids, 3)
            async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
                tenant = await _identity(db, tenant_id, user_id)
                if tenant.google_connection_generation != generation:
                    raise GoogleConnectionError('تغير اتصال Google أثناء الربط، يرجى المحاولة مجددًا')
                prior = (await db.execute(select(models.GoogleOAuthAttempt).where(
                    models.GoogleOAuthAttempt.tenant_id == tenant_id,
                    models.GoogleOAuthAttempt.connection_generation == generation,
                    models.GoogleOAuthAttempt.pending_account_sub == identity['sub'],
                    models.GoogleOAuthAttempt.pending_root_id.is_not(None),
                    models.GoogleOAuthAttempt.pending_backup_id.is_not(None),
                    models.GoogleOAuthAttempt.pending_image_id.is_not(None),
                ).order_by(models.GoogleOAuthAttempt.created_at.asc()))).scalars().first()
                if prior:
                    ids = (prior.pending_root_id, prior.pending_backup_id, prior.pending_image_id)
                else:
                    attempt = (await db.execute(select(models.GoogleOAuthAttempt).where(
                        models.GoogleOAuthAttempt.id == details['attempt_id'],
                        models.GoogleOAuthAttempt.tenant_id == tenant_id,
                        models.GoogleOAuthAttempt.user_id == user_id,
                    ).with_for_update())).scalar_one()
                    attempt.pending_account_sub = identity['sub']
                    attempt.pending_root_id, attempt.pending_backup_id, attempt.pending_image_id = proposed
                    ids = tuple(proposed)
                await db.commit()
        common = {'tenant_id': tenant_id, 'installation_id': installation, 'account_sub': identity['sub']}
        await drive_io(provider.ensure_folder, folder_id=ids[0], name='DENTIX', parent_id=None, kind='root', **common)
        await drive_io(provider.ensure_folder, folder_id=ids[1], name='Backups', parent_id=ids[0], kind='backups', **common)
        await drive_io(provider.ensure_folder, folder_id=ids[2], name='Images', parent_id=ids[0], kind='images', **common)
        async with AsyncSessionLocal(context=RlsContext(tenant_id=tenant_id)) as db:
            tenant = await _identity(db, tenant_id, user_id)
            if tenant.google_connection_generation != generation:
                raise GoogleConnectionError('تغير اتصال Google أثناء الربط، يرجى المحاولة مجددًا')
            if tenant.google_account_sub and tenant.google_account_sub != identity['sub']:
                image = (await db.execute(select(models.Attachment.id).where(
                    models.Attachment.tenant_id == tenant_id,
                    models.Attachment.storage_provider == 'google_drive',
                ).limit(1))).first()
                if image:
                    raise GoogleConnectionError('لا يمكن تغيير حساب Google لوجود صور مرتبطة بالحساب الحالي')
            tenant.google_refresh_token = identity['refresh_token']
            tenant.google_account_sub = identity['sub']
            tenant.google_account_email = identity.get('email')
            tenant.google_root_folder_id, tenant.google_backup_folder_id, tenant.google_image_folder_id = ids
            tenant.google_connection_status = 'connected'
            tenant.google_connection_generation += 1
            await db.commit()
            # Resume previously exhausted remote deletions after reconnecting.
            from sqlalchemy import update
            from datetime import datetime, timezone
            pending_ids = select(models.TenantDataOperation.id).where(
                models.TenantDataOperation.tenant_id == tenant_id,
                models.TenantDataOperation.kind.in_(['drive_image_delete', 'drive_image_cleanup']),
                models.TenantDataOperation.status != 'completed',
            )
            await db.execute(update(models.DomainEvent).where(
                models.DomainEvent.tenant_id == tenant_id,
                models.DomainEvent.event_type.in_(['tenant.image.delete', 'tenant.image.cleanup']),
                models.DomainEvent.status == 'failed',
                models.DomainEvent.aggregate_id.in_(pending_ids),
            ).values(status='pending', attempts=0, available_at=datetime.now(timezone.utc), error_message=None))
            await db.commit()
        from backend.services.drive_image_cache import image_cache
        image_cache.invalidate(tenant_id=tenant_id)
        return True
    finally:
        clear_tenant_context(tenant_token=token)


async def mark_needs_reconnect(db, *, tenant_id, generation):
    """Do not let an old provider failure invalidate a newer connection."""
    from sqlalchemy import update
    result = await db.execute(update(models.Tenant).where(
        models.Tenant.id == tenant_id,
        models.Tenant.google_connection_generation == generation,
        models.Tenant.google_connection_status == 'connected',
    ).values(google_connection_status='needs_reconnect', google_connection_generation=generation + 1))
    await db.commit()
    if result.rowcount == 1:
        from backend.services.drive_image_cache import image_cache
        image_cache.invalidate(tenant_id=tenant_id)
    return result.rowcount == 1
