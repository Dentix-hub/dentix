# DENTIX Test Inventory & Baseline Verification

**Inventory Timestamp**: 2026-08-25T00:41:30Z  

---

## 1. Backend Tests (Pytest)
- **Command**: `cmd /c "set PYTHONPATH=. && uv run pytest backend/tests backend/ci_tests --collect-only -q"`
- **Collected**: 542 test items across 48 test modules
- **Notes**: Running pytest directly from repo root without `PYTHONPATH=.` produces `ModuleNotFoundError: No module named 'backend'` due to import paths. Execution must always include `PYTHONPATH=.`.

## 2. Frontend Tests (Vitest)
- **Command**: `npm.cmd test -- --run` (inside `frontend/`)
- **Status**: 62 test files passed, 258 tests passed (0 failures)
- **Duration**: ~140s

## 3. End-to-End Tests (Playwright)
- **Directory**: `frontend/e2e/`
- **Specs**: `staging-deployment-smoke.spec.ts`, mobile responsive specs
- **Harness**: Configured for local dev server / staging endpoints

## 4. Alembic & Migration Verification
- **Command**: `cmd /c "set PYTHONPATH=. && uv run alembic -c backend/alembic.ini heads"`
- **Current Head**: `d0e1f2a3b4c5`
- **Ephemeral PostgreSQL Suite**: `backend/tests/test_preflight_postgres_contract.py`

## 5. Security & Isolation Suites
- `backend/tests/test_tenant_isolation.py`
- `backend/tests/test_tenant_scope_verification.py`
- `backend/tests/test_rbac.py`
- `backend/ci_tests/test_auth_bootstrap_rls_probe.py`
- `backend/tests/test_security_headers.py`
- `backend/tests/test_push_subscriptions.py`
