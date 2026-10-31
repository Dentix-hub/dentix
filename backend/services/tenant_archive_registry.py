"""Explicit clinic business sections for the version-one archive format.

Identity, authorization, security/audit, platform and queued-operation records
are excluded. This registry is not by itself a restore engine.
"""

ARCHIVE_COLUMNS = {
    'appointments': frozenset('id patient_id doctor_id price_list_id date_time duration_minutes status notes is_deleted deleted_at tenant_id version_id'.split()),
    'attachments': frozenset('id tenant_id patient_id file_path filename file_type note created_at storage_provider storage_uuid drive_original_id drive_thumbnail_id original_size original_sha256 thumbnail_sha256 google_account_sub connection_generation storage_status'.split()),
    'batches': frozenset('id material_id tenant_id batch_number expiry_date supplier cost_per_unit created_at'.split()),
    'care_observations': frozenset('id tenant_id patient_id care_session_id step_id work_item_id observation_code tooth_key structured_value notes recorded_at recorded_by_user_id is_superseded superseded_by_id amendment_reason reference_source_session_id reference_source_date created_at'.split()),
    'care_session_steps': frozenset('id tenant_id care_session_id work_item_id step_order step_code logical_step_code occurrence_number template_step_id is_repeat repeat_reason title status started_at completed_at notes version_id created_at updated_at'.split()),
    'care_sessions': frozenset('id tenant_id patient_id appointment_id provider_user_id status started_at finished_at notes actual_visit_date recorded_by_user_id is_historical amends_session_id amendment_reason version_id created_at updated_at'.split()),
    'clinical_attachment_links': frozenset('id tenant_id attachment_id patient_id work_item_id care_session_id clinical_event_id tooth_key purpose_code notes created_at'.split()),
    'clinical_charges': frozenset('id tenant_id patient_id work_item_id care_session_id doctor_id legacy_treatment_id amount discount status notes version_id created_at updated_at'.split()),
    'clinical_event_targets': frozenset('id tenant_id event_id target_kind tooth_key surface_code root_id canal_id created_at'.split()),
    'clinical_events': frozenset('id tenant_id patient_id work_item_id care_session_id event_type occurred_at actor_user_id payload notes created_at'.split()),
    'clinical_projection_coverages': frozenset('id tenant_id patient_id domain status notes version_id created_at updated_at'.split()),
    'clinical_treatment_plan_items': frozenset('id tenant_id phase_id work_item_id item_order status notes version_id created_at updated_at'.split()),
    'clinical_treatment_plan_phases': frozenset('id tenant_id plan_id phase_order name status notes created_at updated_at'.split()),
    'clinical_treatment_plans': frozenset('id tenant_id patient_id title status notes created_by_user_id version_id created_at updated_at'.split()),
    'clinical_work_item_targets': frozenset('id tenant_id work_item_id target_kind tooth_key surface_code root_id canal_id created_at'.split()),
    'clinical_work_items': frozenset('id tenant_id patient_id kind code lab_choice status notes created_by_user_id version_id created_at updated_at'.split()),
    'expenses': frozenset('id item_name cost category date tenant_id notes'.split()),
    'insurance_providers': frozenset('id tenant_id name code contact_email contact_phone address notes is_active created_at'.split()),
    'lab_orders': frozenset('id patient_id laboratory_id work_item_id treatment_id work_type tooth_number shade material cost price_to_patient status notes order_date delivery_date received_date tenant_id doctor_id'.split()),
    'lab_payments': frozenset('id laboratory_id lab_order_id amount date notes method tenant_id'.split()),
    'laboratories': frozenset('id name phone address contact_person email specialties notes tenant_id is_active created_at'.split()),
    'material_learning_logs': frozenset('id tenant_id session_id material_id total_consumed calculation_data created_at'.split()),
    'material_sessions': frozenset('id tenant_id stock_item_id patient_id opened_at status is_disposed disposal_reason remaining_est current_uses doctor_id closed_at total_amount_consumed'.split()),
    'materials': frozenset('id tenant_id name type base_unit alert_threshold standard_price max_uses category_id brand packaging_ratio is_deleted deleted_at'.split()),
    'next_visit_requests': frozenset('id tenant_id patient_id care_session_id work_item_id requested_by_user_id reason suggested_duration_minutes preferred_time_window_start preferred_time_window_end status notes associated_work_item_ids assigned_doctor_id stopped_at stopped_reason stopped_by_user_id postponed_to_date postponed_reason postponed_by_user_id handoff_at handoff_reason handoff_by_user_id handoff_to_user_id created_at updated_at'.split()),
    'patients': frozenset('id name age phone email address medical_history notes created_at date_of_birth date_of_birth_precision age_recorded_at is_deleted deleted_at tenant_id assigned_doctor_id default_price_list_id'.split()),
    'payments': frozenset('id patient_id doctor_id amount date notes tenant_id'.split()),
    'prescriptions': frozenset('id tenant_id patient_id medications notes date'.split()),
    'price_list_items': frozenset('id price_list_id procedure_id price discount_percent insurance_code max_units requires_approval created_at updated_at'.split()),
    'price_lists': frozenset('id tenant_id name type description is_default is_active insurance_provider_id coverage_percent copay_percent copay_fixed effective_from effective_to created_at updated_at'.split()),
    'procedure_chart_styles': frozenset('id tenant_id procedure_name template color_key created_at updated_at'.split()),
    'procedure_material_weights': frozenset('id procedure_id material_id category_id tenant_id weight current_average_usage sample_size'.split()),
    'procedures': frozenset('id name code category price tenant_id'.split()),
    'salary_payments': frozenset('id user_id month amount payment_date is_partial days_worked notes tenant_id'.split()),
    'saved_medications': frozenset('id tenant_id name strength frequency duration default_dose notes created_at'.split()),
    'stock_items': frozenset('id warehouse_id batch_id tenant_id quantity'.split()),
    'stock_movements': frozenset('id tenant_id stock_item_id change_amount reason reference_id created_at performed_by'.split()),
    'tooth_status': frozenset('id tenant_id patient_id tooth_number condition notes'.split()),
    'treatment_material_usages': frozenset('id treatment_id care_session_id work_item_id material_id session_id weight_score quantity_used cost_calculated is_manual_override tenant_id created_at'.split()),
    'treatment_sessions': frozenset('id treatment_id session_date next_session_date notes tenant_id'.split()),
    'treatments': frozenset('id patient_id tooth_number diagnosis procedure lab_choice doctor_id cost discount date canal_count canal_lengths sessions complications notes status tenant_id is_deleted deleted_at price_list_id unit_price price_snapshot'.split()),
    'warehouses': frozenset('id tenant_id name type'.split()),
    'workflow_templates': frozenset('id tenant_id template_code version title description is_active definition created_at updated_at'.split()),
}

STAFF_REFERENCE_SECTION = "staff_references"
STAFF_REFERENCE_COLUMNS = frozenset({"id", "username", "full_name", "email", "commission_percent", "fixed_salary", "per_appointment_fee", "hire_date"})

def validate_archive_sections(payload, *, tenant_id, require_complete=True):
    """Reject unrecognized sections, columns, ownership and duplicate row IDs.

    Reference, type and live identity validation remain mandatory before any
    restore; successful section validation does not authorize mutation.
    """
    from backend.services.tenant_archive import ArchiveError

    if not isinstance(payload, dict) or not isinstance(payload.get('data'), dict):
        raise ArchiveError('محتوى النسخة الاحتياطية غير صالح')
    data = payload['data']
    required = set(ARCHIVE_COLUMNS) | {STAFF_REFERENCE_SECTION}
    if set(data) != required:
        raise ArchiveError('أقسام النسخة الاحتياطية غير مكتملة أو غير مدعومة')
    for section, rows in data.items():
        allowed = STAFF_REFERENCE_COLUMNS if section == STAFF_REFERENCE_SECTION else ARCHIVE_COLUMNS[section]
        if not isinstance(rows, list):
            raise ArchiveError('بيانات النسخة الاحتياطية غير صالحة')
        ids = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) - allowed or (require_complete and set(row) != allowed):
                raise ArchiveError('تحتوي النسخة الاحتياطية على بيانات غير مدعومة')
            row_id = row.get('id')
            if not isinstance(row_id, int) or isinstance(row_id, bool) or row_id <= 0 or row_id in ids:
                raise ArchiveError('معرّفات النسخة الاحتياطية غير صالحة')
            ids.add(row_id)
            if 'tenant_id' in allowed and row.get('tenant_id') != tenant_id:
                raise ArchiveError('النسخة الاحتياطية لا تخص هذه العيادة')
    return data


def validate_archive_references(data, *, tenant_id, external_ids=None):
    """Validate declared SQL foreign keys before beginning a restore transaction.

    External IDs must have been independently resolved against the current
    installation; archive contents never authorize them. JSON clinical event
    payload references also require format-specific validation before import.
    """
    from backend import models
    from backend.services.tenant_archive import ArchiveError

    external_ids = external_ids or {}
    if set(external_ids) - {'material_categories', 'procedures'}:
        raise ArchiveError('مرجع خارجي غير مدعوم في النسخة الاحتياطية', category='unsupported_external_reference')
    ids = {name: {row['id'] for row in rows} for name, rows in data.items()}
    ids['users'] = ids[STAFF_REFERENCE_SECTION]
    ids['tenants'] = {tenant_id}
    for name, rows in data.items():
        if name == STAFF_REFERENCE_SECTION:
            continue
        table = models.Base.metadata.tables[name]
        for column in table.columns:
            if column.name not in ARCHIVE_COLUMNS[name]:
                continue
            for foreign in column.foreign_keys:
                referenced = foreign.column.table.name
                if foreign.column.name != 'id':
                    raise ArchiveError(
                        f'مرجع غير مدعوم في النسخة الاحتياطية ({name}.{column.name})',
                        section=name, field=column.name, referenced_section=referenced,
                        category='unsupported_reference', counts=1,
                    )
                allowed = ids.get(referenced, set()) | set(external_ids.get(referenced, ()))
                type_mismatch_count = 0
                invalid_ref_count = 0
                for row in rows:
                    value = row.get(column.name)
                    if value is not None:
                        if not isinstance(value, int) or isinstance(value, bool):
                            type_mismatch_count += 1
                        elif value not in allowed:
                            invalid_ref_count += 1
                if type_mismatch_count > 0:
                    raise ArchiveError(
                        f'نوع أو قيمة غير صالحة في النسخة الاحتياطية ({name}.{column.name})',
                        section=name, field=column.name, referenced_section=referenced,
                        category='invalid_reference_type', counts=type_mismatch_count,
                    )
                if invalid_ref_count > 0:
                    raise ArchiveError(
                        f'تحتوي النسخة الاحتياطية على مرجع غير صالح ({name}.{column.name})',
                        section=name, field=column.name, referenced_section=referenced,
                        category='invalid_reference', counts=invalid_ref_count,
                    )


def _is_valid_scalar(kind, value):
    import math
    from datetime import date, datetime
    from decimal import Decimal, InvalidOperation
    from sqlalchemy import Boolean, Date, DateTime, Float, Integer, Numeric, String

    if value is None:
        return True
    try:
        if isinstance(kind, Boolean):
            return isinstance(value, bool)
        if isinstance(kind, Integer):
            return isinstance(value, int) and not isinstance(value, bool)
        if isinstance(kind, Float):
            return isinstance(value, (int, float, str)) and not isinstance(value, bool) and math.isfinite(float(value))
        if isinstance(kind, Numeric):
            return isinstance(value, (str, int)) and not isinstance(value, bool) and Decimal(value).is_finite()
        if isinstance(kind, DateTime):
            return isinstance(value, str) and bool(datetime.fromisoformat(value.replace('Z', '+00:00')))
        if isinstance(kind, Date):
            return isinstance(value, str) and bool(date.fromisoformat(value))
        if isinstance(kind, String):
            return isinstance(value, str) and (kind.length is None or len(value) <= kind.length)
        return True
    except (ValueError, TypeError, OverflowError, InvalidOperation):
        return False


def validate_archive_values(data):
    """Validate scalar database column types before any destructive operation.

    Business rules, nested JSON semantics and identity mapping must also be
    checked by the restore coordinator before this data is imported.
    """
    from backend import models
    from backend.services.tenant_archive import ArchiveError

    for name, rows in data.items():
        table = models.User.__table__ if name == STAFF_REFERENCE_SECTION else models.Base.metadata.tables[name]
        for row in rows:
            for key, value in row.items():
                column = table.c[key]
                if value is None:
                    if not column.nullable and not column.primary_key:
                        missing_count = sum(1 for r in rows if r.get(key) is None)
                        raise ArchiveError(
                            f'قيمة مطلوبة مفقودة في النسخة الاحتياطية ({name}.{key})',
                            section=name, field=key, category='missing_required_value', counts=missing_count,
                        )
                    continue
                kind = column.type
                if not _is_valid_scalar(kind, value):
                    invalid_count = sum(1 for r in rows if not _is_valid_scalar(table.c[key].type, r.get(key)))
                    raise ArchiveError(
                        f'نوع أو قيمة غير صالحة في النسخة الاحتياطية ({name}.{key})',
                        section=name, field=key, category='invalid_value_type', counts=invalid_count,
                    )


async def validate_archive_compatibility(db, payload, *, tenant_id, external_ids=None):
    """Run all non-destructive restore preflight checks on an archive payload.

    Validates section completeness, scalar values/types, attachment metadata,
    SQL foreign keys, embedded JSON payload references, and staff mapping.
    Raises ArchiveError with safe structured diagnostics if incompatible.
    """
    from backend.services.tenant_archive_attachments import validate_attachment_metadata
    from backend.services.tenant_archive_embedded_refs import validate_embedded_references
    from backend.services.tenant_archive_identity import resolve_staff_mapping
    from backend.services.tenant_archive_legacy import ensure_missing_sections_empty, missing_legacy_sections
    from backend.services.tenant_restore_coordinator import known_global_references

    if external_ids is None:
        external_ids = await known_global_references(db)
    missing = missing_legacy_sections(payload)
    data = validate_archive_sections(payload, tenant_id=tenant_id)
    await ensure_missing_sections_empty(db, tenant_id=tenant_id, missing_sections=missing)
    validate_archive_values(data)
    validate_attachment_metadata(data, tenant_id)
    validate_archive_references(data, tenant_id=tenant_id, external_ids=external_ids)
    validate_embedded_references(data, tenant_id=tenant_id, external_ids=external_ids)
    staff_mapping = await resolve_staff_mapping(db, tenant_id, data['staff_references'])
    return data, staff_mapping
