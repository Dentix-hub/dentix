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
- **Role Definitions**: Use the role/permission definitions in the current backend as the source of truth. Confirmed roles include `SUPER_ADMIN`, `CLINIC_OWNER`, `CLINIC_ADMIN`, `DOCTOR`, `RECEPTIONIST`, and `ACCOUNTANT`.
- **Server-Side Enforcement**: Always enforce RBAC on FastAPI endpoints using the existing authentication and RBAC dependencies/helpers already used by nearby routers (e.g., `get_current_user`, `check_permission`). Never rely solely on frontend UI hiding.
- **Doctor Patient Visibility**: Do not broaden doctor visibility as a shortcut. Do not hide patients created by reception staff when the doctor's authorized visibility rules permit access. The backend implementation is the source of truth for visibility behavior.

### 3. Financial & Clinical Data Protection
- **Financial Sensitivity**: Protect revenue, payments, doctor commission percentages, and expenses with strict administrative permissions.
- **PII & Medical Records**: Mask or protect patient national IDs, contact details, medical histories, and clinical notes.
- **Audit Logging**: Record structured audit logs for sensitive actions (user creation, role changes, patient record deletion, billing overrides).

### 4. AI Assistant Security Guardrails
- **Permission Bounded**: All AI tool executions and agent functions must inherit and obey the authenticated user's permissions and active `tenant_id`.
- **No Direct Injection**: Sanitize inputs to LLM prompts and validate tool execution payloads against Pydantic schemas.

## Verification Checklist

1. Discover relevant existing security tests before running them:
   - Search `backend/tests/` for tenant, RBAC, permission, role, visibility, authentication, patient-access, finance-access, and cross-tenant coverage.
2. Run the smallest relevant test set first.
3. For security-sensitive changes, expand to the broader backend security/RBAC suite before completion.
4. `backend/tests/test_rbac.py` may be used when relevant because it exists in the repository.
5. Never invent a test filename or report an unexecuted test as passed.
6. Confirm audit logs and error handlers never leak credentials, secret tokens, or cross-tenant data.
