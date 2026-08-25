# DENTIX Remediation External Hold Queue

The following tasks represent hosted actions, production infrastructure mutations, legal determinations, or external provider configurations that are strictly deferred from local execution.

| Hold ID | External Action | Local Deliverable Only | Acceptance Evidence | Status |
|---|---|---|---|---|
| H-01 | Query real staging/production anomaly counts | Read-only preflight script | Signed/sanitized result and timestamp | BLOCKED_EXTERNAL |
| H-02 | Verify provider backups and PITR | Provider checklist and restore runbook | Settings exports and test restore evidence | BLOCKED_EXTERNAL |
| H-03 | Create uptime monitoring for /health/live | Monitor specification | Monitor ID, interval, regions, recipients | BLOCKED_EXTERNAL |
| H-04 | Configure alert destination | Mock-tested adapter and environment docs | Delivery test and redacted receipt | BLOCKED_EXTERNAL |
| H-05 | Create error aggregation projects | Disabled adapters and privacy checklist | Project settings, retention, redaction | BLOCKED_EXTERNAL |
| H-06 | Approve Egyptian PDPL program | Data map, processing ledger, open legal questions | Counsel-approved basis, notices, retention | BLOCKED_EXTERNAL |
| H-07 | Approve external LLM processing | Default-deny code and vendor questionnaire | DPA, residency, retention/training terms | BLOCKED_EXTERNAL |
| H-08 | Approve patient-facing consent wording | Generic schema and UI placeholder | Approved Arabic/English text and version | BLOCKED_EXTERNAL |
| H-09 | Set real retention periods | Dry-run engine | Approved category schedule and legal holds | BLOCKED_EXTERNAL |
| H-10 | Verify attachment storage backup | Local integrity tooling | Provider inventory and restore sample | BLOCKED_EXTERNAL |
| H-11 | Run migrations on shared data | Migration package and preflight | Reviewed result, backup proof | BLOCKED_EXTERNAL |
| H-12 | Reconcile remote main/staging ancestry | Local comparison report | Reviewed merge strategy | BLOCKED_EXTERNAL |
| H-13 | Enable hosted workers or schedules | Disabled-by-default code | Hosted config, alerting, rollback test | BLOCKED_EXTERNAL |
| H-14 | Enable rate-limit enforcement | Observe/enforce code | Proxy proof, observe metrics | BLOCKED_EXTERNAL |
| H-15 | Expose protected metrics to collector | Protected mode | Network/auth config and scrape proof | BLOCKED_EXTERNAL |
| H-16 | Run load tests against staging | Guarded scripts | Written authorization, synthetic tenant | BLOCKED_EXTERNAL |
| H-17 | Deploy to staging | Local release manifest | Reviewed commits and deployment evidence | BLOCKED_EXTERNAL |
| H-18 | Deploy to production | None during this run | Staging soak, approval, rollback readiness | BLOCKED_EXTERNAL |
| H-19 | Publish apps or PWA release | Local build proof | Compatibility review and release approval | BLOCKED_EXTERNAL |
