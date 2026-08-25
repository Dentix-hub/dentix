# DENTIX Production Readiness Remediation Master Plan

Version 2.0 — English, Atomic, Local One-Run Edition  
Date: 2026-08-24  
Execution target: the developer's local machine only  
Required final state: LOCAL_REVIEW_READY  
Remote mutation policy: prohibited until owner review  
Subscription policy: manual renewal only; third-party subscription payment gateways are excluded

---

## 1. Purpose

This document is both the complete remediation plan for the verified DENTIX findings and the operating specification for one coding model to execute all safe local work in one continuous run.

The executor must finish every locally executable task, preserve evidence, and continue past ordinary blockers. It must not push, open a pull request, merge, deploy, change a hosted environment, call a live write endpoint, or migrate a shared database.

The owner will review the local branch and evidence in a separate session. Online promotion is deliberately outside this execution.

---

## 2. Owner Decisions

| Decision | Required behavior |
|---|---|
| Execution | Local machine only |
| Delivery | Local branch, local commits, tests, and evidence |
| Remote repositories | No push, pull request, merge, tag, release, or remote branch mutation |
| Hosted systems | No deployment or hosted configuration mutation |
| Shared databases | No schema or data mutation |
| Renewal | Authorized staff renew subscriptions manually |
| Charging | No electronic collection or provider confirmation flow |
| Trial | Preserve repository intent; use a documented 14-day default only if no authoritative value exists |
| Expiry | Keep clinical-history reads available; block new billable writes only in explicit enforce mode |
| Existing tenants | No surprise lockout from defaults |
| PHI | Fail closed on cross-tenant access and external transmission |
| Finish line | Stop at LOCAL_REVIEW_READY |

---

## 3. Copy-Paste Prompt for the Local Executor

~~~text
You are the sole implementation agent for the DENTIX local production-readiness remediation.

Read this entire plan before editing anything. Execute the Local Execution Queue in dependency order in one continuous run. Do not ask routine questions. If an ordinary task is blocked, record the blocker, skip only the blocked portion, and continue with every independent local task.

You may inspect the repository and local history; create a local branch or isolated worktree; edit code, tests, migrations, and documentation; install declared dependencies; run tests, builds, local containers, ephemeral databases, and localhost-only load tests; and create small local commits.

You must not push, force-push, open or modify a pull request, merge into a shared branch, tag, publish, release, deploy, mutate a hosted environment, mutate a shared database, call a non-local write endpoint, change DNS or provider configuration, send real patient data externally, implement a third-party subscription payment gateway, or erase/stash/reset/clean/overwrite existing user work.

Use the task loop, statuses, stop conditions, commands, and acceptance criteria in this plan. Add tests before or with behavioral changes. Prefer one local commit per atomic task. If a task is already satisfied, prove it and record SKIPPED_ALREADY_SATISFIED. Never claim an external task is complete.

Finish by running the full local verification matrix, creating docs/remediation/LOCAL_REVIEW_HANDOFF.md, setting the ledger state to LOCAL_REVIEW_READY, printing the final local commit range and unresolved blockers, and stopping. Do not perform any online promotion step.
~~~

---

## 4. Meaning of One Continuous Run

The executor does not pause for ordinary uncertainty, one optional missing tool, or an external-only dependency. It inspects, chooses the safest reversible local action, implements one task, verifies it, commits it locally, updates the ledger, and continues.

If a task is blocked, record the exact reason and continue with independent work. A complete stop is allowed only for Section 8 hard-stop conditions.

---

## 5. Task Statuses

| Status | Meaning |
|---|---|
| NOT_STARTED | No work attempted |
| IN_PROGRESS | Currently being changed or verified |
| LOCAL_PASS | Change and required local verification passed |
| LOCAL_FAIL | Verification failed after safe repair attempts |
| BLOCKED_DEPENDENCY | Another local task must finish first |
| BLOCKED_EXTERNAL | Needs legal, provider, hosted-system, live-data, or owner action |
| DEFERRED_OWNER | A product decision is missing and no safe default exists |
| SKIPPED_ALREADY_SATISFIED | Existing code meets the acceptance criteria and evidence proves it |
| NOT_APPLICABLE | Repository discovery proves the task does not apply |

The run may end as LOCAL_REVIEW_READY only when no task remains IN_PROGRESS, all mandatory local gates pass, every failure or blocker is visible, and no remote mutation occurred. This state means ready for review, not ready for production.

---

## 6. Baseline Rules

The earlier audit observed these historical values. They are evidence, not commands:

| Reference | Historical value |
|---|---|
| Main commit | b44aeeb4710d6aafddaa037b94be9e5345ed02ab |
| Staging commit | 57c1c8c71b6d354fa1a007f6a9b08bf6bcb10b8e |
| Merge base | ea509de70b78b6fa13114b7c43f6873a21a9072a |
| Main Alembic head | b8c9d0e1f2a3 |
| Staging Alembic head | c9d0e1f2a3b4 |

Select the local baseline in this order:

1. Read PROJECT_TRUTH.md and every applicable AGENTS.md or repository instruction.
2. Use an explicitly named canonical local branch if the repository defines one and that ref exists.
3. Otherwise use the currently checked-out HEAD.
4. Never fetch or pull merely to match the historical hashes.
5. Record commit, branch, migration heads, tool versions, test method, and selection reason.
6. Re-run all evidence; do not trust an earlier local checkpoint without verification.

If the current worktree is clean, create local/readiness-remediation-YYYYMMDD-HHMM.

If it is dirty, never stash, reset, clean, or overwrite it. Record changed paths and create an isolated sibling worktree from the selected committed baseline. If safe isolation is impossible and required files overlap, stop under Section 8.

---

## 7. Non-Negotiable Safety Invariants

1. Use synthetic data only in fixtures, logs, prompts, screenshots, and evidence.
2. Run migrations only against a provably ephemeral PostgreSQL database.
3. Cross-tenant access must fail at application and database layers where RLS is used.
4. A request-scoped AsyncSession must never outlive its request.
5. Never log secrets, tokens, authorization values, cookies, raw exception payloads, or clinical text.
6. Full SQL dump download and SQL restore must not remain available through production HTTP.
7. Subscription defaults must not disable existing tenants.
8. Expiry must not make existing clinical history unreadable.
9. External PHI processing defaults to denied.
10. Audit records identify the real actor and are not tenant-rewritable.
11. Security middleware is tested under the real proxy model before hosted enforcement.
12. Public API changes require contract tests and a compatibility decision.
13. Every change has a local rollback path.
14. External tasks are never marked complete from local code alone.
15. No remote mutation occurs during this run.

---

## 8. Mandatory Hard Stops

Stop the whole run, preserve the worktree, and write the blocker only when:

1. the path is not the DENTIX repository;
2. repository instructions forbid the edits;
3. overlapping user changes cannot be isolated;
4. a database command cannot be proven local and ephemeral;
5. an action would expose, rotate, or repurpose a real secret;
6. real patient data appears unexpectedly;
7. completion requires destructive history rewriting;
8. critical repository files are unreadable or corrupt;
9. a security fix requires an unknowable breaking contract and no safe flag or compatibility layer exists;
10. another process is concurrently editing the same worktree.

Missing external credentials, unavailable hosted services, absent legal decisions, one unrelated failing test, and unconfigured alert recipients are not full stops. Record them and continue.

---

## 9. Required Local Artifacts

Create:

| File | Purpose |
|---|---|
| docs/remediation/LOCAL_EXECUTION_LEDGER.md | Status, dependency, commit, verification, result, and blocker per task |
| docs/remediation/BASELINE.md | Local branch, commit, migrations, tools, test baseline, and isolation method |
| docs/remediation/DECISIONS.md | Repository-specific defaults and implementation decisions |
| docs/remediation/RISK_REGISTER.md | Risk, trigger, mitigation, rollback, and owner |
| docs/remediation/EXTERNAL_HOLD_QUEUE.md | Items deliberately not performed locally |
| docs/remediation/LOCAL_REVIEW_HANDOFF.md | Final reviewer entry point |
| docs/remediation/evidence/TASK-ID/ | Sanitized task evidence |

Evidence must contain concise commands and results, never secrets, dumps, PHI, raw exception bodies, or full noisy logs. Use ISO 8601 UTC timestamps.

Ledger columns:

| Task | Status | Depends on | Commit | Verification | Result | Blocker or note |
|---|---|---|---|---|---|---|

---

## 10. Local Commit Protocol

Commit subject:

    task(TASK-ID): imperative summary

Rules:

- Prefer one task per commit.
- Keep its test with the behavior unless a task explicitly says test-first.
- Do not mix formatting with behavior.
- Do not amend a commit after dependent tasks exist; add a follow-up.
- Do not squash or force-update.
- Never change global git configuration.
- If identity is missing, set repository-local values only:
  - user.name: DENTIX Local Remediation Executor
  - user.email: local-only@dentix.invalid

---

## 11. Atomic Task Loop

For each task:

1. Set IN_PROGRESS.
2. Inspect named and adjacent code with rg.
3. Record the intended invariant.
4. Add the smallest failing test when feasible.
5. Confirm the expected failure.
6. Make the smallest implementation change.
7. Run the targeted test.
8. Run adjacent domain tests.
9. Run task-specific static checks.
10. Inspect the diff for unrelated edits, secrets, and PHI.
11. Add sanitized evidence.
12. Commit locally.
13. Record the hash and result.
14. Set the terminal status.
15. Continue immediately.

For repeated endpoint or page work, inventory all targets first, generate child IDs, change at most five endpoints or two pages per child commit, and never hide partial completion behind one broad task.

### 11.1 Atomicity limits

A child task should normally:

- change one observable behavior or one schema concern;
- have one primary rollback action;
- touch no more than five production source files, excluding directly related tests and generated migration snapshots;
- stay below roughly 400 non-generated changed lines;
- complete in about 15 to 90 focused minutes for a capable coding agent;
- produce one targeted test command and one local commit.

If any limit is exceeded, split before editing. A parent card with generated children is a roll-up and receives no implementation commit of its own.

The following cards must be expanded before work:

| Parent | Required child boundary |
|---|---|
| P05-04 | Maximum five list endpoints per child |
| P09-03 | One tenant-column migration concern per table or tightly coupled pair |
| P09-04 | One table backfill and anomaly test per child |
| P09-05 | One table's write paths per child |
| P09-06 | One table's read/query paths per child |
| P09-07 | One table's constraints per child |
| P09-08 | One table's RLS policies per child |
| P09-09 | One table or one pooled-concurrency scenario per child |
| P10-04 | Benchmark corpus, detectors, transformation, integration, and fail-closed behavior as separate children |
| P10-06 | Inventory, selector, legal hold, dry-run report, deletion orchestration, and audit as separate children |
| P11-04 | Maximum five endpoints per child |
| P12-04 | Maximum two pages per child |
| P12-05 | Maximum two pages per child |
| P13-04 | Maximum five constraints per child |

Child ID format:

    PARENT-NNN

Example:

    P09-08-001

Each generated child must be added to the ledger before its first edit, with its exact files, target test, dependency, and rollback.

---

## 12. Local Target Guard

Database commands that mutate, migrate, restore, or load data must require:

- localhost, loopback, a local container service, or an explicitly created ephemeral test container;
- a database name containing test, ci, ephemeral, or dentix_local;
- rejection of configured staging and production hosts;
- LOCAL_DESTRUCTIVE_TESTS=1 for restore tests;
- a sanitized target printed before execution.

HTTP and load tests must require loopback and reject known or configured live domains, including dentixs.app, vercel.app, hf.space, and supabase.co. Never print Authorization values.

If the guard fails, mark the affected test or task and continue. Do not weaken the guard.

---

## 13. Safe Configuration Modes

| Control | Allowed modes | Local default |
|---|---|---|
| SUBSCRIPTION_ENFORCEMENT_MODE | off, observe, enforce | off |
| SUBSCRIPTION_WORKER_ENABLED | false, true | false |
| RATE_LIMIT_MODE | off, observe, enforce | off |
| METRICS_EXPOSURE_MODE | off, protected | off |
| ALERT_DISPATCH_ENABLED | false, true | false |
| ERROR_AGGREGATION_ENABLED | false, true | false |
| BACKUP_SCHEDULER_ENABLED | false, true | false |
| EXTERNAL_AI_PHI_MODE | deny, deidentified, contracted | deny |
| GEOIP_MODE | off, coarse, full | off |
| RAG_MODE | off, isolated | off |

Centralize parsing. Invalid values fail startup safely. Document variables without secrets. Test every mode. Hosted activation belongs to the External Hold Queue.

---

## 14. Gate Order

| Gate | Goal | Exit requirement |
|---|---|---|
| L0 | Safe workspace | Isolated branch/worktree and baseline |
| L1 | Reproducible harness | Existing commands and baseline failures recorded |
| L2 | Immediate containment | Lockout, SQL HTTP, master-code, and raw-log risks contained |
| L3 | Migration confidence | Blank and N-1 upgrade plus drift tests |
| L4 | Tenant integrity | Five PHI tables have ownership and fail-closed tests |
| L5 | Privacy and recoverability | AI default denied; backup/restore locally proven |
| L6 | Reliability | Workers, monitoring code, API, UX, and performance verified |
| L7 | Review package | Full local matrix and handoff |

---

# Local Execution Queue

## Phase P00 — Workspace, Baseline, and Harness

### P00-01 — Identify repository authority

- Depends on: none
- Change: Read PROJECT_TRUTH.md, applicable AGENTS.md files, readmes, CI workflows, manifests, Alembic configuration, and deployment descriptors. Record precedence in BASELINE.md.
- Verify: Repository name, backend and frontend entry points, test commands, and migration directory are identified.
- Commit: task(P00-01): record repository authority
- Accept: No implementation starts with unresolved local instructions.

### P00-02 — Isolate the worktree

- Depends on: P00-01
- Change: Record git status. Create a local branch if clean or a sibling worktree if dirty. Preserve existing work.
- Verify: The execution worktree is clean before plan artifacts are added.
- Commit: included with P00-03
- Accept: The remediation diff contains no pre-existing user edits.

### P00-03 — Create the execution ledger

- Depends on: P00-02
- Change: Create Section 9 artifacts and prepopulate every task ID from P00-01 through P14-07 as NOT_STARTED.
- Verify: Each task ID appears exactly once.
- Commit: task(P00-03): initialize remediation ledger
- Accept: Files alone are enough to resume the run.

### P00-04 — Capture the current baseline

- Depends on: P00-03
- Change: Record HEAD, local branch relationships, migration heads, schema metadata, Python, Node, package managers, Docker availability, and flag defaults.
- Verify: Commands are read-only and outputs sanitized.
- Commit: task(P00-04): capture local baseline
- Accept: Historical audit facts and current local facts are separate.

### P00-05 — Inventory tests and baseline failures

- Depends on: P00-04
- Change: Discover backend, frontend, E2E, migration, security, load, and mobile checks. Run collection or list commands before broad suites.
- Verify: Missing tools, collection errors, and baseline failures are recorded without hiding them.
- Commit: task(P00-05): record test inventory
- Accept: New regressions can be distinguished from old failures.

### P00-06 — Implement live-target guards

- Depends on: P00-05
- Change: Add reusable database and HTTP guards for migration, restore, integration, and load scripts.
- Verify: Unit tests reject representative live hosts and accept loopback ephemeral targets.
- Commit: task(P00-06): guard local destructive tests
- Accept: Repository test utilities cannot accidentally target hosted systems.

### P00-07 — Add safe diff scanning

- Depends on: P00-05
- Change: Add a changed-file/evidence scanner for likely secrets and prohibited sensitive fixture patterns. Report only paths and rule IDs, not matched values.
- Verify: Synthetic canaries are detected and output stays redacted.
- Commit: task(P00-07): add safe change-content scanner
- Accept: Final verification can detect likely leakage.

### P00-08 — Generate architectural inventories

- Depends on: P00-04
- Change: Inventory routers, models, migrations, workers, create_task, router db.execute, logging, external HTTP, AI provider calls, tenant_id, RLS, endpoints, and critical frontend pages.
- Verify: Every inventory has a reproducible command, denominator, and timestamp.
- Commit: task(P00-08): inventory remediation surfaces
- Accept: Coverage claims use measured denominators.

P00 exit: isolated worktree, reproducible baseline, working guards, and known baseline failures.

---

## Phase P01 — Subscription Safety and Manual Renewal

### P01-01 — Reproduce default lockout

- Depends on: P00-05
- Change: Add a regression test that starts with production-like defaults and proves an active tenant is not disabled by an unconfigured subscription worker.
- Verify: Test fails for historical behavior or existing compliance is proven.
- Commit: task(P01-01): reproduce subscription default lockout
- Accept: The risk has an executable regression.

### P01-02 — Add explicit subscription modes

- Depends on: P01-01
- Change: Implement SUBSCRIPTION_ENFORCEMENT_MODE and SUBSCRIPTION_WORKER_ENABLED with Section 13 defaults.
- Verify: Configuration tests cover missing, valid, and invalid values.
- Commit: task(P01-02): add safe subscription modes
- Accept: Missing configuration means no enforcement.

### P01-03 — Prevent worker-driven tenant deactivation

- Depends on: P01-02
- Change: Remove or gate any path that writes tenant is_active=false solely due to expiry or worker execution.
- Verify: Authentication and clinical-history reads remain available after simulated expiry in off and observe modes.
- Commit: task(P01-03): prevent automatic tenant deactivation
- Accept: Default execution cannot globally lock out a tenant.

### P01-04 — Centralize the state machine

- Depends on: P01-02
- Change: Define trial, active, grace, expired_read_only, suspended_admin, and cancelled transitions. Keep account activation separate.
- Verify: Table-driven tests cover every allowed and forbidden transition.
- Commit: task(P01-04): centralize subscription transitions
- Accept: Routers and workers cannot invent transitions independently.

### P01-05 — Centralize entitlements

- Depends on: P01-04
- Change: Add one service that evaluates limits and write entitlement from tenant, subscription, time, and enforcement mode.
- Verify: Cover trial and grace boundaries, expired reads, blocked new billable writes, admin suspension, and off mode.
- Commit: task(P01-05): centralize subscription entitlements
- Accept: Clinical-history read permission is explicitly invariant.

### P01-06 — Harden manual renewal

- Depends on: P01-04, P03-06
- Change: Make the admin renewal action RBAC-protected, cross-tenant safe, idempotent, date-validating, and append-only audited with performed_by_id.
- Verify: Duplicate, unauthorized, invalid-date, cross-tenant, rollback, and successful cases.
- Commit: task(P01-06): harden audited manual renewal
- Accept: Repeating the same request cannot extend twice.

### P01-07 — Align subscription UI

- Depends on: P01-05
- Change: Show status, expiry, limits, read-only reason, and contact-admin instructions. Add no charging action, gateway SDK, transaction confirmation, or provider callback.
- Verify: Component tests cover all state-machine states.
- Commit: task(P01-07): align subscription UI with manual renewal
- Accept: The UI never promises electronic charging.

P01 exit: safe defaults, centralized entitlement, idempotent manual renewal, and no charging integration.

---

## Phase P02 — Remove Dangerous Database HTTP Surfaces

### P02-01 — Inventory export and restore routes

- Depends on: P00-08
- Change: Find every route, service, UI action, permission, schema, and test for full SQL download, upload, backup creation, or restore.
- Verify: Compare router registration with generated OpenAPI.
- Commit: task(P02-01): inventory database HTTP surfaces
- Accept: Aliases and legacy routes are included.

### P02-02 — Specify disabled-route contracts

- Depends on: P02-01
- Change: Test production-like behavior for anonymous, tenant admin, platform admin, alternate methods, and legacy paths.
- Verify: Full SQL download and restore produce 404 or an intentionally documented disabled response.
- Commit: task(P02-02): specify disabled SQL contracts
- Accept: High privilege alone does not expose full SQL.

### P02-03 — Disable full SQL download

- Depends on: P02-02
- Change: Remove route registration or gate it behind a local-development-only control impossible in production mode.
- Verify: Production-like OpenAPI excludes it and contract tests pass.
- Commit: task(P02-03): disable full SQL download
- Accept: No HTTP response streams a complete dump.

### P02-04 — Disable HTTP SQL restore

- Depends on: P02-02
- Change: Remove restore route registration and UI triggers. Keep only a guarded offline operator command if needed.
- Verify: OpenAPI, route tests, and frontend tests expose no restore action.
- Commit: task(P02-04): remove SQL restore HTTP surface
- Accept: A web request cannot execute restoration.

### P02-05 — Restrict the backup UI

- Depends on: P02-03, P02-04
- Change: Show safe metadata or a runbook link only. Hide dump paths, credentials, raw errors, and destructive controls.
- Verify: UI test asserts allowed fields and forbidden controls.
- Commit: task(P02-05): restrict backup administration UI
- Accept: Remaining UI cannot retrieve or restore SQL.

### P02-06 — Prevent route regression

- Depends on: P02-03, P02-04
- Change: Add a test that rejects forbidden route names and patterns in production OpenAPI.
- Verify: A synthetic forbidden route is detected by the test.
- Commit: task(P02-06): prevent SQL route regression
- Accept: Refactors cannot silently reintroduce the surface.

P02 exit: full database SQL cannot cross a production HTTP boundary.

---

## Phase P03 — Safe Logging, Error Contracts, and Audit Integrity

### P03-01 — Inventory sensitive logging

- Depends on: P00-08
- Change: Classify request body, exception, header, token, patient identifier, clinical text, AI prompt, and provider response logging.
- Verify: Save denominator and command without saving matched values.
- Commit: task(P03-01): inventory sensitive logging
- Accept: Raw exception persistence is included.

### P03-02 — Build a bounded sanitizer

- Depends on: P03-01
- Change: Redact authorization, cookies, secrets, phones, national IDs, email, address, clinical fields, prompts, and nested data. Bound depth, fields, and value length.
- Verify: Cover dictionaries, lists, exceptions, Unicode, synthetic Arabic text, circular objects, and oversized values.
- Commit: task(P03-02): add bounded log sanitizer
- Accept: Sanitization cannot raise while handling an error.

### P03-03 — Sanitize persisted SystemError rows

- Depends on: P03-02
- Change: Store safe category, stable fingerprint, correlation ID, and redacted context instead of raw exception bodies.
- Verify: Secret and PHI canaries are absent from persisted rows.
- Commit: task(P03-03): sanitize persisted system errors
- Accept: Records remain actionable without raw sensitive data.

### P03-04 — Remove master codes and token logs

- Depends on: P03-02
- Change: Delete the hard-coded 2FA master value and runtime logging of access, refresh, reset, or verification tokens.
- Verify: Auth tests and repository scans cover historical patterns.
- Commit: task(P03-04): remove master code and token logging
- Accept: No runtime bypass or token value remains.

### P03-05 — Define public exception contracts

- Depends on: P03-02
- Change: Add tests for validation, authentication, authorization, not-found, conflict, rate-limit, and internal errors.
- Verify: Assert status, stable public code, correlation ID, content type, and absence of internals.
- Commit: task(P03-05): define exception contracts
- Accept: Client-visible behavior is explicit before handler wiring.

### P03-06 — Fix impersonation attribution

- Depends on: P03-02
- Change: Use performed_by_id for the real actor and store the impersonated subject separately in the same transaction.
- Verify: Success, rollback, unauthorized, nested denial, and actor/subject tests.
- Commit: task(P03-06): correct impersonation audit identity
- Accept: Audit history cannot accuse the impersonated user of the actor's action.

### P03-07 — Register exception handlers once

- Depends on: P03-03, P03-05
- Change: Register existing global handlers at application construction. Remove duplicates only after contract comparison.
- Verify: Contract suite, OpenAPI smoke, and representative router tests.
- Commit: task(P03-07): register sanitized exception handlers
- Accept: Internal errors are safe and consistently shaped.

P03 exit: logs and stored errors are sanitized, exception contracts are stable, and audit actor identity is correct.

---

## Phase P04 — Migration Safety and Schema Truth

### P04-01 — Inventory migration topology

- Depends on: P00-04, P00-08
- Change: Enumerate heads, branches, merge revisions, local-branch revisions, ORM tables, and metadata differences.
- Verify: Alembic history and repository script agree.
- Commit: task(P04-01): record migration topology
- Accept: Multiple heads or missing revisions are explicit.

### P04-02 — Build ephemeral PostgreSQL

- Depends on: P00-06, P04-01
- Change: Add a local container or fixture with required extensions and a non-BYPASSRLS application role.
- Verify: Start, print sanitized target, query current_database, and tear down.
- Commit: task(P04-02): add ephemeral PostgreSQL harness
- Accept: PostgreSQL and RLS proof never relies on SQLite.

### P04-03 — Test blank-to-head

- Depends on: P04-02
- Change: Upgrade an empty ephemeral database from base to every intentional current head.
- Verify: Introspect tables, constraints, indexes, functions, triggers, and policies.
- Commit: task(P04-03): test blank database upgrades
- Accept: Blank installation reaches one coherent schema state.

### P04-04 — Test N-1-to-head

- Depends on: P04-03
- Change: Upgrade to the predecessor, seed representative synthetic rows, then upgrade to head.
- Verify: Data survives and schema assertions pass.
- Commit: task(P04-04): test existing-version upgrades
- Accept: create_all plus stamp is not migration proof.

### P04-05 — Detect schema drift

- Depends on: P04-03
- Change: Compare Alembic head with ORM metadata and approved database-only objects. Require reasons in an allowlist.
- Verify: A synthetic mismatch fails.
- Commit: task(P04-05): detect migration and ORM drift
- Accept: Unexplained drift cannot pass.

### P04-06 — Decide attachments.note intent

- Depends on: P04-01, P04-05
- Change: Use schemas, UI, tests, code references, and history to decide keep or remove for the column in c9d0e1f2a3b4.
- Verify: DECISIONS.md includes data preservation, compatibility, and rollback.
- Commit: task(P04-06): decide attachment note schema truth
- Accept: Historical migration is never edited.

### P04-07 — Add a forward correction

- Depends on: P04-06
- Change: Create a new migration and matching ORM/schema change. Preserve existing data if removal or transformation is required.
- Verify: Blank, N-1, safe downgrade, and drift tests.
- Commit: task(P04-07): align attachment note schema
- Accept: Current head has coherent schema truth.

### P04-08 — Replace stamp-only verification

- Depends on: P04-04, P04-05
- Change: Update local CI scripts/workflows to perform real PostgreSQL upgrades. Do not activate hosted schedules.
- Verify: Run the exact local CI command.
- Commit: task(P04-08): enforce real migration checks
- Accept: Fresh-create/stamp cannot masquerade as upgrade proof.

P04 exit: blank and N-1 PostgreSQL upgrades pass, drift is detected, and schema correction is forward-only.

---

## Phase P05 — Authentication, TLS, Pagination, Lint, and Rate Limiting

### P05-01 — Make GeoIP non-blocking

- Depends on: P03-02
- Change: Replace blocking GeoIP I/O on the async request path with a bounded async client or executor pattern already approved in the repository.
- Verify: Event-loop responsiveness test, timeout test, provider-error test, and no-request-failure test.
- Commit: task(P05-01): make GeoIP lookup non-blocking
- Accept: GeoIP failure never blocks login or records precise location by default.

### P05-02 — Add GeoIP privacy modes

- Depends on: P05-01
- Change: Implement GEOIP_MODE off, coarse, and full. Default off; coarse stores only minimum operational geography.
- Verify: Mode tests confirm no outbound call in off mode and redacted persistence in coarse mode.
- Commit: task(P05-02): add GeoIP privacy controls
- Accept: Precise location processing is explicit, not accidental.

### P05-03 — Require TLS certificate verification

- Depends on: P00-05
- Change: Remove CERT_NONE and insecure database TLS fallbacks. Centralize SSL context construction.
- Verify: Unit tests reject invalid certificates and accept a trusted local CA fixture.
- Commit: task(P05-03): enforce database TLS verification
- Accept: Production-like settings cannot silently disable certificate validation.

### P05-04 — Add pagination ceilings

- Depends on: P00-08
- Change: Inventory every list endpoint with limit/page_size and set a maximum of 200 unless a stricter domain limit already exists. Preserve existing defaults.
- Verify: Each endpoint rejects or clamps over-limit values according to one documented contract.
- Commit: task(P05-04): bound API pagination
- Accept: No unbounded list query remains.

### P05-05 — Establish a Ruff baseline

- Depends on: P00-05
- Change: Run existing Ruff configuration, classify failures, and make mechanical fixes separately from risky logic.
- Verify: Changed files pass; baseline exclusions are narrow, owned, and documented.
- Commit: task(P05-05): establish Ruff baseline
- Accept: No blanket ignore hides the codebase.

### P05-06 — Add local Ruff CI gate

- Depends on: P05-05
- Change: Add Ruff to the repository's local CI command and workflow definition without triggering remote runs.
- Verify: Exact gate command exits zero locally and a synthetic violation fails.
- Commit: task(P05-06): gate Python lint locally
- Accept: Future changed code cannot bypass current lint rules.

### P05-07 — Wire rate-limit modes

- Depends on: P03-05
- Change: Register the limiter and middleware once, support off/observe/enforce, and centralize client identity.
- Verify: Defaults do not block; observe records safe counters; enforce returns the documented contract.
- Commit: task(P05-07): wire configurable rate limiting
- Accept: Limiting code is live locally without surprise production enforcement.

### P05-08 — Test proxy-aware rate identity

- Depends on: P05-07
- Change: Trust forwarded addresses only from configured proxies and prevent spoofed X-Forwarded-For from choosing arbitrary identities.
- Verify: Direct, trusted-proxy, untrusted-proxy, IPv4, IPv6, and shared-NAT cases.
- Commit: task(P05-08): secure rate-limit client identity
- Accept: Proxy topology cannot collapse all users or allow trivial spoofing.

P05 exit: no event-loop GeoIP block, no insecure TLS fallback, bounded pagination, active lint gate, and tested configurable rate limiting.

---

## Phase P06 — Worker, Outbox, and Background Reliability

### P06-01 — Inventory background lifetimes

- Depends on: P00-08
- Change: Classify create_task, scheduler jobs, worker entry points, session factories, retry loops, and shutdown handling.
- Verify: Every request-scoped fire-and-forget call is listed.
- Commit: task(P06-01): inventory background task lifetimes
- Accept: Background work has a complete denominator.

### P06-02 — Specify request-session lifetime

- Depends on: P06-01
- Change: Add a failing test where a request ends before queued work runs and prove the old AsyncSession cannot be reused.
- Verify: The test captures the historical failure or proves current safety.
- Commit: task(P06-02): specify background session isolation
- Accept: Session ownership is executable, not assumed.

### P06-03 — Replace request fire-and-forget

- Depends on: P06-02
- Change: Route durable work through the outbox or make non-durable work open its own session with bounded lifetime and shutdown tracking.
- Verify: Request completion, rollback, retry, cancellation, and application shutdown tests.
- Commit: task(P06-03): isolate background database sessions
- Accept: No request AsyncSession outlives dependency cleanup.

### P06-04 — Test outbox under FORCE RLS

- Depends on: P04-02
- Change: Run outbox claim, process, retry, and complete using a NOBYPASSRLS worker role and explicit tenant context.
- Verify: Cross-tenant claim is denied and own-tenant event succeeds.
- Commit: task(P06-04): test outbox with enforced RLS
- Accept: Worker correctness does not depend on owner-role bypass.

### P06-05 — Fix outbox tenant context

- Depends on: P06-04
- Change: Make worker tenant context explicit and transaction-local for claim and handling. Fail closed when tenant identity is missing.
- Verify: Concurrency tests prevent double claim and context leakage.
- Commit: task(P06-05): enforce outbox tenant context
- Accept: One tenant's worker transaction cannot read another's event.

### P06-06 — Reject unknown event types

- Depends on: P06-05
- Change: Move unsupported event types to a visible failed/dead-letter state instead of marking them complete.
- Verify: Known, transient-failure, permanent-failure, malformed, and unknown tests.
- Commit: task(P06-06): fail unknown outbox events visibly
- Accept: No unhandled work disappears silently.

### P06-07 — Add worker health and shutdown

- Depends on: P06-03, P06-06
- Change: Expose local worker liveness/readiness state, bounded retry, heartbeat, and graceful shutdown behavior without a public unauthenticated control surface.
- Verify: Startup failure, stale heartbeat, clean shutdown, forced cancellation, and retry exhaustion.
- Commit: task(P06-07): harden worker lifecycle
- Accept: Operators can distinguish healthy, stalled, and stopped workers.

P06 exit: session ownership is safe, outbox is RLS-correct, unknown events are visible, and workers shut down predictably.

---

## Phase P07 — Metrics, Alerts, and Incident Readiness

### P07-01 — Protect metrics exposure

- Depends on: P03-05
- Change: Implement METRICS_EXPOSURE_MODE off/protected. In protected mode require the repository-approved internal auth mechanism.
- Verify: Anonymous requests fail; valid local fixture succeeds; no patient labels exist.
- Commit: task(P07-01): protect metrics endpoint
- Accept: Public production-like mode cannot expose metrics.

### P07-02 — Wire request instrumentation once

- Depends on: P07-01
- Change: Register instrumentation without double counting and exclude health/metrics noise as documented.
- Verify: One request increments once; exception and latency histograms update; labels stay low-cardinality.
- Commit: task(P07-02): wire bounded request metrics
- Accept: Metrics are correct and PHI-free.

### P07-03 — Create alert event schema

- Depends on: P03-02
- Change: Define safe alert fields: rule, severity, fingerprint, first/last seen, count, safe service context, and runbook link.
- Verify: Schema rejects raw request bodies, exception bodies, tokens, and clinical fields.
- Commit: task(P07-03): define safe alert events
- Accept: Alert payloads are deduplicatable and sanitized.

### P07-04 — Connect threshold evaluation to dispatcher

- Depends on: P07-03
- Change: Wire existing error-rate over 5 percent and p95 over 2000 ms calculations to a transport-neutral dispatcher.
- Verify: Boundary, recovery, deduplication, cooldown, repeated breach, and missing-transport tests.
- Commit: task(P07-04): dispatch monitoring threshold alerts
- Accept: Threshold results no longer end as unused return values.

### P07-05 — Add optional webhook transport

- Depends on: P07-04
- Change: Add a bounded-timeout, retry-limited webhook adapter controlled by ALERT_DISPATCH_ENABLED. Never log URL secrets.
- Verify: Local mock covers success, timeout, non-2xx, retry exhaustion, and disabled mode.
- Commit: task(P07-05): add safe alert webhook transport
- Accept: No external call occurs without explicit configuration.

### P07-06 — Add incident runbooks

- Depends on: P07-04
- Change: Write runbooks for API down, database unavailable, high error rate, high latency, worker stalled, backup failed, suspected tenant leak, suspected PHI exposure, and subscription lockout.
- Verify: Each has trigger, impact, first five actions, evidence, containment, recovery, communication, and post-incident steps.
- Commit: task(P07-06): add incident response runbooks
- Accept: Every alert rule links to a runbook.

### P07-07 — Add optional error aggregation

- Depends on: P03-03, P07-03
- Change: Inventory the declared ddtrace dependency and removed Sentry code. Either remove truly unused telemetry dependencies or add one privacy-reviewed, transport-neutral error-aggregation adapter behind ERROR_AGGREGATION_ENABLED.
- Verify: Disabled mode sends nothing; local mock proves fingerprinting, deduplication, sanitization, timeout behavior, and no request-body capture.
- Commit: task(P07-07): add optional safe error aggregation
- Accept: The codebase has no falsely declared active telemetry and no unguarded external error sink.

### P07-08 — Prepare external uptime specification

- Depends on: P07-06
- Change: Write a provider-neutral specification for /health/live with interval, regions, timeout, consecutive-failure threshold, maintenance handling, recipients, escalation, and test-incident evidence.
- Verify: Validate the health route locally and confirm the specification contains no secret.
- Commit: task(P07-08): specify external uptime monitoring
- Accept: Hosted monitor creation remains H-03, but all required settings are reviewable.

P07 exit: metrics are protected, thresholds dispatch safely in local tests, and incident response is documented. Creating an external monitor remains external.

---

## Phase P08 — Backup, Restore, and Recoverability

### P08-01 — Define backup threat model

- Depends on: P02-04, P07-06
- Change: Document assets, encryption boundary, key ownership, storage boundary, retention, checksum, failure notification, and restore authority for database and attachments.
- Verify: No real credentials or provider-specific claims without evidence.
- Commit: task(P08-01): document backup threat model
- Accept: Database and file recovery are both in scope.

### P08-02 — Add offline backup command

- Depends on: P00-06, P08-01
- Change: Create or harden an operator-only command that writes encrypted local test artifacts atomically and never serves them through HTTP.
- Verify: Ephemeral database backup succeeds; partial failure leaves no valid-looking artifact.
- Commit: task(P08-02): add guarded offline backup command
- Accept: The command refuses unsafe database targets in local verification.

### P08-03 — Add manifest and checksum

- Depends on: P08-02
- Change: Produce a non-sensitive manifest with format version, timestamps, schema revision, artifact list, sizes, checksums, and encryption metadata identifiers.
- Verify: Tampering and truncation are detected.
- Commit: task(P08-03): add backup integrity manifest
- Accept: Restore never trusts filename alone.

### P08-04 — Implement scheduler integration disabled by default

- Depends on: P06-06, P08-02
- Change: Add a durable outbox/worker schedule path controlled by BACKUP_SCHEDULER_ENABLED, singleton locking, idempotency, and explicit missed-run behavior.
- Verify: Disabled, due, duplicate, overlap, missed, failure, and retry tests.
- Commit: task(P08-04): add disabled backup scheduler
- Accept: Code is locally ready but no hosted schedule is created.

### P08-05 — Add isolated restore verifier

- Depends on: P08-03
- Change: Restore only into a newly created ephemeral target after guard, checksum, format, and schema checks.
- Verify: Wrong key, corrupt artifact, wrong format, unsafe target, and successful restore.
- Commit: task(P08-05): add guarded restore verifier
- Accept: Restore cannot overwrite the source or an existing shared database.

### P08-06 — Add round-trip recovery test

- Depends on: P08-05
- Change: Seed synthetic multi-tenant data, back up, destroy only the ephemeral target, restore to another ephemeral database, and compare approved invariants.
- Verify: Counts, selected hashes, tenant isolation, migrations, and representative attachments metadata match.
- Commit: task(P08-06): test backup restore round trip
- Accept: A successful dump alone is not counted as recoverability.

### P08-07 — Write recovery operator runbook

- Depends on: P08-06
- Change: Document prerequisites, authority, target validation, key access, restore steps, integrity verification, RLS validation, abort criteria, and evidence cleanup.
- Verify: Dry-run the runbook entirely on ephemeral resources.
- Commit: task(P08-07): document verified recovery procedure
- Accept: Another developer can reproduce the local round trip.

P08 exit: offline encrypted backup and isolated restore are locally proven. Provider scheduling, retention, and PITR verification stay external.

---

## Phase P09 — Tenant Ownership and RLS Completion

The five mandatory direct-ownership tables are ToothStatus, Prescription, Attachment, MaterialSession, and StockMovement. Exact parent paths must be derived from current foreign keys and ORM relationships; do not guess them from this document.

### P09-01 — Build a complete table-classification register

- Depends on: P00-08, P04-05
- Change: Classify every model/table as global, tenant-direct, tenant-indirect, or unresolved. Record sensitivity, owner path, RLS, ORM filtering, indexes, and deletion/export coverage.
- Verify: Registry denominator equals model/table inventory.
- Commit: task(P09-01): classify all tenant data tables
- Accept: Zero unclassified tables.

### P09-02 — Create read-only ownership preflight

- Depends on: P09-01
- Change: Add SQL/report code that derives the intended tenant through authoritative parent joins and reports null, orphan, ambiguous, and cross-tenant rows for each of the five tables.
- Verify: Synthetic fixtures trigger every anomaly class.
- Commit: task(P09-02): add tenant ownership preflight
- Accept: The report never mutates data.

### P09-03 — Add nullable tenant columns

- Depends on: P09-02, P04-04
- Change: Add nullable tenant_id foreign keys and indexes for the five tables in an expand migration.
- Verify: Blank, N-1, upgrade, downgrade, and drift tests.
- Commit: task(P09-03): expand tenant ownership columns
- Accept: Existing rows remain valid during expansion.

### P09-04 — Backfill deterministic ownership

- Depends on: P09-03
- Change: Backfill tenant_id using the documented authoritative parent paths. Abort the migration on ambiguous or orphan rows; never assign a default tenant.
- Verify: Correct, null, orphan, ambiguous, and cross-tenant synthetic datasets.
- Commit: task(P09-04): backfill tenant ownership safely
- Accept: Every populated value is explainable by a parent relationship.

### P09-05 — Make application writes tenant-explicit

- Depends on: P09-03
- Change: Update services and CRUD creation/update paths to set and validate tenant_id directly for all five tables.
- Verify: Own-tenant success, missing context fail, forged tenant fail, and parent/child mismatch fail.
- Commit: task(P09-05): make sensitive writes tenant-explicit
- Accept: No new row depends on later join-based inference.

### P09-06 — Make reads tenant-explicit

- Depends on: P09-05
- Change: Add direct tenant predicates through the central ORM isolation mechanism while retaining necessary parent authorization.
- Verify: List, detail, export, search, eager-load, and raw-query negative tests.
- Commit: task(P09-06): enforce direct tenant reads
- Accept: Forgetting a parent join cannot expose another tenant.

### P09-07 — Enforce database constraints

- Depends on: P09-04, P09-05
- Change: Validate foreign keys, set tenant_id NOT NULL where classification requires it, and add parent/tenant consistency constraints or safe triggers only when relational structure cannot express them.
- Verify: Existing-version migration with data plus mismatch insertion tests.
- Commit: task(P09-07): enforce tenant ownership constraints
- Accept: The database rejects ownerless direct-sensitive rows.

### P09-08 — Add and force RLS

- Depends on: P09-06, P09-07
- Change: Add SELECT/INSERT/UPDATE/DELETE policies with WITH CHECK parity, enable RLS, and FORCE RLS on all five tables.
- Verify: NOBYPASSRLS role tests own-tenant access, cross-tenant denial, missing-context denial, and context reset.
- Commit: task(P09-08): enforce RLS on five sensitive tables
- Accept: Database isolation is fail-closed.

### P09-09 — Add adversarial concurrency tests

- Depends on: P09-08
- Change: Interleave two tenants across pooled connections and transactions for the five tables.
- Verify: No tenant setting survives checkout, rollback, error, or concurrent request boundaries.
- Commit: task(P09-09): test pooled RLS isolation
- Accept: Connection reuse cannot leak context.

### P09-10 — Make audit log append-only

- Depends on: P03-06, P09-08
- Change: Remove tenant UPDATE/DELETE rights from audit rows, provide controlled correction-by-new-event semantics, and document privileged retention authority.
- Verify: Tenant can insert permitted events and read permitted history but cannot update/delete.
- Commit: task(P09-10): enforce append-only audit policy
- Accept: Tenant actors cannot rewrite their trail.

### P09-11 — Add tamper-evident audit checkpoints

- Depends on: P09-10
- Change: Add a versioned hash-chain or signed-checkpoint design for audit events using stable canonical serialization. Implement locally only if key management is not required for correctness; otherwise implement unkeyed chain verification and place signed checkpoint activation on external hold.
- Verify: Insert, chain verification, modified row, deleted row, reordering, concurrency, and version-upgrade tests.
- Commit: task(P09-11): add tamper-evident audit verification
- Accept: Tampering becomes detectable without allowing tenant mutation.

P09 exit: all models are classified, the five PHI tables have direct ownership, constraints and FORCE RLS, and adversarial tests pass.

---

## Phase P10 — Privacy, AI Egress, Retention, and RAG

### P10-01 — Create the data-processing map

- Depends on: P09-01
- Change: Document each data category, source, purpose, tenant, patient relationship, storage, encryption, processor, destination, retention candidate, deletion/export path, and legal-decision owner.
- Verify: Cover Supabase/PostgreSQL, backend hosting, frontend hosting, attachments, Google Drive paths, logs, backups, analytics, AI, and RAG.
- Commit: task(P10-01): map DENTIX data processing
- Accept: Unknown facts are labeled unknown, never guessed.

### P10-02 — Centralize outbound AI policy

- Depends on: P00-08, P03-02
- Change: Route every provider call through one policy service implementing EXTERNAL_AI_PHI_MODE. Default deny when input may contain PHI or tenant context is missing.
- Verify: Direct provider-call scan, deny/deidentified/contracted tests, missing-config test, and bypass-attempt test.
- Commit: task(P10-02): centralize external AI egress policy
- Accept: Tools cannot call a provider around the policy layer.

### P10-03 — Gate clinical voice workflows

- Depends on: P10-02
- Change: Apply the central gate to parse_medical_dictation, add_treatment_voice, and every clinical transcription or generation path. Show a stable safe unavailable response when denied.
- Verify: Synthetic named-patient dictation never reaches the mock provider in deny mode.
- Commit: task(P10-03): gate clinical voice AI egress
- Accept: Default local and unconfigured production-like modes transmit no clinical content.

### P10-04 — Build a measurable de-identification pipeline

- Depends on: P10-02
- Change: Replace phone/national-ID-only scrubbing with a pluggable pipeline for names, identifiers, contacts, addresses, dates, record numbers, and free-text clinical context. Preserve clinical utility only where measurable.
- Verify: Versioned synthetic Arabic/English benchmark records precision, recall, false negatives, and utility. No claim of perfect anonymization.
- Commit: task(P10-04): add measured clinical de-identification
- Accept: Deidentified mode fails closed when confidence or processing fails.

### P10-05 — Add patient processing ledger schema

- Depends on: P04-05, P10-01
- Change: Add generic records for patient, purpose, legal-basis category, consent state where applicable, policy version, actor, captured/withdrawn timestamps, provenance, and immutable audit reference. Do not invent legal copy.
- Verify: Migration tests plus grant, withdrawal, supersession, no-consent-required category, and cross-tenant tests.
- Commit: task(P10-05): add patient processing ledger
- Accept: Code can prove which policy decision governed a processing event.

### P10-06 — Add retention engine in dry-run mode

- Depends on: P10-01, P10-05
- Change: Inventory retention-bearing entities and implement candidate selection, legal hold, tenant scoping, dry-run report, idempotent deletion orchestration, and audit events. Default to dry-run.
- Verify: Boundary dates, legal hold, cross-tenant, repeat run, partial failure, and export-before-delete tests.
- Commit: task(P10-06): add dry-run retention engine
- Accept: No real retention period is activated without approved policy.

### P10-07 — Enforce isolated RAG mode

- Depends on: P09-08, P10-02
- Change: Keep RAG off unless storage provides database-enforced tenant ownership or an equivalently tested isolation boundary. Add direct tenant ownership, filtered retrieval, deletion, and export support.
- Verify: Cross-tenant nearest-neighbor adversarial tests, missing-context denial, forged metadata denial, and pooled-context tests.
- Commit: task(P10-07): enforce isolated tenant RAG
- Accept: Metadata supplied by the caller is not the sole isolation control.

### P10-08 — Complete encryption coverage inventory

- Depends on: P09-01, P10-01
- Change: Map sensitive fields to encryption, deterministic search hashes, key IDs, rotation support, backups, and plaintext migration risk. Add tests for newly identified critical gaps that can be fixed locally.
- Verify: Round-trip, wrong-key, rotation compatibility, hash lookup, and no-plaintext-log tests.
- Commit: task(P10-08): audit sensitive field encryption
- Accept: Remaining gaps are explicit tasks in the External Hold Queue or local follow-ups.

P10 exit: all AI calls cross a default-deny gate, clinical voice paths are covered, retention is dry-run only, RAG is fail-closed, and legal unknowns are visible.

---

## Phase P11 — API Contracts, Documentation, and Maintenance

### P11-01 — Establish one version source

- Depends on: P00-01
- Change: Choose the repository-authoritative version source and make FastAPI metadata, root response, package metadata, frontend display, and release manifest read from it or from a generated build value.
- Verify: A test asserts equality and catches the historical 2.0.8/2.0.0/0.0.0 drift.
- Commit: task(P11-01): unify application version
- Accept: One deliberate version value is exposed everywhere.

### P11-02 — Add an OpenAPI tag registry

- Depends on: P11-01
- Change: Define ordered tags with descriptions, ownership, and security notes; attach every router to registered tags.
- Verify: OpenAPI test rejects unknown and untagged operations except explicitly documented infrastructure routes.
- Commit: task(P11-02): register OpenAPI domain tags
- Accept: API documentation is navigable by humans.

### P11-03 — Inventory response-model coverage

- Depends on: P00-08, P11-02
- Change: Generate endpoint, method, success statuses, current schema, response_model presence, pagination shape, and compatibility-risk inventory.
- Verify: Denominator equals production OpenAPI operation count.
- Commit: task(P11-03): inventory API response contracts
- Accept: The historical 138-endpoint claim is replaced by current measured data.

### P11-04 — Add typed response models in bounded child tasks

- Depends on: P11-03
- Change: Generate child IDs P11-04-001 onward, maximum five endpoints per child. Add typed success models without changing JSON shape; document any intentional exception.
- Verify: Per child, snapshot or contract comparison, OpenAPI validation, targeted router tests, and frontend consumer check.
- Commit: task(P11-04-NNN): type selected API responses
- Accept: Every operation is typed or has a narrow documented waiver. Partial progress remains visible.

### P11-05 — Write human onboarding

- Depends on: P00-04
- Change: Add First Week for a Human Developer covering architecture, setup, local services, migrations, tests, tenant context, PHI handling, workers, release boundaries, common failures, and safe sample data.
- Verify: Follow commands in a fresh local environment or container as far as available.
- Commit: task(P11-05): add human developer onboarding
- Accept: It does not require reading AI-agent-specific documents first.

### P11-06 — Create a dead-code and legacy ledger

- Depends on: P00-08
- Change: Classify rate_limiter.py, paginated_response, and accounting/metrics/laboratories legacy chains as active, duplicate, compatibility, or removable. Remove only proven unreachable code with tests.
- Verify: Import scan, route inventory, test references, and build pass.
- Commit: task(P11-06): classify and prune proven dead code
- Accept: No code is deleted merely because it looks unused.

### P11-07 — Repair known contract/migration drift

- Depends on: P04-08, P11-03
- Change: Resolve file_number dual-shape compatibility and the c1d2e3f4a5b6 RLS-local-setting issue through forward-safe code/migrations and explicit tests.
- Verify: Old and new supported shapes, real N-1 upgrade, RLS fail-closed, and client contract tests.
- Commit: task(P11-07): repair known contract and migration drift
- Accept: Compatibility windows and later cleanup conditions are documented.

### P11-08 — Reconcile design documentation

- Depends on: P12-08
- Change: Update DESIGN.md from actual token sources, including the historical primary-color drift, RTL rules, states, accessibility, and component ownership. Do not change product colors merely to match stale prose.
- Verify: A small token-consistency script or test compares documented generated values with source tokens where practical.
- Commit: task(P11-08): align design documentation with tokens
- Accept: Documentation describes the implemented design system.

P11 exit: one version source, human-readable OpenAPI, measured typed-response progress, onboarding, and controlled legacy cleanup.

---

## Phase P12 — Frontend Reliability and Server State

### P12-01 — Define frontend error taxonomy

- Depends on: P03-05
- Change: Centralize handling for offline, timeout, unauthenticated, forbidden, not-found, validation, conflict, rate-limit, and server error while preserving page-specific information.
- Verify: Unit tests map each backend contract to the intended UI state.
- Commit: task(P12-01): define frontend error taxonomy
- Accept: Global interception does not erase page errors.

### P12-02 — Fix Dashboard failure states

- Depends on: P12-01
- Change: Add explicit loading, empty, stale, partial, retrying, offline, and failed states. Never render zero totals as if a failed request succeeded.
- Verify: Component tests and local browser check with mocked failures.
- Commit: task(P12-02): make Dashboard failures visible
- Accept: Users can distinguish no data from unavailable data.

### P12-03 — Fix Patients and Patient Details

- Depends on: P12-01
- Change: Apply the taxonomy to list, search, details, create/update, pagination, and encrypted-field search paths.
- Verify: Unauthorized, forbidden, offline, empty, timeout, server failure, and retry tests.
- Commit: task(P12-03): harden patient page states
- Accept: Failed clinical loads never look like an empty patient record.

### P12-04 — Fix Appointments and clinical workflow pages

- Depends on: P12-01
- Change: Apply explicit states to appointments, treatments, prescriptions, tooth chart, attachments, and voice actions. Respect AI denied mode.
- Verify: Maximum two pages per generated child commit with component and browser tests.
- Commit: task(P12-04-NNN): harden selected clinical pages
- Accept: Every inventoried critical clinical page has visible failure and retry behavior.

### P12-05 — Fix finance, inventory, and admin pages

- Depends on: P12-01, P01-07
- Change: Apply explicit states to invoices/accounting, materials/stock, laboratories, metrics, tenant administration, and subscription status.
- Verify: Maximum two pages per child; test empty versus failure and authorization states.
- Commit: task(P12-05-NNN): harden selected operational pages
- Accept: Financial/API failure cannot display a misleading success state.

### P12-06 — Migrate tenant server state

- Depends on: P12-01
- Change: Move tenant server data from tenant.store.js to the existing query library incrementally; keep only true local UI state in the store.
- Verify: Cache key includes tenant identity; logout and tenant switch purge data; mutation invalidation works.
- Commit: task(P12-06): isolate tenant server-state cache
- Accept: One tenant's cached data cannot appear after switching.

### P12-07 — Pilot schema-driven forms

- Depends on: P12-03
- Change: Use react-hook-form plus zod or the repository-approved equivalents on one high-value form without broad redesign.
- Verify: Client/server validation parity, RTL errors, keyboard navigation, unsaved-change behavior, and API error mapping.
- Commit: task(P12-07): pilot typed clinical form
- Accept: Pilot yields a reusable pattern and migration checklist.

### P12-08 — Verify RTL, accessibility, and PWA behavior

- Depends on: P12-02 through P12-07
- Change: Check focus, labels, directionality, offline shell, update prompt, cache invalidation, and error visibility across changed routes.
- Verify: Lint, accessibility checks, local browser matrix, production build, and service-worker smoke.
- Commit: task(P12-08): verify frontend compatibility
- Accept: Security and error changes do not break RTL or installed-PWA flows.

### P12-09 — Add local onboarding and synthetic demo data

- Depends on: P12-03, P12-04, P01-05
- Change: Add a resumable first-run wizard and an explicit local-only synthetic demo-data generator. Never enable demo seeding in production mode.
- Verify: New tenant, resume, skip, completed, failed seed, cleanup, RTL, and production-mode denial tests.
- Commit: task(P12-09): add safe onboarding and demo flow
- Accept: A developer can evaluate key workflows without importing real patient data.

P12 exit: critical pages distinguish failure from empty data, tenant cache is isolated, and changed PWA/RTL flows pass.

---

## Phase P13 — Performance, Database Quality, and Local Release Preparation

### P13-01 — Define local SLO measurements

- Depends on: P07-02
- Change: Document latency, error, worker-lag, and critical-flow measures; create a localhost-only k6 configuration with synthetic data.
- Verify: HTTP guard rejects live targets and a localhost smoke run completes.
- Commit: task(P13-01): define guarded performance baseline
- Accept: No unexecuted performance claim is presented as fact.

### P13-02 — Audit physical tenant indexes

- Depends on: P09-01
- Change: Introspect actual PostgreSQL indexes and query patterns for tenant-scoped tables; compare leading columns, selectivity, and duplicate indexes.
- Verify: Synthetic EXPLAIN plans before/after each proposed index.
- Commit: task(P13-02): audit tenant index coverage
- Accept: Add or remove indexes only with measured local evidence.

### P13-03 — Add justified indexes

- Depends on: P13-02
- Change: Add forward migrations for proven missing tenant_id and composite indexes, avoiding redundant write cost.
- Verify: N-1 migration, index introspection, representative EXPLAIN, and write smoke.
- Commit: task(P13-03): add measured tenant indexes
- Accept: Every new index has a query and plan reference.

### P13-04 — Validate financial constraints

- Depends on: P04-04
- Change: Inventory all NOT VALID financial and integrity checks, generate anomaly preflight queries, fix only synthetic fixtures locally, and add forward VALIDATE operations.
- Verify: All current constraints, not a remembered count, are validated on ephemeral seeded data.
- Commit: task(P13-04): validate database integrity constraints
- Accept: The report replaces the historical estimate of 27 with current evidence.

### P13-05 — Evaluate name search safely

- Depends on: P13-02, P10-08
- Change: Write an ADR comparing deterministic encrypted search, normalized hashes, pg_trgm on non-sensitive derived values, and privacy risk. Implement only the approved safe local option.
- Verify: Arabic/English synthetic accuracy, plan, leakage analysis, and tenant filter tests.
- Commit: task(P13-05): improve privacy-safe patient search
- Accept: Plaintext PHI is not introduced for convenience.

### P13-06 — Build a local release manifest

- Depends on: P11-01
- Change: Generate frontend/backend versions, commit, migration head, compatibility range, build timestamp, and artifact checksums without publishing.
- Verify: Repeated build from same source has documented deterministic/non-deterministic fields.
- Commit: task(P13-06): generate local release manifest
- Accept: Reviewer can identify exactly what was built.

### P13-07 — Draft disabled rollout and rollback automation

- Depends on: P13-06, P08-07
- Change: Prepare but do not execute workflow logic for previous-good revision, post-deploy canary, guarded rollback, frontend/backend compatibility, and evidence capture. Keep schedules and deploy triggers disabled.
- Verify: Static workflow validation and mock/local script tests only.
- Commit: task(P13-07): prepare disabled rollout safeguards
- Accept: No hosted job, deployment, or rollback is triggered.

P13 exit: local performance evidence, justified indexes, validated constraints, release identity, and non-executing rollout safeguards exist.

---

## Phase P14 — Full Local Verification and Handoff

### P14-01 — Run backend quality gates

- Depends on: all backend code tasks
- Change: Run formatting check, Ruff, type checks if configured, test collection, full backend tests, coverage, Bandit, dependency audit, and migration suites.
- Verify: Record commands, duration, pass/fail counts, coverage, and known baseline comparison.
- Commit: no code change; evidence commit allowed
- Accept: No new unexplained backend failure.

### P14-02 — Run frontend and PWA gates

- Depends on: all frontend tasks
- Change: Run clean dependency install if allowed, lint, unit/component tests, production build, E2E on local services, accessibility checks, and PWA smoke.
- Verify: Record environment and results; never target live endpoints.
- Commit: evidence only
- Accept: No new unexplained frontend failure.

### P14-03 — Run database and isolation gates

- Depends on: P04, P06, P09, P10, P13 database tasks
- Change: Recreate ephemeral PostgreSQL, run blank and N-1 migrations, drift, constraints, RLS/BOLA/concurrency, backup/restore, retention dry-run, and RAG isolation tests.
- Verify: Use NOBYPASSRLS role and save sanitized summary.
- Commit: evidence only
- Accept: All mandatory tenant and migration safety tests pass.

### P14-04 — Run local full-story smoke

- Depends on: P14-01 through P14-03
- Change: Start production-like local backend/frontend and synthetic database. Exercise login, tenant switch, patient lifecycle, appointment, treatment, prescription, attachment metadata, inventory, manual renewal, expiry read-only, worker event, metrics protection, and AI-denied behavior.
- Verify: Browser, API, database effects, and logs agree; no secret or PHI canary leaks.
- Commit: evidence only
- Accept: The complete local story works with no external dependency.

### P14-05 — Audit the final diff and commits

- Depends on: P14-04
- Change: Review commit graph, diffstat, changed migrations, public contracts, environment examples, dependency locks, accidental generated files, secret scan, PHI scan, and TODO/FIXME additions.
- Verify: Each changed file maps to a task; no remote refs changed.
- Commit: task(P14-05): finalize remediation evidence
- Accept: Unrelated or unexplained edits are removed safely.

### P14-06 — Write the reviewer handoff

- Depends on: P14-05
- Change: Complete LOCAL_REVIEW_HANDOFF.md using Section 20, list exact commit range, passes, failures, blocked external work, risky migrations, feature defaults, rollback map, and reviewer priorities.
- Verify: Every assertion links to a task, commit, test, or evidence path.
- Commit: task(P14-06): prepare local review handoff
- Accept: Reviewer can start without reconstructing the run.

### P14-07 — Mark LOCAL_REVIEW_READY and stop

- Depends on: P14-06
- Change: Set ledger summary to LOCAL_REVIEW_READY, print final local branch, commit range, git status, verification summary, and blockers.
- Verify: git status is clean except explicitly documented evidence generated after final commit; no push/deploy command appears in shell history captured by the run.
- Commit: task(P14-07): mark local remediation review ready
- Accept: Stop. Do not execute Section 21.

P14 exit: the owner has a clean, evidence-backed local implementation to review.

---

## 15. Autonomous Queue Scheduler

The executor must maintain two queues:

1. Local Execution Queue: tasks that can be completed using repository files, synthetic data, local services, and ephemeral infrastructure.
2. External Hold Queue: legal approvals, provider configuration, live data checks, hosted monitoring, real deployment, and online promotion.

Selection algorithm:

1. Load the ledger.
2. Find tasks with NOT_STARTED status whose dependencies are terminal and not failed in a way that invalidates them.
3. Prefer the lowest phase number.
4. Within a phase, prefer Critical, then High, then Medium, then Low risk.
5. Set one task IN_PROGRESS.
6. Execute the task loop.
7. Retry an identical failing command no more than twice without a code or configuration change.
8. Use at most three repair cycles for an atomic task.
9. After three unsuccessful repair cycles, record LOCAL_FAIL with root-cause evidence and continue to independent tasks.
10. At a phase boundary, run the phase gate before opening the next risk-bearing phase.
11. Never wait for an external response. Record BLOCKED_EXTERNAL immediately and continue.
12. Repeat until no locally executable task remains.

Dependency interpretation:

- LOCAL_PASS and SKIPPED_ALREADY_SATISFIED satisfy dependencies.
- NOT_APPLICABLE satisfies a dependency only when evidence proves the dependent behavior is also irrelevant.
- BLOCKED_EXTERNAL permits a dependent local scaffold task only if that task can remain disabled and honestly tested with mocks.
- LOCAL_FAIL blocks tasks that rely on the failed invariant, but not unrelated phases.
- DEFERRED_OWNER permits only the safest fail-closed implementation.

Interruption recovery:

- Update the ledger before and after each task.
- Create a checkpoint commit at least once per completed phase.
- Record the last command and next eligible task.
- On process restart, verify HEAD and git status, then resume from the ledger instead of repeating completed tasks.

---

## 16. High-Risk Change Procedures

### 16.1 Migration procedure

Every schema task follows:

1. Discover current heads and deployed-history clues from repository evidence.
2. Never rewrite an existing revision that may have run anywhere.
3. Create an expand migration first.
4. Make application code compatible with old and expanded schemas when a rolling window is possible.
5. Run a read-only preflight for data anomalies.
6. Backfill deterministically; abort on ambiguity.
7. Validate constraints separately.
8. Enable and force RLS only after tenant ownership is populated and application writes are explicit.
9. Remove compatibility code only in a later cleanup migration.
10. Prove blank, N-1, and seeded upgrade paths.
11. Test downgrade only to the declared safe point. Do not promise data-reversing downgrade where impossible.
12. Record lock and duration considerations for future hosted execution.

Migration rollback policy:

- Before contract: application rollback must still understand nullable expanded columns.
- After backfill but before NOT NULL: code rollback is safe if old code ignores the new column.
- After RLS/NOT NULL: rollback must use a reviewed forward correction or a compatibility release; never disable RLS as an emergency shortcut.
- No destructive column drop belongs in the same future hosted release as initial expansion.

### 16.2 Tenant isolation procedure

For each sensitive table:

1. Name the authoritative parent relationship.
2. Prove parent uniqueness per row.
3. Add a nullable direct tenant owner.
4. Backfill only through authoritative relationships.
5. Reject ownerless and ambiguous rows.
6. Set owner directly on new writes.
7. Add direct owner predicates on reads.
8. Validate FK and NOT NULL.
9. add SELECT policies using the transaction-local tenant setting;
10. add INSERT/UPDATE WITH CHECK parity;
11. define DELETE policy explicitly;
12. enable RLS and FORCE RLS;
13. test with NOBYPASSRLS;
14. test pooled connection context reset;
15. cover export and tenant purge;
16. update the classification register.

No service-role or table-owner test counts as RLS proof.

### 16.3 Error and logging procedure

Safe internal error record:

- correlation_id;
- timestamp;
- service/module;
- stable error category;
- stable fingerprint;
- safe operation name;
- tenant identifier only when authorized and required;
- bounded redacted metadata;
- stack trace only in a protected local/development sink after sanitization.

Never persist or transmit:

- Authorization or Cookie;
- access, refresh, reset, or verification tokens;
- passwords or secret keys;
- full request/response bodies;
- raw database URLs;
- patient name, phone, national ID, address, medical history, notes, diagnosis, dictation, prescription text, or attachment content;
- raw provider prompt or completion;
- arbitrary exception string without sanitization.

### 16.4 Subscription procedure

The safe enforcement order is:

1. off: calculate nothing that changes access;
2. observe: calculate state and log only sanitized counters;
3. enforce: block only newly billable writes defined by the entitlement service;
4. preserve clinical-history reads;
5. keep administrative suspension separate and explicitly authorized;
6. require an audited manual renewal transition;
7. never change tenant is_active because a clock crossed an expiry boundary;
8. never automatically reactivate an administratively suspended tenant;
9. use database time consistently;
10. test exact boundary timestamps and time zones.

### 16.5 External AI procedure

For each AI feature:

1. classify whether input can contain PHI;
2. identify provider, region, retention behavior, training behavior, and contractual status as known or unknown;
3. route through the central policy;
4. in deny mode, make no provider call;
5. in deidentified mode, require benchmarked transformation and fail closed;
6. in contracted mode, require an externally approved configuration marker, not just a secret being present;
7. record only safe metadata such as feature, provider ID, policy mode, latency, token counts, and result status;
8. provide a user-visible unavailable state;
9. test direct-call bypass scanning;
10. maintain an immediate kill switch.

### 16.6 Backup procedure

A local backup test is successful only when:

- the source is ephemeral;
- the artifact is encrypted;
- a manifest and checksum exist;
- partial output cannot appear complete;
- the artifact restores into a different new ephemeral target;
- schema revision is compatible;
- representative data and tenant isolation survive;
- synthetic attachment metadata and file-integrity rules are covered;
- test artifacts are removed safely after evidence is recorded.

The local run does not prove provider PITR, retention, off-site durability, real attachment backups, or recovery time in a hosted environment.

### 16.7 Rate-limit procedure

Before enforce mode:

- identify trusted proxy hops;
- distinguish authenticated user, tenant, and IP dimensions;
- avoid high-cardinality metrics;
- define exemptions for health and internal callbacks narrowly;
- test shared-clinic NAT;
- test IPv6;
- specify 429 response and Retry-After;
- verify state-store failure behavior;
- provide off and observe rollback modes.

---

## 17. Verification Matrix

The executor must discover repository-specific paths and scripts first. The commands below are preferred patterns, not permission to ignore repository instructions.

### 17.1 Backend

| Check | Preferred command pattern | Required result |
|---|---|---|
| Locked install | uv sync --frozen | Success or documented lock issue |
| Import smoke | uv run python -c with application import | Success |
| Collection | uv run pytest --collect-only -q | No new collection error |
| Targeted tests | uv run pytest path::test -q | Pass per task |
| Full suite | uv run pytest -q | No new failure |
| Coverage | repository coverage command | At least existing 52 percent gate; no reduction |
| Ruff | uv run ruff check . | Pass |
| Format | uv run ruff format --check . | Pass if configured |
| Types | repository mypy/pyright command | Pass or baseline documented |
| Bandit | repository security command | No new high-confidence issue |
| Dependencies | repository safety/audit command | No newly introduced known critical issue |

Do not mechanically raise coverage by excluding files. Critical changed modules require meaningful branch tests even if the global floor remains 52 percent.

### 17.2 Database

| Check | Required database | Required result |
|---|---|---|
| Blank upgrade | Ephemeral PostgreSQL | Base to head passes |
| N-1 upgrade | Ephemeral PostgreSQL with seed | Data survives |
| Drift | Head schema versus metadata | No unexplained drift |
| Downgrade | Declared safe range only | Pass |
| Constraints | Seeded anomalies and valid rows | Invalid rejected, valid accepted |
| RLS | NOBYPASSRLS role | Own allowed, cross denied |
| Pool isolation | Two tenants and reused connections | No context leak |
| Backup round trip | Two ephemeral databases | Invariants match |

### 17.3 Frontend

| Check | Preferred command pattern | Required result |
|---|---|---|
| Locked install | npm ci or repository equivalent | Success |
| Lint | npm run lint | Pass |
| Unit/component | npm test -- --run or configured command | Pass |
| Production build | npm run build | Pass |
| E2E | configured Playwright command against localhost | Critical flows pass |
| Accessibility | configured axe/lighthouse/local check | No new critical issue |
| PWA | local production preview | Install/update/offline shell smoke passes |

### 17.4 Security and privacy

- Secret/PHI changed-file scan passes.
- Historical master code scan returns no runtime match.
- Token-bearing logging scan returns no runtime match.
- Direct external AI-call inventory has zero bypasses.
- Production OpenAPI contains no full SQL dump/restore route.
- Metrics are absent or protected.
- Cross-tenant BOLA tests pass for all five remediated tables.
- SystemError and alert canary tests contain no sensitive value.
- Dependency changes have a reason and lockfile.

### 17.5 Performance

- Target is loopback only.
- Dataset is synthetic and versioned.
- Record local hardware/container limits.
- Run smoke, steady, and short burst profiles.
- Report p50, p95, p99, error rate, throughput, and database pool behavior.
- Treat local results as comparative evidence, not production capacity.

### 17.6 Clean-room build

Before handoff:

1. create a fresh local checkout/worktree from the final local branch;
2. install from locks;
3. run migrations on a new ephemeral PostgreSQL instance;
4. build frontend and backend production artifacts;
5. run the local full-story smoke;
6. compare release manifest and expected migration head.

If resources prevent the clean-room run, mark P14 LOCAL_FAIL or a clearly justified local limitation. Do not silently omit it.

---

## 18. Change Budgets and Rollback Controls

| Change class | Maximum atomic scope | Required rollback |
|---|---|---|
| Router contract | Five endpoints | Revert commit or compatibility flag |
| Frontend reliability | Two pages | Revert child commit |
| Migration expand | One ownership concept | Compatible code plus forward correction |
| Migration contract | One validated constraint group | Reviewed forward correction |
| RLS | One table or tightly coupled group | Application compatibility; never blanket-disable |
| Worker | One event/lifecycle behavior | Disable worker flag |
| Monitoring transport | One adapter | Disable alert flag |
| External AI | One policy/gated feature group | EXTERNAL_AI_PHI_MODE=deny |
| Subscription enforcement | One transition/entitlement group | mode=off |
| Rate limiting | One identity/policy group | mode=off |
| Backup scheduler | Scheduler only | enabled=false |

No commit should combine:

- tenant schema expansion and RLS enforcement;
- exception contract definition and unrelated router refactor;
- subscription enforcement and tenant account activation;
- external AI permission and de-identification algorithm;
- backup generation and HTTP exposure;
- performance optimization and broad formatting;
- frontend server-state migration and visual redesign.

---

## 19. External Hold Queue — Do Not Execute Locally

The executor must create local scripts, templates, mocks, and runbooks where requested, then mark these items BLOCKED_EXTERNAL. It must not perform them.

| Hold ID | External action | Local deliverable only | Future proof required |
|---|---|---|---|
| H-01 | Query real staging/production anomaly counts | Read-only preflight script | Signed/sanitized result and timestamp |
| H-02 | Verify provider backups and PITR | Provider checklist and restore runbook | Settings screenshots/exports and test restore evidence |
| H-03 | Create uptime monitoring for /health/live | Monitor specification | Monitor ID, interval, regions, recipients, test incident |
| H-04 | Configure alert destination | Mock-tested adapter and environment docs | Delivery test and redacted receipt |
| H-05 | Create error aggregation projects | Disabled adapters and privacy checklist | Project settings, retention, redaction, test event |
| H-06 | Approve Egyptian PDPL program | Data map, processing ledger, open legal questions | Counsel-approved basis, notices, retention, breach process |
| H-07 | Approve external LLM processing | Default-deny code and vendor questionnaire | DPA, residency, retention/training terms, approved mode |
| H-08 | Approve patient-facing consent wording | Generic schema and UI placeholder | Approved Arabic/English text and version |
| H-09 | Set real retention periods | Dry-run engine | Approved category schedule and legal holds |
| H-10 | Verify attachment storage backup | Local integrity tooling | Provider inventory and restore sample |
| H-11 | Run migrations on shared data | Migration package and preflight | Reviewed result, backup proof, maintenance authorization |
| H-12 | Reconcile remote main/staging ancestry | Local comparison report | Reviewed merge strategy and protected-branch action |
| H-13 | Enable hosted workers or schedules | Disabled-by-default code | Hosted config, owner, alerting, rollback test |
| H-14 | Enable rate-limit enforcement | Observe/enforce code | Proxy proof, observe metrics, approved thresholds |
| H-15 | Expose protected metrics to collector | Protected mode | Network/auth config and scrape proof |
| H-16 | Run load tests against staging | Guarded scripts | Written authorization, synthetic tenant, monitoring window |
| H-17 | Deploy to staging | Local release manifest | Reviewed commits and deployment evidence |
| H-18 | Deploy to production | None during this run | Staging soak, approval, rollback readiness |
| H-19 | Publish apps or PWA release | Local build proof | Compatibility review and release approval |

Items that are entirely excluded from this program:

- electronic subscription collection;
- gateway checkout or transaction-confirmation flows;
- provider-specific subscription callbacks;
- automatic charging or automatic paid renewal.

---

## 20. LOCAL_REVIEW_HANDOFF Template

The final handoff must use this exact structure:

### A. Identity

- Repository:
- Local branch:
- Base commit:
- Final commit:
- Commit range:
- Migration head before:
- Migration head after:
- Backend version:
- Frontend version:
- Execution start/end UTC:

### B. Outcome

- Overall state: LOCAL_REVIEW_READY or NOT_READY
- Tasks LOCAL_PASS:
- Tasks SKIPPED_ALREADY_SATISFIED:
- Tasks NOT_APPLICABLE:
- Tasks LOCAL_FAIL:
- Tasks BLOCKED_EXTERNAL:
- Tasks DEFERRED_OWNER:

### C. Highest-Risk Changes

For each:

- task ID and commit;
- old behavior;
- new behavior;
- tests;
- feature default;
- rollback;
- reviewer question.

Mandatory entries: subscription safety, SQL HTTP removal, error sanitization, migration harness, five-table RLS, AI gate, backup/restore, and frontend error behavior.

### D. Verification

- exact commands;
- pass/fail counts;
- duration;
- coverage;
- migration results;
- frontend build;
- E2E;
- secret/PHI scan;
- baseline failures versus final failures.

### E. Migrations

- revision list;
- expand/backfill/contract order;
- data preflights;
- lock considerations;
- rollback/forward-correction strategy;
- confirmation that only ephemeral databases were used.

### F. API and UI Compatibility

- changed routes and schemas;
- compatibility shims;
- removed dangerous routes;
- visible UI changes;
- PWA implications.

### G. External Hold Queue

- hold ID;
- owner needed;
- exact next action;
- local artifact;
- acceptance evidence.

### H. Reviewer Start Here

List no more than ten files or commits in the best review order.

### I. Explicit Declaration

Include:

    No remote branch, pull request, deployment, hosted configuration, shared database, external monitor, or real patient record was mutated during this run.

---

## 21. Post-Review Online Sequence — DO NOT EXECUTE

This section is a future checklist for the owner and reviewer. The local executor must stop before it.

1. Review LOCAL_REVIEW_HANDOFF.md.
2. Review every LOCAL_FAIL, DEFERRED_OWNER, and BLOCKED_EXTERNAL item.
3. Review high-risk commits in isolation.
4. Re-run mandatory tests on the owner's machine.
5. Decide whether to reorder, split, or drop local commits.
6. Decide the canonical remote base and reconcile ancestry explicitly.
7. Prepare small pull requests from reviewed commit groups.
8. Run CI on each pull request.
9. Obtain security review for tenant, auth, logging, backup, and AI changes.
10. Obtain migration review and real-data read-only preflight.
11. Confirm provider backup and restore readiness.
12. Deploy to staging only.
13. Run staging smoke with synthetic data.
14. Keep risky modes off, then enable observe mode one control at a time.
15. Complete the agreed staging soak.
16. Approve production release and rollback target.
17. Deploy compatible backend/frontend order.
18. Run canaries and verify alerts.
19. Enable enforcement only after observed evidence and explicit approval.
20. Backport/reconcile release ancestry according to repository policy.

No step above is implied, started, or authorized by executing this plan locally.

---

## 22. Expected Noticeable Product Changes

After later review and deployment, users should notice:

- the system no longer silently shows empty dashboards when an API call failed;
- critical pages show clear loading, offline, error, and retry states;
- subscription expiry does not erase access to existing clinical history;
- manual renewal is consistent and auditable;
- subscription screens direct users to authorized staff rather than offering online charging;
- unsafe database download/restore actions disappear from web administration;
- external clinical AI features may show a clear unavailable state until privacy approval exists;
- error messages become consistent and do not reveal internals;
- tenant switching no longer risks stale cached data;
- slow or failing background work becomes visible to operators.

Most other changes are intentionally invisible: stronger tenant isolation, verified migrations, safe logs, restore proof, TLS validation, bounded queries, protected metrics, and better tests.

---

## 23. Definition of Done

### 23.1 Local Definition of Done

- All 116 primary task cards have terminal statuses.
- Generated child tasks are individually listed.
- Mandatory containment tests pass.
- Blank and N-1 migration tests pass on ephemeral PostgreSQL.
- Five-table RLS tests pass with NOBYPASSRLS.
- External AI defaults to deny.
- Backup/restore round trip passes locally.
- Backend and frontend full local gates have no new unexplained failure.
- Changed-file secret and PHI scans pass.
- Local commits are small, attributable, and not pushed.
- LOCAL_REVIEW_HANDOFF.md is complete.
- Ledger state is LOCAL_REVIEW_READY.

### 23.2 Production Definition of Done

Production-ready requires the local definition plus completion of the relevant External Hold Queue, reviewed pull requests, hosted CI, real-data preflight, legal decisions, provider recovery proof, staging deployment and soak, alert delivery proof, approved production rollout, canary success, and rollback readiness.

The local executor must never claim the production definition is met.

---

## 24. Risk Register Starter

Copy these into RISK_REGISTER.md and update them during execution:

| Risk | Trigger | Immediate containment | Local rollback |
|---|---|---|---|
| R-01 Existing tenant lockout | Default startup changes access | Set subscription modes off; stop worker | Revert P01 behavior commits |
| R-02 Clinical history blocked | Expired tenant cannot read records | Restore read entitlement invariant | Revert entitlement child |
| R-03 API contract break | Frontend or contract snapshot changes unexpectedly | Keep compatibility response and document | Revert affected endpoint child |
| R-04 Exception handler regression | Status or response shape changes | Disable registration while retaining tests | Revert P03-07 |
| R-05 Sensitive error capture | Canary appears in log, DB, alert, or mock sink | Disable sink; purge only synthetic test data | Revert sink integration |
| R-06 Migration ambiguity | Backfill finds null/orphan/multiple owners | Abort; produce report; never default owner | Revert unapplied local revision |
| R-07 RLS self-lockout | Own-tenant operation fails with NOBYPASSRLS | Keep policy change local; inspect context | Revert table-specific RLS child |
| R-08 RLS leak | Cross-tenant negative test succeeds | Stop dependent tenancy tasks | Revert and fix offending table child |
| R-09 Connection context leak | Tenant survives pool reuse | Disable affected worker/test path | Revert context-management commit |
| R-10 Outbox data loss | Unknown event becomes complete | Move to failed/dead-letter state | Revert handler mapping only if safe |
| R-11 Backup false success | Incomplete/corrupt artifact appears valid | Reject artifact; disable scheduler | Set scheduler false; revert writer |
| R-12 Restore wrong target | Guard cannot prove target ephemeral | Hard stop destructive test | No command runs |
| R-13 External AI bypass | Direct provider call exists | Set AI mode deny and block feature | Revert feature integration |
| R-14 De-identification miss | Benchmark false negative exceeds approved threshold | Keep deidentified/contracted modes unavailable | AI mode deny |
| R-15 Rate-limit outage | Shared users receive incorrect 429 | Keep mode off or observe | RATE_LIMIT_MODE=off |
| R-16 Metrics exposure | Anonymous production-like request succeeds | Set metrics off | METRICS_EXPOSURE_MODE=off |
| R-17 Frontend false empty | Failed API renders success/zero state | Restore explicit error state | Revert page child |
| R-18 Dependency regression | Lockfile introduces incompatible or critical package | Revert dependency and lock changes | Revert task commit |
| R-19 Test concealment | New ignore, skip, xfail, or coverage omission appears | Remove concealment; document real failure | Revert concealment commit |
| R-20 Scope expansion | Charging integration or remote action appears | Remove change and record violation | Revert offending commit |

---

## 25. Historical Finding Traceability

| Finding | Primary tasks | Local proof |
|---|---|---|
| Exception handlers implemented but not registered | P03-05, P03-07 | Exception contract suite |
| Blocking GeoIP in async path | P05-01, P05-02 | Event-loop and timeout tests |
| Hard-coded 2FA code and token logging | P03-04 | Auth tests and repository scan |
| Database TLS CERT_NONE | P05-03 | Invalid/trusted certificate tests |
| Limiter declared but middleware not active | P05-07, P05-08 | Mode and proxy-identity tests |
| Impersonation audit uses wrong actor field | P03-06 | Actor/subject transaction tests |
| Ruff not a gate | P05-05, P05-06 | Local CI command |
| Critical pages hide API failure | P12-01 through P12-05 | Component and local browser tests |
| Monitoring thresholds have no dispatcher | P07-03 through P07-05 | Mock transport and threshold tests |
| No external uptime monitor | P07-08, H-03 | Local specification; external delivery later |
| Metrics are publicly exposed | P07-01, P07-02 | Production-like anonymous denial |
| Error aggregation removed or unused | P07-07, H-05 | Disabled adapter mock and external setup later |
| No incident playbooks | P07-06 | Runbook completeness review |
| API versions conflict | P11-01 | Version equality test |
| Untagged and untyped OpenAPI | P11-02 through P11-04 | Generated OpenAPI inventory |
| Human onboarding absent | P11-05 | Fresh-environment walkthrough |
| Dead and legacy paths increase maintenance | P11-06, P11-07 | Import/route/build evidence |
| Design tokens and DESIGN.md drift | P11-08 | Token consistency evidence |
| External clinical AI may receive PHI | P10-02 through P10-04 | Default-deny and bypass tests |
| Consent/legal-basis record absent | P10-05, H-06, H-08 | Schema tests; legal wording later |
| Retention absent | P10-06, H-09 | Dry-run engine and external policy later |
| Residency/processor map absent | P10-01, H-06, H-07 | Data map with unknowns |
| Five PHI tables lack direct ownership/RLS | P09-01 through P09-09 | Ephemeral PostgreSQL adversarial suite |
| Audit rows tenant-rewritable | P09-10, P09-11 | Append-only and tamper tests |
| RAG isolated by metadata only | P10-07 | Cross-tenant nearest-neighbor tests |
| Backup has no schedule or restore proof | P08-01 through P08-07, H-02, H-10, H-13 | Local round trip; provider proof later |
| Request session reused by background task | P06-01 through P06-03 | Session-lifetime tests |
| Outbox/worker reliability unproven | P06-04 through P06-07 | FORCE RLS and lifecycle tests |
| Unknown events can disappear | P06-06 | Dead-letter tests |
| Subscription defaults can lock tenants | P01-01 through P01-05 | Default and transition tests |
| Manual renewal needs robust audit/idempotency | P01-06, P01-07 | API and UI tests |
| Full SQL dump/restore exposed via HTTP | P02-01 through P02-06 | Production OpenAPI and route tests |
| Pagination can be unbounded | P05-04 | Generated endpoint boundary tests |
| Existing-version migrations untested | P04-02 through P04-08 | Blank, N-1, and drift suite |
| Attachment note schema drift | P04-06, P04-07 | Forward migration tests |
| Tenant indexes and constraints unproven | P13-02 through P13-04 | Introspection, plans, and validation |
| k6 suite never established as evidence | P13-01 | Guarded localhost results |
| Automatic rollback absent | P13-06, P13-07, H-17, H-18 | Local static/mock proof; hosted proof later |

---

## 26. Facts the Local Executor Must Recalculate

Do not preserve these as assumptions:

- current endpoint count and response-model coverage;
- current test count and coverage;
- current model/table count;
- current RLS and tenant-index coverage;
- current NOT VALID constraint count;
- current branch and migration topology;
- current worker registrations;
- current active external provider calls;
- current critical frontend page inventory;
- current dependency vulnerabilities.

The following cannot be proven from local code alone and remain external:

- actual number of active clinics;
- real production/staging bindings;
- which migration revisions have run on shared databases;
- real ownership anomaly counts;
- real backup retention and PITR state;
- alert recipients and escalation ownership;
- processor contracts and data residency;
- approved PDPL legal basis, notices, retention, and breach procedure;
- permission to transmit PHI to an external model;
- production latency, throughput, and recovery time.

If active clinics are later proven to exceed ten, prioritize staged index verification, pool behavior, worker lag, and authorized staging load tests before lower-risk documentation cleanup. This does not lower the priority of PHI isolation or legal compliance.

---

## 27. Final Executor Output

After P14-07, print only a concise summary containing:

1. LOCAL_REVIEW_READY or NOT_READY;
2. local branch;
3. base and final commit;
4. number of passed, failed, skipped, not-applicable, deferred, and external tasks;
5. mandatory gate results;
6. highest-risk unresolved blockers;
7. path to LOCAL_REVIEW_HANDOFF.md;
8. confirmation that no remote or hosted mutation occurred;
9. the sentence: “Stopped before online promotion as required.”

Then end the run.
