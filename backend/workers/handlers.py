"""
Event Handlers — Domain Event Consumers

Each handler is registered via @register_handler("event_type") and is called
by the background event_processor when a matching DomainEvent is polled.

Handlers receive the DomainEvent ORM object and should be async functions.
"""

import logging
from backend.workers.event_processor import register_handler
from backend.models.domain_event import DomainEvent
from backend import models

logger = logging.getLogger("smart_clinic.events")


@register_handler("appointment.created")
async def on_appointment_created(event: DomainEvent):
    """
    Fires when a new appointment is saved.
    Future uses: push notification, CRM sync.
    For now: structured log so we can verify the pipeline works end-to-end.
    """
    payload = event.payload or {}
    logger.info(
        "[EVENT] appointment.created | tenant=%s | patient=%s | time=%s",
        event.tenant_id,
        payload.get("patient_id"),
        payload.get("time"),
    )


@register_handler("appointment.cancelled")
async def on_appointment_cancelled(event: DomainEvent):
    """Handle appointment cancellation events."""
    payload = event.payload or {}
    logger.info(
        "[EVENT] appointment.cancelled | tenant=%s | appointment=%s | reason=%s",
        event.tenant_id,
        event.aggregate_id,
        payload.get("reason", "N/A"),
    )


@register_handler("payment.created")
async def on_payment_created(event: DomainEvent):
    """
    Fires when a payment is recorded.
    Future uses: receipt generation, SMS confirmation, financial dashboard cache invalidation.
    """
    payload = event.payload or {}
    logger.info(
        "[EVENT] payment.created | tenant=%s | patient=%s | amount=%s",
        event.tenant_id,
        payload.get("patient_id"),
        payload.get("amount"),
    )


@register_handler("treatment.created")
async def on_treatment_created(event: DomainEvent):
    """Handle treatment creation events."""
    payload = event.payload or {}
    logger.info(
        "[EVENT] treatment.created | tenant=%s | patient=%s | procedure=%s",
        event.tenant_id,
        payload.get("patient_id"),
        payload.get("procedure"),
    )


@register_handler("system.backup.requested")
async def on_system_backup_requested(event: DomainEvent):
    """Run one durable backup request on the isolated system DB session."""
    from backend.database import system_session_scope
    from backend.services.backup_scheduler_service import execute_backup_event

    async with system_session_scope() as db:
        await execute_backup_event(db, event)



@register_handler("auth.password_reset.requested")
async def on_password_reset_requested(event: DomainEvent):
    """Deliver one encrypted, short-lived reset token and erase its payload."""
    import asyncio
    import hashlib
    from datetime import datetime, timezone
    from sqlalchemy import select
    from backend.core.security import get_encryption_manager
    from backend.database import AsyncSessionLocal, RlsContext, system_session_scope
    from backend.email_service import send_password_reset_email
    from backend.services.auth_bootstrap import resolve_password_reset_identity, password_reset_identity_scope

    async def erase_payload():
        async with system_session_scope() as system_db:
            row = (await system_db.execute(select(DomainEvent).where(
                DomainEvent.id == event.id, DomainEvent.event_type == "auth.password_reset.requested",
                DomainEvent.tenant_id.is_(None) if event.tenant_id is None else DomainEvent.tenant_id == event.tenant_id,
            ))).scalar_one_or_none()
            if row is not None:
                row.payload = {}
                await system_db.commit()

    encrypted = (event.payload or {}).get("encrypted_token")
    if not encrypted:
        return
    try:
        raw = get_encryption_manager().decrypt(encrypted, allow_plaintext_fallback=False)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        identity = await resolve_password_reset_identity(token_hash=digest)
        if identity is None or identity[1] != event.tenant_id or str(identity[0]) != event.aggregate_id:
            await erase_payload()
            return
        async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as db:
            async with password_reset_identity_scope(db, identity) as (scoped_db, user):
                token = (await scoped_db.execute(select(models.PasswordResetToken).where(
                    models.PasswordResetToken.user_id == identity[0],
                    models.PasswordResetToken.token == digest,
                    models.PasswordResetToken.used.is_(False),
                ))).scalar_one_or_none()
                expires = token.expires_at if token else None
                if expires and expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if not user or not user.email or not expires or expires <= datetime.now(timezone.utc):
                    await erase_payload()
                    return
                sent = await asyncio.to_thread(send_password_reset_email, user.email, raw, user.username)
                if not sent:
                    raise RuntimeError("Password reset delivery failed")
        await erase_payload()
    except Exception:
        # Event processor persists exception text, so never propagate provider data.
        raise RuntimeError("Password reset delivery failed") from None


@register_handler('tenant.restore.confirmed')
async def on_tenant_restore_confirmed(event: DomainEvent):
    """Resume a durable restore without putting clinic data in the outbox."""
    from sqlalchemy import select, text
    from backend.core.tenancy import set_current_tenant_id, clear_tenant_context
    from backend.database import AsyncSessionLocal, RlsContext
    from backend.services.tenant_archive import configured_keys
    from backend.services.tenant_backup_config import archive_max_bytes
    from backend.services.tenant_restore_coordinator import run_confirmed_restore

    token = set_current_tenant_id(event.tenant_id)
    try:
        async with AsyncSessionLocal(context=RlsContext(tenant_id=event.tenant_id)) as db:
            operation = (await db.execute(select(models.TenantDataOperation).where(
                models.TenantDataOperation.tenant_id == event.tenant_id,
                models.TenantDataOperation.id == event.aggregate_id,
            ))).scalar_one_or_none()
            if operation is None or operation.status in {'completed', 'failed', 'expired'}:
                return
            _, keys, installation_id = configured_keys()
            revision = (await db.execute(text('SELECT version_num FROM alembic_version'))).scalar_one()
            await run_confirmed_restore(db, tenant_id=event.tenant_id, operation_id=event.aggregate_id,
                                        installation_id=installation_id, keys=keys,
                                        supported_revisions={revision}, max_bytes=archive_max_bytes())
    except Exception:
        # Provider data, archive content and encryption configuration are not
        # persisted in the job error or emitted to logs.
        raise RuntimeError('تعذرت معالجة عملية استعادة العيادة') from None
    finally:
        clear_tenant_context(tenant_token=token)
