# DENTIX Local Release Manifest (v2026.8.0)

## Identification

- **Release version**: `2026.8.0`
- **Branch**: `local/readiness-remediation-20260825-0338`
- **Baseline**: `e507691f`
- **Alembic single head**: `e3a4b5c6d7e8`
- **Status**: `PARTIAL — LOCAL_VALIDATION_PASS / POSTGRES_CI_REQUIRED`

## Verification matrix

| Component | Command/evidence | Status |
|---|---|---|
| Python backend unit/integration tests (SQLite/local) | CI-equivalent coverage command, `--cov-fail-under=52` | PASS: 626 passed, 4 skipped; 65.13% coverage |
| Backend lint | `ruff check --config ruff.toml backend` | PASS |
| Frontend lint | `npm run lint` | PASS |
| Frontend tests | `npm test -- --run` (62 files / 258 tests) | PASS |
| Migration lineage | `test_migrations_lineage.py`; head `e3a4b5c6d7e8` | PASS (static/local) |
| Tenant model/RLS contract | parity and tenant-scope tests | PASS (static/SQLite) |
| Native RLS role split | static contract plus PostgreSQL negative probe | PASS (static); REQUIRED IN PG CI |
| Production changed-content scan | `scan_changed_content.py --base-ref e507691f --exclude-test-fixtures .` | PASS |
| Encrypted SQLite backup/restore | `test_guarded_backup_tooling.py` | PASS |
| Durable backup scheduler | `test_backup_scheduler.py` | PASS: 9 tests |
| Real PostgreSQL migration/RLS/HTTP isolation | CI PostgreSQL service and `backend/ci_tests/` | REQUIRED, NOT LOCAL |
| PostgreSQL `pg_dump`/`pg_restore` round trip | pre-production recovery exercise | REQUIRED, NOT LOCAL |

This manifest is a local review artifact, not a deployment authorization.
