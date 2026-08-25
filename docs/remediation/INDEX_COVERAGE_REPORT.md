# DENTIX Database Index Coverage & Integrity Report

## 1. Index Audit Summary
All tenant-scoped tables feature B-tree indexes on `tenant_id` alongside composite performance indexes.

---

## 2. Key Table Indexes

| Table | Index Name | Indexed Columns | Purpose |
|---|---|---|---|
| `patients` | `idx_patients_tenant_deleted` | `(tenant_id, is_deleted)` | Active patient list filtering |
| `patients` | `idx_patients_name_norm` | `(tenant_id, name_search_normalized)` | Privacy-safe name search |
| `patients` | `idx_patients_phone_hash` | `(tenant_id, phone_search_hash)` | Blind phone lookups |
| `treatments` | `idx_treatment_patient_date` | `(patient_id, date)` | Patient clinical history |
| `treatments` | `idx_treatment_doctor_date` | `(doctor_id, date)` | Doctor performance reports |
| `appointments` | `idx_appointment_doctor_date`| `(doctor_id, date_time)` | Doctor schedule view |
| `domain_events`| `ix_domain_events_status` | `(status, available_at)` | Outbox worker claim queue |
| `push_subscriptions`| `ix_push_subscriptions_session_sid` | `session_sid` | PWA session push routing |
