# DENTIX Database Migration Topology & Lineage

## 1. Executive Summary
This document records the exact Alembic migration graph, revision tree, branch points, merge points, and current head revision for the DENTIX database schema.

- **Current Head**: `d0e1f2a3b4c5` (add push_subscriptions with RLS)
- **Base Revision**: `ceb1e9e1108c` (add_system_errors_table)
- **Total Revisions**: 35 migration scripts
- **Merge Points**:
  - `b7c8d9e0f1a2` (Merges 4 branches: `6ce58b4d24ba`, `74e590e3094c`, `e0eb7ca469b9`, `e146e0d57b66`)
  - `f7a8b9c0d1e2` (Merges 2 branches: `a4b5c6d7e8f9`, `e4f5a6b7c8d9`)

---

## 2. Complete Chronological Lineage (Top-to-Bottom / Head-to-Base)

| Revision ID | Down Revision(s) | Type | Description |
|---|---|---|---|
| `d0e1f2a3b4c5` | `c9d0e1f2a3b4` | **HEAD** | Add `push_subscriptions` table with RLS |
| `c9d0e1f2a3b4` | `b8c9d0e1f2a3` | Standard | Repair legacy attachments schema (`notes` vs `note`) |
| `b8c9d0e1f2a3` | `a7b8c9d0e1f2` | Standard | Enforce RLS on `subscription_checkouts` |
| `a7b8c9d0e1f2` | `f6a7b8c9d0e1` | Standard | Encrypt persisted Google OAuth refresh tokens |
| `f6a7b8c9d0e1` | `e5f6a7b8c9d0` | Standard | Use exact numeric types (`Numeric(12,2)`) and financial invariants |
| `e5f6a7b8c9d0` | `d4e5f6a7b8c9` | Standard | Add material soft delete (`is_deleted`, `deleted_at`) |
| `d4e5f6a7b8c9` | `f2a4c6e8b0d1` | Standard | Enforce RLS on `subscription_payments` |
| `f2a4c6e8b0d1` | `c1d2e3f4a5b6` | Standard | Backfill finance event tenant IDs |
| `c1d2e3f4a5b6` | `c8d9e0f1a2b3` | Standard | Add patient workspace search indexes and age metadata |
| `c8d9e0f1a2b3` | `f7a8b9c0d1e2` | Standard | Add tenant timezone for business-day reporting |
| `f7a8b9c0d1e2` | `a4b5c6d7e8f9`, `e4f5a6b7c8d9` | **MERGEPOINT** | Merge production and HF staging migration histories |
| `a4b5c6d7e8f9` | `9f3a1c2d4e5f` | Standard | Make patient file numbers unique inside each tenant |
| `9f3a1c2d4e5f` | `0c0c38745bc3` | Standard | Secure subscription checkout and webhook processing |
| `e4f5a6b7c8d9` | `0c0c38745bc3` | Standard | Allow global procedures (`tenant_id` nullable) |
| `0c0c38745bc3` | `da377f438006` | **BRANCHPOINT** | Fix procedures name unique scope |
| `da377f438006` | `bf6c75e1c3d3` | Standard | Add soft delete to treatments |
| `bf6c75e1c3d3` | `b7c8d9e0f1a2` | Standard | Add RLS policies for tenant tables |
| `b7c8d9e0f1a2` | `6ce58b4d24ba`, `74e590e3094c`, `e0eb7ca469b9`, `e146e0d57b66` | **MERGEPOINT** | Phase 3 SaaS scaling tables |
| `74e590e3094c` | `e21aaee286c0` | Standard | Add domain events outbox (`domain_events`) |
| `e21aaee286c0` | `ded07d91ace9` | Standard | Add patient_id and disposal tracking to material_sessions |
| `ded07d91ace9` | `d15e940112dd` | Standard | Add usage and status tracking |
| `d15e940112dd` | `e5f6g7h8i9j0` | Standard | Add `contact_phone` to tenants |
| `e5f6g7h8i9j0` | `b0d1e2f3a4b5` | Standard | Add domain to tenants and tenant_id to appointments |
| `b0d1e2f3a4b5` | `6ce58b4d24ba` | Standard | Add `full_name` to users |
| `6ce58b4d24ba` | `a2b3c4d5e6f7` | **BRANCHPOINT** | Add `duration_minutes` to appointments |
| `a2b3c4d5e6f7` | `f1a2b3c4d5e6` | Standard | Add composite indexes for performance |
| `f1a2b3c4d5e6` | `4326f6d2f707` | Standard | Add material categories & treatment material usage |
| `4326f6d2f707` | `e146e0d57b66` | Standard | Add `fcm_token` to users |
| `e146e0d57b66` | `drop_ai_usage_logs` | **BRANCHPOINT** | Add system error missing columns |
| `drop_ai_usage_logs`| `a1b2c3d4e5f6` | Standard | Remove legacy AI usage logs |
| `a1b2c3d4e5f6` | `e0eb7ca469b9` | Standard | Add `version_id` to appointments |
| `e0eb7ca469b9` | `75f8ada5a00f` | **BRANCHPOINT** | Add missing AI and inventory tables |
| `75f8ada5a00f` | `225a616b0b3d` | Standard | Add `standard_price` |
| `225a616b0b3d` | `ceb1e9e1108c` | Standard | Add inventory tables |
| `ceb1e9e1108c` | `<base>` | **BASE** | Add system errors table |

---

## 3. Invariants & Rules
1. `alembic.ini` configuration must point to `backend/alembic` script location.
2. All migrations must be idempotent and support both PostgreSQL and SQLite dialect branching.
3. No migration script should hardcode cross-tenant queries without filtering by `tenant_id`.
