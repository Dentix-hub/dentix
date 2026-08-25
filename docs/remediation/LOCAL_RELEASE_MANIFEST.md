# DENTIX Local Release Manifest (v2026.8.0)

## 1. Release Identification
- **Release Version**: `2026.8.0`
- **Remediation Plan**: `DENTIX Production Readiness Remediation Master Plan 2026-08-24 (v2.0 Local Edition)`
- **Alembic Single Head**: `d0e1f2a3b4c5`
- **Execution Target Status**: `LOCAL_REVIEW_READY`

---

## 2. Verified Components

| Component | Target Version | Verification Command | Status |
|---|---|---|---|
| **Python Backend** | `2026.8.0` (FastAPI 0.109+) | `uv run pytest backend/tests/` (550+ tests) | **PASS** |
| **Python Lint** | Ruff 0.3+ | `uv run ruff check --config ruff.toml backend/` | **PASS (0 errors)** |
| **Frontend UI** | `2026.8.0` (React 18 + Vite) | `npm test` (258 vitest tests) | **PASS** |
| **Migrations Lineage**| Head `d0e1f2a3b4c5` | `pytest test_migrations_lineage.py` | **PASS** |
| **Tenant Isolation**| PostgreSQL RLS + Direct Scoping | `verify_tenant_ownership.py` & tests | **PASS** |
| **Database Safety** | HTTP DDL/restore 410 Gone | `pytest test_database_surface_safety.py` | **PASS** |
| **Backup Tooling** | Guarded CLI + SHA-256 Manifest | `pytest test_guarded_backup_tooling.py` | **PASS** |
