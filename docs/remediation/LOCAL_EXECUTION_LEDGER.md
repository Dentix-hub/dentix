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
| P00-03 | IN_PROGRESS | P00-02 | pending | file verification | Pending | Initializing ledger and section 9 artifacts |
| P00-04 | NOT_STARTED | P00-03 | - | - | - | Capture local baseline |
| P00-05 | NOT_STARTED | P00-04 | - | - | - | Record test inventory |
| P00-06 | NOT_STARTED | P00-05 | - | - | - | Guard local destructive tests |
| P00-07 | NOT_STARTED | P00-05 | - | - | - | Add safe change-content scanner |
| P00-08 | NOT_STARTED | P00-04 | - | - | - | Inventory remediation surfaces |
| P01-01 | NOT_STARTED | P00-05 | - | - | - | Reproduce subscription default lockout |
| P01-02 | NOT_STARTED | P01-01 | - | - | - | Add safe subscription modes |
| P01-03 | NOT_STARTED | P01-02 | - | - | - | Prevent automatic tenant deactivation |
| P01-04 | NOT_STARTED | P01-02 | - | - | - | Centralize subscription transitions |
| P01-05 | NOT_STARTED | P01-04 | - | - | - | Centralize subscription entitlements |
| P01-06 | NOT_STARTED | P01-04, P03-06 | - | - | - | Harden audited manual renewal |
| P01-07 | NOT_STARTED | P01-05 | - | - | - | Align subscription UI with manual renewal |
| P02-01 | NOT_STARTED | P00-08 | - | - | - | Inventory database HTTP surfaces |
| P02-02 | NOT_STARTED | P02-01 | - | - | - | Specify disabled SQL contracts |
| P02-03 | NOT_STARTED | P02-02 | - | - | - | Disable full SQL download |
| P02-04 | NOT_STARTED | P02-02 | - | - | - | Remove SQL restore HTTP surface |
| P02-05 | NOT_STARTED | P02-03, P02-04 | - | - | - | Restrict backup administration UI |
| P02-06 | NOT_STARTED | P02-03, P02-04 | - | - | - | Prevent SQL route regression |
| P03-01 | NOT_STARTED | P00-08 | - | - | - | Inventory sensitive logging |
| P03-02 | NOT_STARTED | P03-01 | - | - | - | Add bounded log sanitizer |
| P03-03 | NOT_STARTED | P03-02 | - | - | - | Sanitize persisted system errors |
| P03-04 | NOT_STARTED | P03-02 | - | - | - | Remove master code and token logging |
| P03-05 | NOT_STARTED | P03-02 | - | - | - | Define exception contracts |
| P03-06 | NOT_STARTED | P03-02 | - | - | - | Correct impersonation audit identity |
| P03-07 | NOT_STARTED | P03-03, P03-05 | - | - | - | Register sanitized exception handlers |
| P04-01 | NOT_STARTED | P00-04, P00-08 | - | - | - | Record migration topology |
| P04-02 | NOT_STARTED | P00-06, P04-01 | - | - | - | Add ephemeral PostgreSQL harness |
| P04-03 | NOT_STARTED | P04-02 | - | - | - | Test blank database upgrades |
| P04-04 | NOT_STARTED | P04-03 | - | - | - | Test existing-version upgrades |
| P04-05 | NOT_STARTED | P04-03 | - | - | - | Detect migration and ORM drift |
| P04-06 | NOT_STARTED | P04-01, P04-05 | - | - | - | Decide attachment note schema truth |
| P04-07 | NOT_STARTED | P04-06 | - | - | - | Align attachment note schema |
| P04-08 | NOT_STARTED | P04-04, P04-05 | - | - | - | Enforce real migration checks |
| P05-01 | NOT_STARTED | P03-02 | - | - | - | Make GeoIP lookup non-blocking |
| P05-02 | NOT_STARTED | P05-01 | - | - | - | Add GeoIP privacy controls |
| P05-03 | NOT_STARTED | P00-05 | - | - | - | Enforce database TLS verification |
| P05-04 | NOT_STARTED | P00-08 | - | - | - | Bound API pagination |
| P05-05 | NOT_STARTED | P00-05 | - | - | - | Establish Ruff baseline |
| P05-06 | NOT_STARTED | P05-05 | - | - | - | Gate Python lint locally |
| P05-07 | NOT_STARTED | P03-05 | - | - | - | Wire configurable rate limiting |
| P05-08 | NOT_STARTED | P05-07 | - | - | - | Secure rate-limit client identity |
| P06-01 | NOT_STARTED | P00-08 | - | - | - | Inventory background task lifetimes |
| P06-02 | NOT_STARTED | P06-01 | - | - | - | Specify background session isolation |
| P06-03 | NOT_STARTED | P06-02 | - | - | - | Isolate background database sessions |
| P06-04 | NOT_STARTED | P04-02 | - | - | - | Test outbox with enforced RLS |
| P06-05 | NOT_STARTED | P06-04 | - | - | - | Enforce outbox tenant context |
| P06-06 | NOT_STARTED | P06-05 | - | - | - | Fail unknown outbox events visibly |
| P06-07 | NOT_STARTED | P06-03, P06-06 | - | - | - | Harden worker lifecycle |
| P07-01 | NOT_STARTED | P03-05 | - | - | - | Protect metrics endpoint |
| P07-02 | NOT_STARTED | P07-01 | - | - | - | Wire bounded request metrics |
| P07-03 | NOT_STARTED | P03-02 | - | - | - | Define safe alert events |
| P07-04 | NOT_STARTED | P07-03 | - | - | - | Dispatch monitoring threshold alerts |
| P07-05 | NOT_STARTED | P07-04 | - | - | - | Add safe alert webhook transport |
| P07-06 | NOT_STARTED | P07-04 | - | - | - | Add incident response runbooks |
| P07-07 | NOT_STARTED | P03-03, P07-03 | - | - | - | Add optional safe error aggregation |
| P07-08 | NOT_STARTED | P07-06 | - | - | - | Specify external uptime monitoring |
| P08-01 | NOT_STARTED | P02-04, P07-06 | - | - | - | Document backup threat model |
| P08-02 | NOT_STARTED | P00-06, P08-01 | - | - | - | Add guarded offline backup command |
| P08-03 | NOT_STARTED | P08-02 | - | - | - | Add backup integrity manifest |
| P08-04 | NOT_STARTED | P06-06, P08-02 | - | - | - | Add disabled backup scheduler |
| P08-05 | NOT_STARTED | P08-03 | - | - | - | Add guarded restore verifier |
| P08-06 | NOT_STARTED | P08-05 | - | - | - | Test backup restore round trip |
| P08-07 | NOT_STARTED | P08-06 | - | - | - | Document verified recovery procedure |
| P09-01 | NOT_STARTED | P00-08, P04-05 | - | - | - | Classify all tenant data tables |
| P09-02 | NOT_STARTED | P09-01 | - | - | - | Add tenant ownership preflight |
| P09-03 | NOT_STARTED | P09-02, P04-04 | - | - | - | Expand tenant ownership columns |
| P09-04 | NOT_STARTED | P09-03 | - | - | - | Backfill tenant ownership safely |
| P09-05 | NOT_STARTED | P09-03 | - | - | - | Make sensitive writes tenant-explicit |
| P09-06 | NOT_STARTED | P09-05 | - | - | - | Enforce direct tenant reads |
| P09-07 | NOT_STARTED | P09-04, P09-05 | - | - | - | Enforce tenant ownership constraints |
| P09-08 | NOT_STARTED | P09-06, P09-07 | - | - | - | Enforce RLS on five sensitive tables |
| P09-09 | NOT_STARTED | P09-08 | - | - | - | Test pooled RLS isolation |
| P09-10 | NOT_STARTED | P03-06, P09-08 | - | - | - | Enforce append-only audit policy |
| P09-11 | NOT_STARTED | P09-10 | - | - | - | Add tamper-evident audit verification |
| P10-01 | NOT_STARTED | P09-01 | - | - | - | Map DENTIX data processing |
| P10-02 | NOT_STARTED | P00-08, P03-02 | - | - | - | Centralize external AI egress policy |
| P10-03 | NOT_STARTED | P10-02 | - | - | - | Gate clinical voice AI egress |
| P10-04 | NOT_STARTED | P10-02 | - | - | - | Add measured clinical de-identification |
| P10-05 | NOT_STARTED | P04-05, P10-01 | - | - | - | Add patient processing ledger |
| P10-06 | NOT_STARTED | P10-01, P10-05 | - | - | - | Add dry-run retention engine |
| P10-07 | NOT_STARTED | P09-08, P10-02 | - | - | - | Enforce isolated tenant RAG |
| P10-08 | NOT_STARTED | P09-01, P10-01 | - | - | - | Audit sensitive field encryption |
| P11-01 | NOT_STARTED | P00-01 | - | - | - | Unify application version |
| P11-02 | NOT_STARTED | P11-01 | - | - | - | Register OpenAPI domain tags |
| P11-03 | NOT_STARTED | P00-08, P11-02 | - | - | - | Inventory API response contracts |
| P11-04 | NOT_STARTED | P11-03 | - | - | - | Type selected API responses |
| P11-05 | NOT_STARTED | P00-04 | - | - | - | Add human developer onboarding |
| P11-06 | NOT_STARTED | P00-08 | - | - | - | Classify and prune proven dead code |
| P11-07 | NOT_STARTED | P04-08, P11-03 | - | - | - | Repair known contract and migration drift |
| P11-08 | NOT_STARTED | P12-08 | - | - | - | Align design documentation with tokens |
| P12-01 | NOT_STARTED | P03-05 | - | - | - | Define frontend error taxonomy |
| P12-02 | NOT_STARTED | P12-01 | - | - | - | Make Dashboard failures visible |
| P12-03 | NOT_STARTED | P12-01 | - | - | - | Harden patient page states |
| P12-04 | NOT_STARTED | P12-01 | - | - | - | Harden selected clinical pages |
| P12-05 | NOT_STARTED | P12-01, P01-07 | - | - | - | Harden selected operational pages |
| P12-06 | NOT_STARTED | P12-01 | - | - | - | Isolate tenant server-state cache |
| P12-07 | NOT_STARTED | P12-03 | - | - | - | Pilot typed clinical form |
| P12-08 | NOT_STARTED | P12-02 through P12-07 | - | - | - | Verify frontend compatibility |
| P12-09 | NOT_STARTED | P12-03, P12-04, P01-05 | - | - | - | Add safe onboarding and demo flow |
| P13-01 | NOT_STARTED | P07-02 | - | - | - | Define guarded performance baseline |
| P13-02 | NOT_STARTED | P09-01 | - | - | - | Audit tenant index coverage |
| P13-03 | NOT_STARTED | P13-02 | - | - | - | Add measured tenant indexes |
| P13-04 | NOT_STARTED | P04-04 | - | - | - | Validate database integrity constraints |
| P13-05 | NOT_STARTED | P13-02, P10-08 | - | - | - | Improve privacy-safe patient search |
| P13-06 | NOT_STARTED | P11-01 | - | - | - | Generate local release manifest |
| P13-07 | NOT_STARTED | P13-06, P08-07 | - | - | - | Prepare disabled rollout safeguards |
| P14-01 | NOT_STARTED | all backend tasks | - | - | - | Run backend quality gates |
| P14-02 | NOT_STARTED | all frontend tasks | - | - | - | Run frontend and PWA gates |
| P14-03 | NOT_STARTED | database tasks | - | - | - | Run database and isolation gates |
| P14-04 | NOT_STARTED | P14-01 through P14-03 | - | - | - | Run local full-story smoke |
| P14-05 | NOT_STARTED | P14-04 | - | - | - | Finalize remediation evidence |
| P14-06 | NOT_STARTED | P14-05 | - | - | - | Prepare local review handoff |
| P14-07 | NOT_STARTED | P14-06 | - | - | - | Mark local remediation review ready |
