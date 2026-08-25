# External Verification Gates

| Gate | Local result | Required evidence |
|---|---|---|
| PostgreSQL Alembic preflight and ORM drift | Not run; no local PG/Docker runtime | Passing CI log on exact reviewed commit |
| Native database-role separation and application-GUC negative probe | Not run locally | Startup verifies distinct same-database non-superuser `NOBYPASSRLS`/`BYPASSRLS` roles; `test_child_tenant_rls_postgres.py` proves the app cannot self-elevate |
| FORCE-RLS child isolation under application role | Not run locally | Passing `test_child_tenant_rls_postgres.py` |
| Cross-tenant HTTP adversarial flow on PostgreSQL | Not run locally | Passing `test_cross_tenant_http_postgres.py` |
| Encrypted PostgreSQL backup/restore | Not run locally | Retained pre-production recovery report |
| Production-like load and query plans | Not run locally | Retained workload, latency/error, saturation, and `EXPLAIN` artifact |

These gates are not failures, but they prevent a truthful production-ready/DONE release declaration.
