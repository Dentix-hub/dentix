---
name: dentix-database-migrations
description: Use for DENTIX SQLAlchemy, PostgreSQL, Alembic, schema, index, migration, query optimization, transaction, or data-integrity work.
---

# DENTIX Database & Alembic Migrations Guide

## Database Architecture
- **Engine**: PostgreSQL (Production) / SQLite or PostgreSQL (Testing/Dev).
- **ORM**: SQLAlchemy Async (`sqlalchemy.ext.asyncio`).
- **Migration Tool**: Alembic (`alembic`).

## Migration Workflow & Best Practices

### 1. Schema Change Justification
- Only introduce database schema modifications when the feature explicitly requires new entities, columns, or relations.
- Review existing models in `backend/app/models/` and historical migrations in `backend/alembic/versions/` before creating new revisions.

### 2. Alembic Migration Creation
- Generate new revision with descriptive messages:
  ```bash
  alembic revision --autogenerate -m "add_appointment_reminder_status"
  ```
- Always inspect the generated migration script:
  - Check `upgrade()` and `downgrade()` functions for completeness and symmetry.
  - Verify column types, default values, and foreign key constraints.
  - Ensure tenant columns (`tenant_id`) include non-nullable constraints and appropriate indices.

### 3. Data Safety & Non-Destructive Operations
- **Backward Compatibility**: Add new nullable columns or provide server defaults when altering tables with existing production data.
- **Index Strategy**: Create compound indices for common filter patterns (e.g., `(tenant_id, created_at)`, `(tenant_id, doctor_id)`).
- **Never Edit Applied Migrations**: Never modify or delete previously committed migration revisions in the repository.

### Verification Checklist
- Run migration syntax check: `pytest backend/tests/test_migrations.py` or verify import validity.
- Run database model integration tests.
- Confirm schema diff contains zero unintended drops or type conversions.
