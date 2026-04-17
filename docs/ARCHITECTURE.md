# Dentix — Architecture Guide

## Layer Map

```
HTTP Request
    ↓
FastAPI Router (routers/)          ← validation only, ≤15 lines/endpoint
    ↓
Service Layer (services/)          ← all business logic
    ↓
CRUD Layer (crud/)                 ← raw DB operations
    ↓
SQLAlchemy Models (models/)        ← schema + relationships
    ↓
PostgreSQL Database
```

## Multi-Tenancy Strategy

Every request carries a `tenant_id` (set by `TenantMiddleware`).
The `tenant_scope.py` event listener auto-injects
`.filter(Model.tenant_id == current_tenant_id)` on every ORM query.

Super Admin bypasses this via `set_super_admin_bypass(True)`.

## RBAC Matrix

| Permission | admin | manager | doctor | receptionist | nurse | accountant | assistant |
|-----------|:-----:|:-------:|:------:|:------------:|:-----:|:----------:|:--------:|
| PATIENT_CREATE | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| CLINICAL_WRITE | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| FINANCIAL_WRITE | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| SYSTEM_CONFIG | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Key Design Decisions

- **async-first**: FastAPI routes are sync wrappers where needed; services are sync SQLAlchemy
- **tenant_scope**: uses SQLAlchemy `do_orm_execute` event — auto, not manual
- **auth.py**: canonical JWT utilities — used by tests, scripts, and routers
- **AIUsageLog**: type alias for AILog in models/__init__.py — legacy code works unchanged
