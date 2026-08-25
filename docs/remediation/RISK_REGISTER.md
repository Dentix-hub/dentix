# DENTIX Remediation Risk Register

| Risk ID | Description | Trigger | Immediate Containment | Local Rollback | Status |
|---|---|---|---|---|---|
| R-01 | Existing tenant lockout | Default startup changes access | Set subscription modes off; stop worker | Revert P01 behavior commits | ACTIVE |
| R-02 | Clinical history blocked | Expired tenant cannot read records | Restore read entitlement invariant | Revert entitlement child | ACTIVE |
| R-03 | API contract break | Frontend or contract snapshot changes unexpectedly | Keep compatibility response and document | Revert affected endpoint child | ACTIVE |
| R-04 | Exception handler regression | Status or response shape changes | Disable registration while retaining tests | Revert P03-07 | ACTIVE |
| R-05 | Sensitive error capture | Canary appears in log, DB, alert, or mock sink | Disable sink; purge only synthetic test data | Revert sink integration | ACTIVE |
| R-06 | Migration ambiguity | Backfill finds null/orphan/multiple owners | Abort; produce report; never default owner | Revert unapplied local revision | ACTIVE |
| R-07 | RLS self-lockout | Own-tenant operation fails with NOBYPASSRLS | Keep policy change local; inspect context | Revert table-specific RLS child | ACTIVE |
| R-08 | RLS leak | Cross-tenant negative test succeeds | Stop dependent tenancy tasks | Revert and fix offending table child | ACTIVE |
| R-09 | Connection context leak | Tenant survives pool reuse | Disable affected worker/test path | Revert context-management commit | ACTIVE |
| R-10 | Outbox data loss | Unknown event becomes complete | Move to failed/dead-letter state | Revert handler mapping only if safe | ACTIVE |
| R-11 | Backup false success | Incomplete/corrupt artifact appears valid | Reject artifact; disable scheduler | Set scheduler false; revert writer | ACTIVE |
| R-12 | Restore wrong target | Guard cannot prove target ephemeral | Hard stop destructive test | No command runs | ACTIVE |
| R-13 | External AI bypass | Direct provider call exists | Set AI mode deny and block feature | Revert feature integration | ACTIVE |
| R-14 | De-identification miss | Benchmark false negative exceeds approved threshold | Keep deidentified/contracted modes unavailable | AI mode deny | ACTIVE |
| R-15 | Rate-limit outage | Shared users receive incorrect 429 | Keep mode off or observe | RATE_LIMIT_MODE=off | ACTIVE |
| R-16 | Metrics exposure | Anonymous production-like request succeeds | Set metrics off | METRICS_EXPOSURE_MODE=off | ACTIVE |
| R-17 | Frontend false empty | Failed API renders success/zero state | Restore explicit error state | Revert page child | ACTIVE |
| R-18 | Dependency regression | Lockfile introduces incompatible or critical package | Revert dependency and lock changes | Revert task commit | ACTIVE |
| R-19 | Test concealment | New ignore, skip, xfail, or coverage omission appears | Remove concealment; document real failure | Revert concealment commit | ACTIVE |
| R-20 | Scope expansion | Charging integration or remote action appears | Remove change and record violation | Revert offending commit | ACTIVE |
