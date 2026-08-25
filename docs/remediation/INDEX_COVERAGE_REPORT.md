# DENTIX Database Index Coverage Report

## Verified additions

The migration chain contains targeted indexes for high-value tenant/search/work-queue paths. Revision `e1f2a3b4c5d6` additionally creates `tenant_id` indexes for `tooth_status`, `prescriptions`, `attachments`, `material_sessions`, and `stock_movements`; revision `e2f3a4b5c6d7` indexes `subscription_renewal_requests.tenant_id` and enforces uniqueness of `(tenant_id, idempotency_key)`.

| Table/path | Representative index | Intended query |
|---|---|---|
| `patients` | `(tenant_id, is_deleted)` | active patient directory |
| `patients` | `(tenant_id, name_search_normalized)` | normalized tenant search |
| `patients` | `(tenant_id, phone_search_hash)` | blind phone lookup |
| `treatments` | `(patient_id, date)` / `(doctor_id, date)` | clinical history and doctor reports |
| `appointments` | `(doctor_id, date_time)` | doctor schedule |
| `domain_events` | `(status, available_at)` | outbox claiming |
| newly direct-owned child tables | `(tenant_id)` | RLS-compatible tenant access |

This is a schema inventory, not proof that every production query uses an optimal plan. PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` on representative production-like data remains a pre-production performance gate.
