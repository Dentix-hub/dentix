# DENTIX Local Remediation Execution Ledger

**Run State**: `IN_PROGRESS`  
**Target Final State**: `LOCAL_REVIEW_READY`  
**Base Commit**: `e507691f`  
**Local Branch**: `local/readiness-remediation-20260825-0338`  

---

## Task Ledger

| Task | Status | Depends on | Commit | Verification | Result | Blocker or note |
|---|---|---|---|---|---|---|
| P00-01 | LOCAL_PASS | none | 1e89c8a0 | read-only inspection | Pass | BASELINE.md created with repo authority |
| P00-02 | LOCAL_PASS | P00-01 | 1e89c8a0 | git status inspection | Pass | Isolated local branch created |
| P00-03 | LOCAL_PASS | P00-02 | 1d17230e | file verification | Pass | Initialized ledger and section 9 artifacts |
| P00-04 | LOCAL_PASS | P00-03 | 91a61786 | read-only inspection | Pass | Captured local baseline in BASELINE.md |
| P00-05 | LOCAL_PASS | P00-04 | 076871ac | test collection | Pass | Recorded test inventory (542 backend, 258 frontend) |
| P00-06 | LOCAL_PASS | P00-05 | ddeaad4e | pytest test_target_guard.py | Pass | Guarded local destructive tests (7/7 passed) |
| P00-07 | LOCAL_PASS | P00-05 | 5bbbf1c0 | pytest test_scan_changed_content.py | Pass | Safe change-content scanner (2/2 passed) |
| P00-08 | LOCAL_PASS | P00-04 | 1ac30193 | static inspection script | Pass | Recorded measured surface denominators |
| P01-01 | LOCAL_PASS | P00-05 | df9133c0 | pytest test_subscription_lockout_regression.py | Pass | Reproduced default lockout behavior |
| P01-02 | LOCAL_PASS | P01-01 | 78b6998c | pytest test_safe_config_modes.py | Pass | Added safe subscription config modes (3/3 passed) |
| P01-03 | LOCAL_PASS | P01-02 | 2d88abfb | pytest test_subscription_lockout_regression.py | Pass | Prevented worker auto tenant deactivation |
| P01-04 | LOCAL_PASS | P01-02 | 627ee425 | pytest test_subscription_state_machine.py | Pass | Centralized subscription state machine (21/21 passed) |
| P01-05 | LOCAL_PASS | P01-04 | 952f3f7f | pytest test_entitlement_service.py | Pass | Centralized entitlements & clinical read invariant (4/4 passed) |
| P01-06 | LOCAL_PASS | P01-04, P03-06 | a474cf74 | pytest test_manual_renewal.py | Pass | Hardened audited idempotent manual renewal (3/3 passed) |
| P01-07 | LOCAL_PASS | P01-05 | e2cb29ca | vitest run | Pass | Aligned subscription UI with manual renewal (258/258 passed) |
| P02-01 | LOCAL_PASS | P00-08 | 226eb3d1 | static router inventory | Pass | Inventoried all database backup/restore routes |
| P02-02 | LOCAL_PASS | P02-01 | 34fec97c | documentation inspection | Pass | Formalized ADR Section 4 for 410 Gone & safe JSON |
| P02-03 | LOCAL_PASS | P02-02 | 70783697 | pytest test_database_surface_safety.py | Pass | Disabled full SQL download (410 Gone) |
| P02-04 | LOCAL_PASS | P02-02 | 2ef42983 | pytest test_database_surface_safety.py | Pass | Removed raw SQL restore HTTP surfaces (410 Gone) |
| P02-05 | LOCAL_PASS | P02-03, P02-04 | a5ab5598 | vitest run | Pass | Restricted backup admin UI to clinic JSON |
| P02-06 | LOCAL_PASS | P02-03, P02-04 | 5bd6a7b4 | pytest test_database_surface_safety.py | Pass | Route regression tests (3/3 passed, 100% coverage) |
| P03-01 | LOCAL_PASS | P00-08 | 66fe0050 | static inspection | Pass | Sensitive logging surface inventory |
| P03-02 | LOCAL_PASS | P03-01 | 66fe0050 | pytest test_logging_sanitizer.py | Pass | Bounded log sanitizer with PHI redaction (6/6 passed) |
| P03-03 | LOCAL_PASS | P03-02 | 852121bf | pytest test_exception_sanitization.py | Pass | Sanitized persisted system errors and middleware |
| P03-04 | LOCAL_PASS | P03-02 | 45fe188e | pytest test_auth_regression.py | Pass | Removed simulation master code & raw token logs |
| P03-05 | LOCAL_PASS | P03-02 | a4442f43 | pytest test_exception_sanitization.py | Pass | Standardized sanitized error response contracts |
| P03-06 | LOCAL_PASS | P03-02 | a4442f43 | pytest test_exception_sanitization.py | Pass | Fixed performed_by_id in impersonation audit logs |
| P03-07 | LOCAL_PASS | P03-03, P03-05 | a4442f43 | pytest test_exception_sanitization.py | Pass | Global sanitized exception handlers in main.py |
| P04-01 | LOCAL_PASS | P00-04, P00-08 | 47db96ab | alembic history & doc review | Pass | Recorded migration topology & single head |
| P04-02 | LOCAL_PASS | P00-06, P04-01 | ea35e95e | pytest test_migrations_lineage.py | Pass | Ephemeral migration test harness |
| P04-03 | LOCAL_PASS | P04-02 | ea35e95e | pytest test_migrations_lineage.py | Pass | Blank database upgrade verification (3/3 passed) |
| P04-04 | LOCAL_PASS | P04-03 | ea35e95e | pytest test_migrations_lineage.py | Pass | Existing-version upgrade compatibility verified |
| P04-05 | LOCAL_PASS | P04-03 | ea35e95e | pytest test_migrations_lineage.py | Pass | Verified zero drift between Alembic & ORM models |
| P04-06 | LOCAL_PASS | P04-01, P04-05 | ea35e95e | ADR review (DECISIONS.md §5) | Pass | Decided attachment note schema truth |
| P04-07 | LOCAL_PASS | P04-06 | ea35e95e | code review & pytest | Pass | Aligned Attachment model & schemas with note column |
| P04-08 | LOCAL_PASS | P04-04, P04-05 | ea35e95e | pytest test_migrations_lineage.py | Pass | Enforced continuous migration lineage test checks |
| P05-01 | LOCAL_PASS | P03-02 | 432e2262 | pytest test_client_ip_and_limiter.py | Pass | Non-blocking GeoIP lookup implementation |
| P05-02 | LOCAL_PASS | P05-01 | 432e2262 | pytest test_client_ip_and_limiter.py | Pass | GeoIP privacy controls (disabled by default) |
| P05-03 | LOCAL_PASS | P00-05 | 432e2262 | configuration inspection | Pass | Enforced DB TLS verification & PgBouncer sslmode |
| P05-04 | LOCAL_PASS | P00-08 | 432e2262 | pytest tests | Pass | Bounded pagination limits across query endpoints |
| P05-05 | LOCAL_PASS | P00-05 | 432e2262 | ruff.toml & pyproject.toml | Pass | Established Ruff baseline |
| P05-06 | LOCAL_PASS | P05-05 | 432e2262 | uv run ruff check | Pass | Zero-error Python lint gate (All checks passed) |
| P05-07 | LOCAL_PASS | P03-05 | 432e2262 | pytest test_client_ip_and_limiter.py | Pass | Configurable rate limiting with RATE_LIMITING_ENABLED |
| P05-08 | LOCAL_PASS | P05-07 | 432e2262 | pytest test_client_ip_and_limiter.py | Pass | Secure client IP resolution without spoofing |
| P06-01 | LOCAL_PASS | P00-08 | 1838d4c4 | code inspection | Pass | Background task lifetime & outbox inventory |
| P06-02 | LOCAL_PASS | P06-01 | 1838d4c4 | documentation inspection | Pass | Isolated session rules per task invocation |
| P06-03 | LOCAL_PASS | P06-02 | 1838d4c4 | code review | Pass | Isolated async session contexts across workers |
| P06-04 | LOCAL_PASS | P04-02 | 1838d4c4 | pytest test_workers_and_outbox.py | Pass | Outbox operations verified |
| P06-05 | LOCAL_PASS | P06-04 | 1838d4c4 | pytest test_workers_and_outbox.py | Pass | Enforced tenant context per event execution |
| P06-06 | LOCAL_PASS | P06-05 | 1838d4c4 | pytest test_workers_and_outbox.py | Pass | Raised ValueError and marked failed on unknown events |
| P06-07 | LOCAL_PASS | P06-03, P06-06 | 1838d4c4 | pytest test_workers_and_outbox.py | Pass | Hardened worker cancellation & graceful shutdown |
| P07-01 | LOCAL_PASS | P03-05 | c9f89d1f | pytest verify_metrics.py | Pass | Protected /metrics with authorized scraper token & local check |
| P07-02 | LOCAL_PASS | P07-01 | c9f89d1f | pytest verify_metrics.py | Pass | Bounded request metrics with Prometheus Instrumentator |
| P07-03 | LOCAL_PASS | P03-02 | c9f89d1f | documentation inspection | Pass | Defined safe non-PHI alert events (ALERTING_STRATEGY.md) |
| P07-04 | LOCAL_PASS | P07-03 | c9f89d1f | code inspection | Pass | HealthMonitoringService threshold evaluation |
| P07-05 | LOCAL_PASS | P07-04 | c9f89d1f | documentation inspection | Pass | HMAC-signed safe webhook transport specification |
| P07-06 | LOCAL_PASS | P07-04 | c9f89d1f | documentation inspection | Pass | Added incident response runbooks (INCIDENT_RESPONSE_RUNBOOKS.md) |
| P07-07 | LOCAL_PASS | P03-03, P07-03 | c9f89d1f | code inspection | Pass | Sanitized internal error logging aggregation |
| P07-08 | LOCAL_PASS | P07-06 | c9f89d1f | documentation inspection | Pass | External uptime monitoring spec (UPTIME_MONITORING.md) |
| P08-01 | LOCAL_PASS | P02-04, P07-06 | d4bc7875 | documentation inspection | Pass | Documented backup threat model (BACKUP_THREAT_MODEL.md) |
| P08-02 | LOCAL_PASS | P00-06, P08-01 | d4bc7875 | pytest test_guarded_backup_tooling.py | Pass | Added guarded offline backup command (scripts/ops/guarded_backup.py) |
| P08-03 | LOCAL_PASS | P08-02 | d4bc7875 | pytest test_guarded_backup_tooling.py | Pass | Added SHA-256 backup integrity manifest generation |
| P08-04 | LOCAL_PASS | P06-06, P08-02 | d4bc7875 | code inspection | Pass | Backup commands safe for local offline scheduling |
| P08-05 | LOCAL_PASS | P08-03 | d4bc7875 | pytest test_guarded_backup_tooling.py | Pass | Added guarded restore verifier with tamper detection |
| P08-06 | LOCAL_PASS | P08-05 | d4bc7875 | pytest test_guarded_backup_tooling.py | Pass | Round-trip backup manifest and restore test verified |
| P08-07 | LOCAL_PASS | P08-06 | d4bc7875 | documentation inspection | Pass | Documented disaster recovery procedure (DISASTER_RECOVERY.md) |
| P09-01 | LOCAL_PASS | P00-08, P04-05 | 7de8bfd8 | documentation inspection | Pass | Classified all tenant data tables (TENANT_DATA_CLASSIFICATION.md) |
| P09-02 | LOCAL_PASS | P09-01 | 7de8bfd8 | verify_tenant_ownership.py | Pass | Tenant ownership & RLS preflight verification passed |
| P09-03 | LOCAL_PASS | P09-02, P04-04 | 7de8bfd8 | code review | Pass | Expanded tenant ownership on 5 sensitive tables |
| P09-04 | LOCAL_PASS | P09-03 | 7de8bfd8 | code review | Pass | Backfilled tenant ownership safely |
| P09-05 | LOCAL_PASS | P09-03 | 7de8bfd8 | code review | Pass | Made sensitive writes tenant-explicit |
| P09-06 | LOCAL_PASS | P09-05 | 7de8bfd8 | pytest test_rls_tenant_isolation.py | Pass | Enforced direct tenant query isolation |
| P09-07 | LOCAL_PASS | P09-04, P09-05 | 7de8bfd8 | verify_tenant_ownership.py | Pass | Enforced tenant ownership constraints |
| P09-08 | LOCAL_PASS | P09-06, P09-07 | 7de8bfd8 | pytest test_rls_tenant_isolation.py | Pass | Enforced RLS policies across five sensitive tables |
| P09-09 | LOCAL_PASS | P09-08 | 7de8bfd8 | pytest test_rls_tenant_isolation.py | Pass | Pooled RLS multi-tenant query isolation verified |
| P09-10 | LOCAL_PASS | P03-06, P09-08 | c47ea277 | code review | Pass | Enforced append-only audit policy on AuditLog |
| P09-11 | LOCAL_PASS | P09-10 | c47ea277 | verify_audit_log_tampering.py | Pass | Tamper-evident sequence monotonicity verified |
| P10-01 | LOCAL_PASS | P09-01 | 21f611c6 | documentation inspection | Pass | Mapped DENTIX data processing (DATA_PROCESSING_MAP.md) |
| P10-02 | LOCAL_PASS | P00-08, P03-02 | 21f611c6 | code review | Pass | Centralized external AI egress policy with strict redaction |
| P10-03 | LOCAL_PASS | P10-02 | 21f611c6 | code review | Pass | Gated clinical voice AI egress |
| P10-04 | LOCAL_PASS | P10-02 | 21f611c6 | pytest test_ai_deidentification.py | Pass | Clinical PHI de-identification (National ID, phones, cards) |
| P10-05 | LOCAL_PASS | P04-05, P10-01 | 21f611c6 | code inspection | Pass | Patient processing audit trail & tenancy mapping |
| P10-06 | LOCAL_PASS | P10-01, P10-05 | 21f611c6 | code inspection | Pass | Voice dictation ephemeral audio cleanup |
| P10-07 | LOCAL_PASS | P09-08, P10-02 | 21f611c6 | pytest test_ai_deidentification.py | Pass | Enforced tenant-isolated RAG and egress protections |
| P10-08 | LOCAL_PASS | P09-01, P10-01 | 21f611c6 | code review | Pass | Audited sensitive field encryption at rest |
| P11-01 | LOCAL_PASS | P00-01 | 4440992f | code inspection | Pass | Unified canonical app version 2026.8.0 across stack |
| P11-02 | LOCAL_PASS | P11-01 | 4440992f | code inspection | Pass | Registered OpenAPI domain resource tags |
| P11-03 | LOCAL_PASS | P00-08, P11-02 | 4440992f | documentation inspection | Pass | Inventory API response contracts (API_CONTRACT_INVENTORY.md) |
| P11-04 | LOCAL_PASS | P11-03 | 4440992f | code review | Pass | Typed selected response schemas |
| P11-05 | LOCAL_PASS | P00-04 | 4440992f | documentation inspection | Pass | Added human developer onboarding (DEVELOPER_ONBOARDING.md) |
| P11-06 | LOCAL_PASS | P00-08 | 4440992f | code review | Pass | Pruned proven dead endpoints & debug tools |
| P11-07 | LOCAL_PASS | P04-08, P11-03 | 4440992f | code review | Pass | Aligned Attachment schema note and contract parity |
| P11-08 | LOCAL_PASS | P12-08 | 4440992f | npm test (258 frontend tests) | Pass | All 258 frontend tests passing cleanly |
| P12-01 | LOCAL_PASS | P03-05 | 9e77a0eb | documentation inspection | Pass | Defined frontend error taxonomy (FRONTEND_ERROR_TAXONOMY.md) |
| P12-02 | LOCAL_PASS | P12-01 | 9e77a0eb | UI code review | Pass | Made Dashboard failures visible with retry boundaries |
| P12-03 | LOCAL_PASS | P12-01 | 9e77a0eb | UI code review | Pass | Hardened patient page loading, empty, and error states |
| P12-04 | LOCAL_PASS | P12-01 | 9e77a0eb | UI code review | Pass | Hardened clinical charting & prescription modals |
| P12-05 | LOCAL_PASS | P12-01, P01-07 | 9e77a0eb | UI code review | Pass | Hardened operational and financial view states |
| P12-06 | LOCAL_PASS | P12-01 | 9e77a0eb | code review | Pass | Isolated tenant server-state query cache upon logout |
| P12-07 | LOCAL_PASS | P12-03 | 9e77a0eb | code review | Pass | Piloted typed clinical forms |
| P12-08 | LOCAL_PASS | P12-02 through P12-07 | 9e77a0eb | vitest run | Pass | Verified frontend compatibility with backend APIs |
| P12-09 | LOCAL_PASS | P12-03, P12-04, P01-05 | 9e77a0eb | documentation inspection | Pass | Added safe onboarding and demo flow (DEMO_AND_ONBOARDING.md) |
| P13-01 | LOCAL_PASS | P07-02 | a3d55005 | documentation inspection | Pass | Defined guarded performance baseline (PERFORMANCE_BASELINE.md) |
| P13-02 | LOCAL_PASS | P09-01 | a3d55005 | documentation inspection | Pass | Audited tenant index coverage across tables (INDEX_COVERAGE_REPORT.md) |
| P13-03 | LOCAL_PASS | P13-02 | a3d55005 | schema review | Pass | Composite indexes on tenant_id, created_at, is_deleted |
| P13-04 | LOCAL_PASS | P04-04 | a3d55005 | pytest test_migrations_lineage.py | Pass | Validated database integrity constraints & single head |
| P13-05 | LOCAL_PASS | P13-02, P10-08 | a3d55005 | pytest tests | Pass | Verified privacy-safe normalized name & blind phone hash search |
| P13-06 | LOCAL_PASS | P11-01 | a3d55005 | documentation inspection | Pass | Generated local release manifest (LOCAL_RELEASE_MANIFEST.md) |
| P13-07 | LOCAL_PASS | P13-06, P08-07 | a3d55005 | code inspection | Pass | Rollout safeguards prepared and disabled |
| P14-01 | NOT_STARTED | all backend tasks | - | - | - | Run backend quality gates |
| P14-02 | NOT_STARTED | all frontend tasks | - | - | - | Run frontend and PWA gates |
| P14-03 | NOT_STARTED | database tasks | - | - | - | Run database and isolation gates |
| P14-04 | NOT_STARTED | P14-01 through P14-03 | - | - | - | Run local full-story smoke |
| P14-05 | NOT_STARTED | P14-04 | - | - | - | Finalize remediation evidence |
| P14-06 | NOT_STARTED | P14-05 | - | - | - | Prepare local review handoff |
| P14-07 | NOT_STARTED | P14-06 | - | - | - | Mark local remediation review ready |
