---
name: dentix-backend-fastapi
description: Implement or review DENTIX FastAPI/Python backend work involving routers, services, CRUD, schemas, domain logic, background tasks, or backend integrations.
---

# DENTIX Backend Architecture & FastAPI Guide

## Architecture Flow
DENTIX follows a strict layered backend pattern:
```text
Router -> Service -> CRUD -> Database (SQLAlchemy Async / PostgreSQL)
```

### 1. Routers (`backend/app/api/`)
- Handle HTTP semantics, URL routing, request parsing, and status codes.
- Define OpenAPI schemas and request validation via Pydantic.
- Act as the entry boundary for authentication (`get_current_user`) and RBAC permissions (`require_role`, `check_permission`).
- Delegate all business and domain logic immediately to the Service layer.

### 2. Services (`backend/app/services/`)
- Contain all business logic, workflow orchestration, validation rules, and calculations.
- Maintain and propagate multi-tenant context (`tenant_id`).
- Coordinate cross-module operations, event notifications, background jobs, and external integrations.
- Never write raw SQL directly in services; invoke the CRUD layer.

### 3. CRUD (`backend/app/crud/`)
- Encapsulate database query building, joins, filtering, and persistence.
- Enforce tenant isolation in all queries using tenant scope utilities (`tenant_scope.py`).
- Use SQLAlchemy Async session methods (`select`, `execute`, `scalars`).

### 4. Schemas (`backend/app/schemas/`)
- Define Pydantic models for request validation and response serialization.
- Separate base, create, update, and response models.
- Ensure sensitive internal fields (passwords, internal tenant keys, audit hashes) are never exposed.

## Critical Backend Rules
- **Tenant Scope Integrity**: Never bypass `tenant_scope.py`. Every query touching tenant-scoped tables must filter by `tenant_id`.
- **Async Execution**: Ensure all database I/O, external network calls, and background jobs are asynchronous (`async`/`await`).
- **Data Visibility**: Inspect role and doctor assignments on any endpoint that accesses patient records or clinical summaries.
- **Error Handling**: Use standard `HTTPException` with informative error codes and user-friendly detail messages. Never swallow exceptions silently.
- **Schema Safety**: Do not modify existing database models or migration files unless explicitly justified by the task.

## Verification Checklist
- Run targeted pytest suites: `pytest backend/tests/test_<module>.py -v`.
- Check tenant isolation with multi-tenant test cases.
- Verify that coverage meets repository CI thresholds (70% minimum).
