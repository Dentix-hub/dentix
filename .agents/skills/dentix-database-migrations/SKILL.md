---
name: dentix-database-migrations
description: Use for DENTIX SQLAlchemy, PostgreSQL, Alembic, schema, index, migration, query optimization, transaction, or data-integrity work.
---

# DENTIX Database & Alembic Migrations Guide

## Database Architecture
- **Engine**: PostgreSQL (Production) / SQLite or PostgreSQL (Testing/Dev).
- **ORM**: SQLAlchemy Async (`sqlalchemy.ext.asyncio`).
- **Migration Tool**: Alembic (`alembic`).

## Project Paths
- **Models**: `backend/models/`
- **Migrations**: `backend/alembic/versions/`
- **Alembic Config**: `backend/alembic.ini`
- **Database Config**: `backend/database.py`

## Migration Workflow & Best Practices

### 1. Schema Change Justification
- Only introduce database schema modifications when the feature explicitly requires new entities, columns, or relations.
- Review existing models in `backend/models/` and historical migrations in `backend/alembic/versions/` before creating new revisions.

### 2. Alembic Migration Creation
- Run Alembic from the directory/configuration expected by the existing project, using the existing `backend/alembic.ini` configuration.
- Always inspect the generated migration script:
  - Check `upgrade()` and `downgrade()` functions for completeness and symmetry.
  - Verify column types, default values, and foreign key constraints.
  - Ensure tenant columns (`tenant_id`) include non-nullable constraints and appropriate indices.

### 3. Data Safety & Non-Destructive Operations
- **Backward Compatibility**: Add new nullable columns or provide server defaults when altering tables with existing production data.
- **Index Strategy**: Evaluate composite indexes from measured query patterns and existing access paths. Common tenant-first patterns may be useful, but do not add indexes without evidence.
- **Never Edit Applied Migrations**: Never modify or delete previously committed migration revisions in the repository.

### Verification Checklist
- Run database model integration tests.
- Confirm schema diff contains zero unintended drops or type conversions.
