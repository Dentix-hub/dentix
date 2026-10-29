"""Transactional replacement of validated clinic business data.

Only the restore coordinator may call this function, after authenticating the
archive, validating every field/reference, and authorizing a confirmed operation.
It never commits; failures must roll back the entire caller transaction.
"""
from datetime import date, datetime
from decimal import Decimal
from graphlib import TopologicalSorter

from sqlalchemy import Date, DateTime, Numeric, delete, select, text

from backend import models
from backend.services.tenant_archive import ArchiveError
from backend.services.tenant_archive_embedded_refs import (
    remap_event_payload, remap_learning_data, remap_price_snapshot, remap_stock_reference, remap_treatment_note,
)
from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS
from backend.services.tenant_archive_history import deleted_treatment_contexts, historical_treatment_ids

GATE_NAMESPACE = 1146377304


def _model_classes():
    return {mapper.local_table.name: mapper.class_ for mapper in models.Base.registry.mappers}


def _order():
    names = set(ARCHIVE_COLUMNS)
    dependencies = {}
    for name in sorted(names):
        table = models.Base.metadata.tables[name]
        dependencies[name] = sorted({fk.column.table.name for column in table.columns for fk in column.foreign_keys
                                     if fk.column.table.name in names and fk.column.table.name != name})
    return list(TopologicalSorter(dependencies).static_order())


def _convert(column, value):
    if value is None:
        return None
    if isinstance(column.type, DateTime):
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    if isinstance(column.type, Date):
        return date.fromisoformat(value)
    if isinstance(column.type, Numeric) and isinstance(value, str):
        return Decimal(value)
    return value


async def replace_clinic_business_data(db, *, tenant_id, data, staff_mapping, external_ids=None, missing_sections=()):
    if db.bind.dialect.name != 'postgresql':
        raise ArchiveError('الاستعادة الآمنة تتطلب قاعدة بيانات PostgreSQL')
    # Every ordinary business write acquires a shared gate in a database
    # trigger; the exclusive transaction lock waits for all previous writers.
    await db.execute(text('SELECT pg_advisory_xact_lock(:namespace, :tenant)'),
                     {'namespace': GATE_NAMESPACE, 'tenant': tenant_id})
    from backend.services.drive_image_safety import ensure_no_active_image_operations
    await ensure_no_active_image_operations(db, tenant_id)
    from backend.services.tenant_archive_legacy import ensure_missing_sections_empty
    await ensure_missing_sections_empty(db, tenant_id=tenant_id, missing_sections=missing_sections)
    classes = _model_classes()
    historical_contexts = deleted_treatment_contexts(data)
    order = _order()
    for name in reversed(order):
        cls = classes[name]
        if name == 'price_list_items':
            lists = select(models.PriceList.id).where(models.PriceList.tenant_id == tenant_id)
            stmt = delete(cls).where(cls.price_list_id.in_(lists))
        else:
            stmt = delete(cls).where(cls.tenant_id == tenant_id)
        await db.execute(stmt)
    mapping = {'tenants': {tenant_id: tenant_id}, 'users': dict(staff_mapping)}
    for name, values in (external_ids or {}).items():
        if name not in {'material_categories', 'procedures'}:
            raise ArchiveError('مرجع خارجي غير مدعوم في النسخة الاحتياطية')
        mapping[name] = {value: value for value in values}
    deferred = []
    for name in order:
        cls = classes[name]
        table = models.Base.metadata.tables[name]
        table_map = mapping.setdefault(name, {})
        for source in data[name]:
            values = {}
            later = {}
            for key, value in source.items():
                if key == 'id':
                    continue
                col = table.c[key]
                if name == 'material_learning_logs' and key == 'calculation_data':
                    later[key] = value
                    values[key] = None
                    continue
                if name == 'clinical_events' and key == 'payload':
                    later[key] = value
                    later['historical_ids'] = historical_contexts.get((source.get('patient_id'), source.get('work_item_id')), set())
                    values[key] = {}
                    continue
                if name == 'stock_movements' and key == 'reference_id':
                    later[key] = value
                    values[key] = None
                    continue
                if name == 'treatments' and key in {'notes', 'price_snapshot'}:
                    later[key] = value
                    values[key] = None
                    continue
                for foreign in col.foreign_keys:
                    if value is not None:
                        try:
                            value = mapping[foreign.column.table.name][value]
                        except KeyError as exc:
                            raise ArchiveError(
                                f'تحتوي النسخة الاحتياطية على مرجع غير صالح ({name}.{key})',
                                section=name, field=key, referenced_section=foreign.column.table.name,
                                category='invalid_reference', counts=1,
                            ) from exc
                values[key] = _convert(col, value)
            row = cls(**values)
            db.add(row)
            await db.flush()
            table_map[source['id']] = row.id
            if later:
                deferred.append((name, row, later))
    # Reserve sequence values without inserting treatments. Historical references
    # must stay absent after IDs are regenerated, even if an old ID is now used
    # by another clinic or would collide with a newly restored live treatment.
    historical = {}
    historical_ids = sorted(historical_treatment_ids(historical_contexts))
    if historical_ids:
        reserved = (await db.execute(text(
            "SELECT nextval(pg_get_serial_sequence('treatments', 'id')) "
            "FROM generate_series(1, :count)"
        ), {'count': len(historical_ids)})).scalars().all()
        if (
            any(not isinstance(value, int) or value <= 0 for value in reserved)
            or len(set(reserved)) != len(historical_ids)
            or set(reserved).intersection(mapping.get('treatments', {}).values())
        ):
            raise ArchiveError('تعذر تخصيص مراجع آمنة لسجل العلاجات المحذوفة')
        historical = dict(zip(historical_ids, reserved, strict=True))
        mapping['historical_treatments'] = historical
    for name, row, later in deferred:
        if name == 'material_learning_logs':
            row.calculation_data = remap_learning_data(later['calculation_data'], mapping, historical_mapping=historical)
        elif name == 'clinical_events':
            row.payload = remap_event_payload(later['payload'], mapping,
                                            historical_mapping={value: historical[value] for value in later['historical_ids']})
        elif name == 'stock_movements':
            row.reference_id = remap_stock_reference(later['reference_id'], mapping, historical_mapping=historical)
        elif name == 'treatments':
            row.notes = remap_treatment_note(later['notes'], mapping)
            row.price_snapshot = remap_price_snapshot(later['price_snapshot'], mapping)
    # Only the financial staff attributes are business backup data. Never
    # restore login credentials, permission/role fields, sessions, or 2FA.
    financial_fields = ('commission_percent', 'fixed_salary', 'per_appointment_fee', 'hire_date')
    for reference in data['staff_references']:
        user = (await db.execute(select(models.User).where(
            models.User.tenant_id == tenant_id, models.User.id == staff_mapping[reference['id']],
        ).with_for_update())).scalar_one()
        for key in financial_fields:
            setattr(user, key, _convert(models.User.__table__.c[key], reference[key]))
    await db.flush()
    return {name: len(data[name]) for name in order}, mapping
