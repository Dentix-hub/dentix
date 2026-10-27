"""Execute a confirmed clinic restore with durable success/failure status."""
import base64
import binascii
import hashlib
import hmac
from datetime import datetime, timezone

from sqlalchemy import select

from backend import models
from backend.services.tenant_archive import ArchiveError, decode_archive
from backend.services.tenant_archive_embedded_refs import validate_embedded_references
from backend.services.tenant_archive_identity import resolve_staff_mapping
from backend.services.tenant_archive_legacy import missing_legacy_sections
from backend.services.tenant_archive_import import replace_clinic_business_data
from backend.services.tenant_archive_registry import validate_archive_references, validate_archive_sections, validate_archive_values


async def known_global_references(db):
    """Resolve shared references from this installation, never from an archive."""
    categories = (await db.execute(select(models.MaterialCategory.id))).scalars().all()
    procedures = (await db.execute(select(models.Procedure.id).where(models.Procedure.tenant_id.is_(None)))).scalars().all()
    return {'material_categories': set(categories), 'procedures': set(procedures)}


async def run_confirmed_restore(db, *, tenant_id, operation_id, installation_id, keys, supported_revisions, max_bytes):
    """Restore atomically; record failure only after the business rollback."""
    try:
        operation = (await db.execute(select(models.TenantDataOperation).where(
            models.TenantDataOperation.tenant_id == tenant_id,
            models.TenantDataOperation.id == operation_id,
        ).with_for_update())).scalar_one_or_none()
        if operation is None or operation.kind != 'restore' or operation.status != 'confirmed' or not operation.encrypted_payload:
            raise ArchiveError('عملية الاستعادة غير صالحة أو سبق تنفيذها')
        expires = operation.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc):
            raise ArchiveError('انتهت صلاحية عملية الاستعادة')
        if len(operation.encrypted_payload) > ((max_bytes + 2) // 3) * 4:
            raise ArchiveError('حجم النسخة الاحتياطية أكبر من الحد المسموح')
        try:
            archive = base64.b64decode(operation.encrypted_payload, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ArchiveError('ملف النسخة الاحتياطية غير صالح') from exc
        if not hmac.compare_digest(hashlib.sha256(archive).hexdigest(), operation.archive_digest):
            raise ArchiveError('ملف الاستعادة لا يطابق الملف الذي تمت معاينته')
        header, payload = decode_archive(archive, tenant_id=tenant_id, installation_id=installation_id, keys=keys, max_bytes=max_bytes)
        if header.get('schema_revision') not in supported_revisions:
            raise ArchiveError('إصدار قاعدة بيانات النسخة الاحتياطية غير مدعوم')
        missing = missing_legacy_sections(payload)
        data = validate_archive_sections(payload, tenant_id=tenant_id)
        validate_archive_values(data)
        external_ids = await known_global_references(db)
        validate_archive_references(data, tenant_id=tenant_id, external_ids=external_ids)
        validate_embedded_references(data, tenant_id=tenant_id, external_ids=external_ids)
        staff = await resolve_staff_mapping(db, tenant_id, data['staff_references'])
        if header.get('counts') != {name: len(rows) for name, rows in data.items()}:
            raise ArchiveError('أعداد سجلات النسخة الاحتياطية غير متطابقة')
        counts, mapping = await replace_clinic_business_data(db, tenant_id=tenant_id, data=data, staff_mapping=staff, external_ids=external_ids, missing_sections=missing)
        operation.status = 'completed'
        operation.encrypted_payload = None
        operation.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return counts, mapping
    except Exception:
        await db.rollback()
        # A concurrent or invalid request must not overwrite an existing outcome.
        operation = (await db.execute(select(models.TenantDataOperation).where(
            models.TenantDataOperation.tenant_id == tenant_id,
            models.TenantDataOperation.id == operation_id,
        ).with_for_update())).scalar_one_or_none()
        if operation is not None and operation.status == 'confirmed':
            operation.status = 'failed'
            operation.error_code = 'restore_failed'
            operation.completed_at = datetime.now(timezone.utc)
            operation.encrypted_payload = None
            await db.commit()
        else:
            await db.rollback()
        raise
