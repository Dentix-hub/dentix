# DENTIX Local Review Handoff

## What is ready

The locally actionable remediation is implemented on `local/readiness-remediation-20260825-0338`. Local backend, frontend, lint, build, encrypted SQLite recovery, and production-diff security gates pass. The Alembic head is `e3a4b5c6d7e8`.

## What a reviewer must run

1. Review the complete diff from baseline `e507691f`, with special attention to the three new migrations, RLS policy/trigger SQL, native role separation, the renewal transaction, AI egress policy, and backup/restore scheduler/tooling.
2. Run `.github/workflows/ci.yml` on the exact reviewed commit with the PostgreSQL service. Require Alembic preflight/model drift, app/system database-role verification, `backend/ci_tests/test_child_tenant_rls_postgres.py`, and `backend/ci_tests/test_cross_tenant_http_postgres.py` to pass under the non-owner application role.
3. In an approved pre-production environment, perform an encrypted PostgreSQL `pg_dump`/`pg_restore` round trip into an empty guarded database and run health, tenant-isolation, and clinical read-only smoke checks.
4. Run a retained production-like PostgreSQL load/`EXPLAIN` exercise before claiming the proposed latency budgets.
5. Resolve or explicitly accept every item still present in `EXTERNAL_HOLD_QUEUE.md`.

## Decision rule

Promote the status to `LOCAL_REVIEW_READY` only after the PostgreSQL CI gates pass. Production approval additionally requires the recovery and performance evidence above. Until then, the honest status is `PARTIAL — LOCAL_VALIDATION_PASS / POSTGRES_CI_REQUIRED`.
