# Backup model inventory — preliminary

Generated from SQLAlchemy metadata on the local combined branch. This is an inventory, not an inclusion or restore-coverage claim. Each table still needs an explicit business/security classification, column allowlist, ownership analysis, and round-trip tests. Tables without tenant_id are included because ownership can be indirect.

| Table | Tenant column | Columns | Foreign-key tables | Classification and restore coverage |
|---|---|---|---|---|
| `ai_logs` | yes | id, trace_id, tenant_id, user_id, intent, tool, model, input_text, output_text, tool_params, tool_result, execution_time_ms, tokens_in, tokens_out, cost, confidence, status, error_type, error_details, policy_check, scribe_mode, username, created_at, timestamp | users | Pending |
| `appointments` | yes | id, patient_id, doctor_id, price_list_id, date_time, duration_minutes, status, notes, is_deleted, deleted_at, tenant_id, version_id | patients, price_lists, tenants, users | Pending |
| `attachments` | yes | id, tenant_id, patient_id, file_path, filename, file_type, note, created_at | patients, tenants | Pending |
| `audit_logs` | yes | id, action, entity_type, entity_id, target_user_id, target_username, performed_by_id, performed_by_username, old_value, new_value, details, tenant_id, created_at | tenants, users | Pending |
| `background_jobs` | yes | id, job_name, status, started_at, completed_at, duration_seconds, error_message, triggered_by, tenant_id | — | Pending |
| `batches` | yes | id, material_id, tenant_id, batch_number, expiry_date, supplier, cost_per_unit, created_at | materials, tenants | Pending |
| `blocked_ips` | no | id, ip_address, reason, blocked_by, created_at, expires_at | — | Pending |
| `care_observations` | yes | id, tenant_id, patient_id, care_session_id, step_id, work_item_id, observation_code, tooth_key, structured_value, notes, recorded_at, recorded_by_user_id, created_at | care_session_steps, care_sessions, clinical_work_items, patients, tenants, users | Pending |
| `care_session_steps` | yes | id, tenant_id, care_session_id, work_item_id, step_order, step_code, title, status, started_at, completed_at, notes, version_id, created_at, updated_at | care_sessions, clinical_work_items, tenants | Pending |
| `care_sessions` | yes | id, tenant_id, patient_id, appointment_id, provider_user_id, status, started_at, finished_at, notes, version_id, created_at, updated_at | appointments, patients, tenants, users | Pending |
| `clinical_attachment_links` | yes | id, tenant_id, attachment_id, patient_id, work_item_id, care_session_id, clinical_event_id, tooth_key, purpose_code, notes, created_at | attachments, care_sessions, clinical_events, clinical_work_items, patients, tenants | Pending |
| `clinical_charges` | yes | id, tenant_id, patient_id, work_item_id, care_session_id, doctor_id, legacy_treatment_id, amount, discount, status, notes, version_id, created_at, updated_at | care_sessions, clinical_work_items, patients, tenants, treatments, users | Pending |
| `clinical_event_targets` | yes | id, tenant_id, event_id, target_kind, tooth_key, surface_code, root_id, canal_id, created_at | clinical_events, tenants | Pending |
| `clinical_events` | yes | id, tenant_id, patient_id, work_item_id, care_session_id, event_type, occurred_at, actor_user_id, payload, notes, created_at | care_sessions, clinical_work_items, patients, tenants, users | Pending |
| `clinical_projection_coverages` | yes | id, tenant_id, patient_id, domain, status, notes, version_id, created_at, updated_at | patients, tenants | Pending |
| `clinical_treatment_plan_items` | yes | id, tenant_id, phase_id, work_item_id, item_order, status, notes, version_id, created_at, updated_at | clinical_treatment_plan_phases, clinical_work_items, tenants | Pending |
| `clinical_treatment_plan_phases` | yes | id, tenant_id, plan_id, phase_order, name, status, notes, created_at, updated_at | clinical_treatment_plans, tenants | Pending |
| `clinical_treatment_plans` | yes | id, tenant_id, patient_id, title, status, notes, created_by_user_id, version_id, created_at, updated_at | patients, tenants, users | Pending |
| `clinical_work_item_targets` | yes | id, tenant_id, work_item_id, target_kind, tooth_key, surface_code, root_id, canal_id, created_at | clinical_work_items, tenants | Pending |
| `clinical_work_items` | yes | id, tenant_id, patient_id, kind, code, status, notes, created_by_user_id, version_id, created_at, updated_at | patients, tenants, users | Pending |
| `daily_system_stats` | no | date, total_tenants, active_tenants, new_tenants, total_revenue, api_error_rate | — | Pending |
| `domain_events` | yes | id, tenant_id, event_type, aggregate_type, aggregate_id, payload, status, attempts, max_attempts, error_message, available_at, created_at, processed_at | — | Pending |
| `expenses` | yes | id, item_name, cost, category, date, tenant_id, notes | tenants | Pending |
| `feature_flags` | no | id, key, description, is_global_enabled, rollout_percentage | — | Pending |
| `insurance_providers` | yes | id, tenant_id, name, code, contact_email, contact_phone, address, notes, is_active, created_at | tenants | Pending |
| `lab_orders` | yes | id, patient_id, laboratory_id, work_item_id, treatment_id, work_type, tooth_number, shade, material, cost, price_to_patient, status, notes, order_date, delivery_date, received_date, tenant_id, doctor_id | clinical_work_items, laboratories, patients, tenants, treatments, users | Pending |
| `lab_payments` | yes | id, laboratory_id, lab_order_id, amount, date, notes, method, tenant_id | lab_orders, laboratories, tenants | Pending |
| `laboratories` | yes | id, name, phone, address, contact_person, email, specialties, notes, tenant_id, is_active, created_at | tenants | Pending |
| `login_history` | no | id, user_id, ip_address, user_agent, status, created_at | users | Pending |
| `material_categories` | no | id, name_en, name_ar, default_type, default_unit | — | Pending |
| `material_learning_logs` | yes | id, tenant_id, session_id, material_id, total_consumed, calculation_data, created_at | material_sessions, materials, tenants | Pending |
| `material_sessions` | yes | id, tenant_id, stock_item_id, patient_id, opened_at, status, is_disposed, disposal_reason, remaining_est, current_uses, doctor_id, closed_at, total_amount_consumed | patients, stock_items, tenants, users | Pending |
| `materials` | yes | id, tenant_id, name, type, base_unit, alert_threshold, standard_price, max_uses, category_id, brand, packaging_ratio, is_deleted, deleted_at | material_categories, tenants | Pending |
| `next_visit_requests` | yes | id, tenant_id, patient_id, care_session_id, work_item_id, requested_by_user_id, reason, suggested_duration_minutes, preferred_time_window_start, preferred_time_window_end, status, notes, created_at, updated_at | care_sessions, clinical_work_items, patients, tenants, users | Pending |
| `notification_reads` | no | id, user_id, notification_id, read_at, is_deleted | notifications, users | Pending |
| `notifications` | yes | id, title, content, type, is_global, tenant_id, created_at, created_by_id | tenants, users | Pending |
| `password_reset_tokens` | no | id, token, user_id, expires_at, used, created_at | users | Pending |
| `patients` | yes | id, name, age, phone, email, address, medical_history, notes, created_at, name_search_normalized, phone_search_hash, date_of_birth, date_of_birth_precision, age_recorded_at, is_deleted, deleted_at, tenant_id, assigned_doctor_id, default_price_list_id | price_lists, tenants, users | Pending |
| `payments` | yes | id, patient_id, doctor_id, amount, date, notes, tenant_id | patients, tenants, users | Pending |
| `prescriptions` | yes | id, tenant_id, patient_id, medications, notes, date | patients, tenants | Pending |
| `price_list_items` | no | id, price_list_id, procedure_id, price, discount_percent, insurance_code, max_units, requires_approval, created_at, updated_at | price_lists, procedures | Pending |
| `price_lists` | yes | id, tenant_id, name, type, description, is_default, is_active, insurance_provider_id, coverage_percent, copay_percent, copay_fixed, effective_from, effective_to, created_at, updated_at | insurance_providers, tenants | Pending |
| `procedure_chart_styles` | yes | id, tenant_id, procedure_name, template, color_key, created_at, updated_at | tenants | Pending |
| `procedure_material_weights` | yes | id, procedure_id, material_id, category_id, tenant_id, weight, current_average_usage, sample_size | material_categories, materials, procedures, tenants | Pending |
| `procedures` | yes | id, name, code, category, price, tenant_id | tenants | Pending |
| `push_subscriptions` | yes | id, user_id, tenant_id, provider, endpoint, p256dh_key, auth_key, provider_token, device_installation_id, session_sid, platform, browser_family, created_at, updated_at, last_seen_at, revoked_at, is_active | tenants, users | Pending |
| `salary_payments` | yes | id, user_id, month, amount, payment_date, is_partial, days_worked, notes, tenant_id | tenants, users | Pending |
| `saved_medications` | yes | id, tenant_id, name, strength, frequency, duration, default_dose, notes, created_at | tenants | Pending |
| `security_events` | yes | id, tenant_id, user_id, event_type, severity, description, details, ip_address, user_agent, timestamp | users | Pending |
| `stock_items` | yes | id, warehouse_id, batch_id, tenant_id, quantity | batches, tenants, warehouses | Pending |
| `stock_movements` | yes | id, tenant_id, stock_item_id, change_amount, reason, reference_id, created_at, performed_by | stock_items, tenants, users | Pending |
| `subscription_checkouts` | yes | id, provider_reference, tenant_id, plan_id, provider, expected_amount, currency, status, expires_at, provider_payment_id, processed_at, created_at | subscription_plans, tenants | Pending |
| `subscription_payments` | yes | id, tenant_id, plan_id, amount, payment_method, payment_date, notes, created_by, paid_by, provider, provider_payment_id, provider_status | subscription_plans, tenants | Pending |
| `subscription_plans` | no | id, name, display_name_ar, price, duration_days, max_users, max_patients, features, is_ai_enabled, ai_daily_limit, ai_features, is_default, is_active, created_at | — | Pending |
| `subscription_renewal_requests` | yes | id, tenant_id, idempotency_key, request_hash, response_json, created_by_id, created_at | tenants, users | Pending |
| `support_messages` | yes | id, user_id, tenant_id, subject, message, priority, status, created_at | tenants, users | Pending |
| `system_errors` | yes | id, level, source, message, stack_trace, path, method, user_id, tenant_id, user_agent, ip_address, created_at | — | Pending |
| `system_settings` | no | key, value, description, updated_at | — | Pending |
| `tenant_features` | yes | id, tenant_id, feature_key, is_enabled | feature_flags, tenants | Pending |
| `tenants` | no | id, name, logo, subscription_status, grace_period_until, auto_suspend_at, payment_failed_count, manual_override_reason, subscription_end_date, plan, plan_id, domain, timezone, is_active, created_at, total_revenue, backup_frequency, google_refresh_token, last_backup_at, last_login, doctor_name, doctor_title, clinic_address, clinic_phone, contact_phone, print_header_image, print_footer_image, is_deleted, deleted_at | subscription_plans | Pending |
| `tooth_status` | yes | id, tenant_id, patient_id, tooth_number, condition, notes | patients, tenants | Pending |
| `treatment_material_usages` | yes | id, treatment_id, care_session_id, work_item_id, material_id, session_id, weight_score, quantity_used, cost_calculated, is_manual_override, tenant_id, created_at | care_sessions, clinical_work_items, material_sessions, materials, tenants, treatments | Pending |
| `treatment_sessions` | yes | id, treatment_id, session_date, notes, tenant_id | tenants, treatments | Pending |
| `treatments` | yes | id, patient_id, tooth_number, diagnosis, procedure, doctor_id, cost, discount, date, canal_count, canal_lengths, sessions, complications, notes, status, tenant_id, is_deleted, deleted_at, price_list_id, unit_price, price_snapshot | patients, price_lists, tenants, users | Pending |
| `user_onboarding_state` | yes | id, tenant_id, user_id, dismissed, seen_tips, events, updated_at | tenants, users | Pending |
| `user_sessions` | no | id, user_id, token_hash, ip_address, user_agent, device_info, last_active_at, expires_at, is_active, remember_me, created_at | users | Pending |
| `users` | yes | id, username, full_name, email, hashed_password, failed_login_attempts, last_failed_login, account_locked_until, is_2fa_enabled, otp_secret, active_session_id, role, permissions, tenant_id, fcm_token, patient_visibility_mode, can_view_other_doctors_history, commission_percent, fixed_salary, per_appointment_fee, hire_date, is_active, is_deleted, deleted_at | tenants | Pending |
| `warehouses` | yes | id, tenant_id, name, type | tenants | Pending |
| `workflow_templates` | yes | id, tenant_id, template_code, version, title, description, is_active, definition, created_at, updated_at | tenants | Pending |
