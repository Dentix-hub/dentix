"""Explicit clinic business sections for the version-one archive format.

Identity, authorization, security/audit, platform and queued-operation records
are excluded. This registry is not by itself a restore engine.
"""

ARCHIVE_COLUMNS = {
    'appointments': frozenset('id patient_id doctor_id price_list_id date_time duration_minutes status notes is_deleted deleted_at tenant_id version_id'.split()),
    'attachments': frozenset('id tenant_id patient_id file_path filename file_type note created_at'.split()),
    'batches': frozenset('id material_id tenant_id batch_number expiry_date supplier cost_per_unit created_at'.split()),
    'care_observations': frozenset('id tenant_id patient_id care_session_id step_id work_item_id observation_code tooth_key structured_value notes recorded_at recorded_by_user_id created_at'.split()),
    'care_session_steps': frozenset('id tenant_id care_session_id work_item_id step_order step_code title status started_at completed_at notes version_id created_at updated_at'.split()),
    'care_sessions': frozenset('id tenant_id patient_id appointment_id provider_user_id status started_at finished_at notes version_id created_at updated_at'.split()),
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
    'next_visit_requests': frozenset('id tenant_id patient_id care_session_id work_item_id requested_by_user_id reason suggested_duration_minutes preferred_time_window_start preferred_time_window_end status notes created_at updated_at'.split()),
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
    'treatment_sessions': frozenset('id treatment_id session_date notes tenant_id'.split()),
    'treatments': frozenset('id patient_id tooth_number diagnosis procedure lab_choice doctor_id cost discount date canal_count canal_lengths sessions complications notes status tenant_id is_deleted deleted_at price_list_id unit_price price_snapshot'.split()),
    'warehouses': frozenset('id tenant_id name type'.split()),
    'workflow_templates': frozenset('id tenant_id template_code version title description is_active definition created_at updated_at'.split()),
}

STAFF_REFERENCE_SECTION = "staff_references"
STAFF_REFERENCE_COLUMNS = frozenset({"id", "username", "full_name", "email", "commission_percent", "fixed_salary", "per_appointment_fee", "hire_date"})

def validate_archive_sections(payload, *, tenant_id):
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
            if not isinstance(row, dict) or set(row) - allowed:
                raise ArchiveError('تحتوي النسخة الاحتياطية على بيانات غير مدعومة')
            row_id = row.get('id')
            if not isinstance(row_id, int) or isinstance(row_id, bool) or row_id <= 0 or row_id in ids:
                raise ArchiveError('معرّفات النسخة الاحتياطية غير صالحة')
            ids.add(row_id)
            if 'tenant_id' in allowed and row.get('tenant_id') != tenant_id:
                raise ArchiveError('النسخة الاحتياطية لا تخص هذه العيادة')
    return data
