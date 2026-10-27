"""Known-version adapter for historical, unauthenticated clinic JSON files."""
from backend.services.tenant_archive import ArchiveError
from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS, STAFF_REFERENCE_COLUMNS

# Old exports contain these fields. Sensitive identity values are recognized
# only to discard them; they must never enter the new archive or a log.
LEGACY_USER_COLUMNS = frozenset('id username full_name email hashed_password failed_login_attempts last_failed_login account_locked_until is_2fa_enabled otp_secret active_session_id role permissions tenant_id fcm_token patient_visibility_mode can_view_other_doctors_history commission_percent fixed_salary per_appointment_fee hire_date is_active is_deleted deleted_at'.split())
LEGACY_DISCARDED_COLUMNS = {
    'patients': {'phone_search_hash', 'name_search_normalized'},
    'treatments': {'request_key', 'request_fingerprint'},
}
LEGACY_RENAMES = {'tooth_statuses': 'tooth_status'}


def adapt_legacy_json(source, *, tenant_id):
    """Return an explicitly unverified payload and disclose missing sections.

    Missing legacy sections must not be deleted by a restore. The coordinator
    must reject restoration when any omitted section contains live data.
    """
    if not isinstance(source, dict) or source.get('version') != '1.0' or source.get('tenant_id') != tenant_id:
        raise ArchiveError('ملف النسخة الاحتياطية القديم غير مدعوم أو لا يخص هذه العيادة')
    if set(source) - {'version', 'tenant_id', 'exported_at', 'data'} or not isinstance(source.get('data'), dict):
        raise ArchiveError('ملف النسخة الاحتياطية القديم غير صالح')
    sections = {}
    staff = None
    for original_name, rows in source['data'].items():
        name = LEGACY_RENAMES.get(original_name, original_name)
        if not isinstance(rows, list):
            raise ArchiveError('بيانات النسخة الاحتياطية القديمة غير صالحة')
        if name == 'users':
            if staff is not None:
                raise ArchiveError('أقسام النسخة الاحتياطية القديمة مكررة')
            staff = []
            for row in rows:
                if not isinstance(row, dict) or set(row) - LEGACY_USER_COLUMNS:
                    raise ArchiveError('بيانات المستخدمين القديمة غير مدعومة')
                if row.get('tenant_id') != tenant_id or row.get('role') == 'super_admin':
                    raise ArchiveError('حساب المستخدم في النسخة الاحتياطية غير صالح')
                staff.append({key: row.get(key) for key in STAFF_REFERENCE_COLUMNS})
            continue
        if name not in ARCHIVE_COLUMNS or name in sections:
            raise ArchiveError('أقسام النسخة الاحتياطية القديمة غير مدعومة')
        allowed = ARCHIVE_COLUMNS[name]
        discarded = LEGACY_DISCARDED_COLUMNS.get(name, set())
        converted = []
        for row in rows:
            if not isinstance(row, dict) or set(row) - allowed - discarded:
                raise ArchiveError('بيانات النسخة الاحتياطية القديمة غير مدعومة')
            if 'tenant_id' in allowed and row.get('tenant_id') != tenant_id:
                raise ArchiveError('النسخة الاحتياطية لا تخص هذه العيادة')
            converted.append({key: row.get(key) for key in allowed})
        sections[name] = converted
    if staff is None:
        raise ArchiveError('بيانات العاملين مفقودة من النسخة الاحتياطية القديمة')
    missing = sorted(set(ARCHIVE_COLUMNS) - set(sections))
    for name in missing:
        sections[name] = []
    sections['staff_references'] = staff
    return {'data': sections, 'legacy_unverified': True, 'missing_sections': missing, 'legacy_exported_at': source.get('exported_at')}


def missing_legacy_sections(payload):
    """Validate the legacy disclosure before it can affect replacement."""
    if not payload.get('legacy_unverified'):
        if set(payload) != {'data'}:
            raise ArchiveError('بيانات النسخة الاحتياطية غير مدعومة')
        return []
    if payload.get('legacy_unverified') is not True or set(payload) != {'data', 'legacy_unverified', 'missing_sections', 'legacy_exported_at'}:
        raise ArchiveError('بيانات النسخة الاحتياطية القديمة غير صالحة')
    missing = payload.get('missing_sections')
    if not isinstance(missing, list) or any(not isinstance(name, str) for name in missing) or len(set(missing)) != len(missing) or set(missing) - set(ARCHIVE_COLUMNS):
        raise ArchiveError('أقسام النسخة الاحتياطية القديمة غير صالحة')
    if any(payload['data'].get(name) != [] for name in missing):
        raise ArchiveError('أقسام النسخة الاحتياطية القديمة غير صالحة')
    return missing


async def ensure_missing_sections_empty(db, *, tenant_id, missing_sections):
    """Never erase current business rows absent from an old backup."""
    from sqlalchemy import select
    from backend import models
    classes = {mapper.local_table.name: mapper.class_ for mapper in models.Base.registry.mappers}
    for name in missing_sections:
        cls = classes[name]
        stmt = select(cls.id).limit(1)
        if name == 'price_list_items':
            stmt = stmt.join(models.PriceList, cls.price_list_id == models.PriceList.id).where(models.PriceList.tenant_id == tenant_id)
        else:
            stmt = stmt.where(cls.tenant_id == tenant_id)
        if (await db.execute(stmt)).first() is not None:
            raise ArchiveError('النسخة القديمة لا تشمل بيانات حالية في العيادة؛ لا يمكن استعادتها بأمان')
