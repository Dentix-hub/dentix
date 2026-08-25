# DENTIX Production Readiness Remediation — Final Verification Dossier

## Executive status

- **Implementation status**: `DONE` for the locally actionable remediation scope.
- **Release-readiness status**: `PARTIAL — LOCAL_VALIDATION_PASS / POSTGRES_CI_REQUIRED`.
- **Branch**: `local/readiness-remediation-20260825-0338`.
- **Baseline**: `e507691f`.
- **Hosted/remote mutations**: none.

The earlier `LOCAL_REVIEW_READY` statement was too broad. The local machine has no available PostgreSQL/Docker runtime, so real PostgreSQL migration, FORCE-RLS, cross-tenant HTTP, and `pg_dump`/`pg_restore` round-trip gates remain mandatory before release approval. These gates are wired into `.github/workflows/ci.yml`; they have not been represented here as locally executed.

## Completed remediation

| Area | Result | Local evidence |
|---|---|---|
| Tenant ownership and RLS | Added direct tenant ownership and FORCE-RLS for the five previously indirect child tables; removed every application-controlled bypass clause; privileged operations now require a physically separate native `BYPASSRLS` role | tenant/RLS contract suites, `test_rls_bypass_role_contract.py`; PostgreSQL negative probes added under `backend/ci_tests/` |
| Manual renewal | Durable tenant-scoped idempotency record, request-hash conflict detection, tenant row lock, preserved `is_active`, audit event | `test_manual_renewal.py` |
| AI egress | Central default-deny policy; de-identification and contracted-processing modes; provider calls receive policy-approved messages only | `test_ai_egress_policy.py`, `test_ai_deidentification.py` |
| Backup and restore | Real SQLite/`pg_dump` snapshots, AES-256-GCM manifest 2.1, native format/schema validation, empty-target enforcement, and durable singleton scheduling with job outcomes | `test_guarded_backup_tooling.py`, `test_backup_scheduler.py` |
| Network and observability | Trusted-proxy client IP parsing, rate-limit default off, protected/off metrics modes, bounded sanitized logging, signed metadata-only alert webhook | `test_client_ip_and_limiter.py`, `verify_metrics.py`, `test_logging_sanitizer.py`, `test_alert_dispatch_service.py` |
| Dangerous surfaces and UI | Raw database HTTP operations remain retired; dead admin handlers removed; subscription lint warning removed | `test_database_surface_safety.py`, frontend lint/tests |
| Migration lineage | Single head `e3a4b5c6d7e8`; ownership and bypass-removal migrations are intentionally irreversible where rollback would restore a known tenant-isolation exposure | `test_migrations_lineage.py` |
| Changed-content scan | Added-line scan from a base revision, redacted findings, untracked-file coverage, explicit separation of synthetic test canaries | `test_scan_changed_content.py` and production-diff scan |

## Verification scorecard

- **Backend focused regression set**: passing.
- **Backend full suite**: 626 passed, 4 skipped (630 collected); 65.13% coverage against the 52% CI gate.
- **Backend Ruff gate**: `ruff check --config ruff.toml backend` passes.
- **Frontend lint**: passes with zero warnings.
- **Frontend tests**: 62 files / 258 tests pass.
- **Production changed-content scan**: zero findings relative to `e507691f`; synthetic canaries in `tests/` and `ci_tests/` are excluded only by the explicit `--exclude-test-fixtures` mode.
- **SQLite encrypted backup/restore round trip**: passes.
- **PostgreSQL execution gates**: **not run locally**; required in CI/pre-production.

## Release decision

Do not label this branch production-approved until all PostgreSQL CI gates pass on the exact reviewed commit, including Alembic preflight/model drift, startup verification of distinct `NOBYPASSRLS`/`BYPASSRLS` roles, the negative application-GUC bypass probe, cross-tenant HTTP tests, and a PostgreSQL backup/restore exercise. No external/legal item in `EXTERNAL_HOLD_QUEUE.md` is silently treated as completed.
