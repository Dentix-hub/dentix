---
name: dentix-security-tenancy-rbac
description: Review or implement DENTIX changes involving authentication, authorization, roles, permissions, tenant isolation, patient visibility, doctor access, financial data, files, audit logs, or sensitive clinic information.
---

# DENTIX Security, Multi-Tenancy & RBAC Guide

## Security & Tenant Boundary Guardrails

### 1. Multi-Tenant Isolation
- **Tenant Scope Enforcement**: Every database query touching clinic data (patients, appointments, invoices, treatments, prescriptions) must be filtered by `tenant_id` via `tenant_scope.py`.
- **No ID-Only Lookups**: Never retrieve an entity by primary key alone (`GET /patients/{id}`) without matching against the active authenticated user's `tenant_id`.
- **Traversal & Joins**: Ensure foreign key traversal and joins cannot leak related entities belonging to other tenants.
- **Bulk Actions**: All batch inserts, updates, and deletes must strictly assert tenant boundaries.

### 2. Role-Based Access Control (RBAC)
- **Roles Hierarchy**: Support predefined clinic roles (`SUPER_ADMIN`, `CLINIC_OWNER`, `CLINIC_ADMIN`, `DOCTOR`, `RECEPTIONIST`, `ACCOUNTANT`).
- **Server-Side Enforcement**: Always enforce RBAC on FastAPI endpoints using security dependencies (`require_role`, `check_permission`). Never rely solely on frontend UI hiding.
- **Doctor Patient Visibility**: Respect clinic patient assignment logic. Ensure doctors only access authorized patient records while receptionists can manage scheduling across the clinic.

### 3. Financial & Clinical Data Protection
- **Financial Sensitivity**: Protect revenue, payments, doctor commission percentages, and expenses with strict administrative permissions.
- **PII & Medical Records**: Mask or protect patient national IDs, contact details, medical histories, and clinical notes.
- **Audit Logging**: Record structured audit logs for sensitive actions (user creation, role changes, patient record deletion, billing overrides).

### 4. AI Assistant Security Guardrails
- **Permission Bounded**: All AI tool executions and agent functions must inherit and obey the authenticated user's permissions and active `tenant_id`.
- **No Direct Injection**: Sanitize inputs to LLM prompts and validate tool execution payloads against Pydantic schemas.

## Verification Checklist
- Run tenant isolation test suite: `pytest backend/tests/test_tenant_scope.py backend/tests/test_multi_tenancy.py -v`.
- Verify RBAC test suite: `pytest backend/tests/test_rbac.py backend/tests/test_permissions.py -v`.
- Confirm audit logs and error handlers never leak credentials, secret tokens, or cross-tenant data.
