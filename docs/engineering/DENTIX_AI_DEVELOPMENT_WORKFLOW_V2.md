# DENTIX AI Development Workflow V2

## Purpose and authority

This workflow turns an approved DENTIX goal into traceable tickets, isolated implementation, risk-appropriate review, wave-level integration, and repository verification. It is an orchestration contract only. It does not change application behavior, API contracts, database behavior, tenant isolation, RBAC, clinical rules, or financial rules.

When instructions conflict, apply this precedence exactly:

1. Explicit current user requirement or approved implementation plan.
2. Security, tenant isolation, RBAC, data integrity, and privacy constraints.
3. `PROJECT_STANDARDS.md`.
4. Root `AGENTS.md`.
5. Task-specific repository documentation.
6. Relevant native `.agents/skills/` instructions.
7. General engineering conventions.

External delegate or review tooling is transport or an execution engine. It is never a DENTIX policy authority and cannot override this precedence.

## Core V2.1 Lean Architecture

Workflow V2.1 decouples scope tracking from expensive execution cycles:

```text
micro-ticket               = scope and traceability unit
wave or high-risk boundary = review unit
wave or phase              = verification unit (T2)
wave                       = normal PR unit (FAST / STANDARD)
high-risk ticket           = individual PR unit (HIGH_RISK)
release / protected push   = full CI unit (T3)
```

## Roles and decision rights

### User / Product Authority

- Defines the goal, product decisions, approved scope, and acceptance intent.
- Approves meaningful scope expansion and decisions that require new authority.

### Orchestrator

- Inspects repository truth and reads the complete source plan or specification once before dispatch.
- Builds and maintains the ticket ledger, dependency graph, risk classification, execution modes, and execution waves.
- Produces self-contained delegate briefs with explicit touch surfaces and dispatches only ready tickets.
- Reviews returned diffs mechanically or schedules independent wave/ticket reviews based on execution mode.
- Recalculates the dependency graph immediately on drift or contract changes, otherwise at wave boundaries.
- Never treats an implementer's final report as proof and never bypasses repository gates.

### Implementer

- Edits only within one bounded ticket or assigned wave in its isolated worktree.
- Applies the relevant native DENTIX domain skills, respects the declared touch surface, and stops if unexpected production files are required (drift-abort).
- Runs targeted T1 checks for production changes and direct regressions before returning. Cannot verify, merge, close, or release its own work.

### Independent Reviewer

- Reviews requirements against the actual diff in a distinct read-only session or lane.
- Invocation Cadence:
  - **FAST**: Orchestrator mechanical diff/scope inspection only.
  - **STANDARD**: One independent review per wave at the wave boundary (`WAVE_READY`).
  - **HIGH_RISK**: Independent review per ticket.
  - **DWF-11 Debate Review**: Optional, reserved for severe architectural/security disputes; never default.
- Applies `.agents/skills/dentix-code-review/SKILL.md`, including tenant/RBAC, data-integrity, compatibility, and test review.
- Does not edit while acting as reviewer and does not merge on behalf of the orchestrator.

### CI & Status Checks

- Runs repository-defined checks and supplies authoritative technical gate evidence.
- Conditional PR execution routes low-risk checks cleanly while keeping required status contexts materialized.
- Pushes to protected branches (`staging`, `main`) always execute full CI.
- Model-driven CI polling is forbidden. After PR creation, state transitions to `AWAITING_CI` and the model stops.

### Release

- Enforces the governed path `scoped branch -> staging -> main`.
- Production promotion occurs from `staging` to `main`, except documented branch-governance exceptions.
- No implementer, reviewer, or orchestration tool may merge automatically.

## Execution Modes & Risk Classification

Every ticket declares an `execution_mode`:

### 1. FAST
- **Scope**: Tests-only, docs-only, or isolated presentational UI.
- **Constraints**: Touched-file pilot cap <= 3 files, single subsystem, no shared contracts, no auth/RBAC/tenancy/finance/migrations/clinical semantics.
- **Lifecycle**: T1 targeted check where relevant, orchestrator mechanical inspection, wave PR allowed.

### 2. STANDARD
- **Scope**: Ordinary product features, refactors, and non-high-risk UI/backend logic.
- **Constraints**: Wave budget <= 5 tickets in the same subsystem/risk family, no HIGH_RISK tickets mixed in.
- **Lifecycle**: T1 for production changes, one independent review per wave, T2 wave gate, wave PR.

### 3. HIGH_RISK
- **Closed List**:
  - Authentication & Authorization (RBAC)
  - Multi-tenant boundary isolation & PostgreSQL RLS
  - Finance, invoicing, doctor commissions, payment ledgers
  - Database migrations and schema lineage
  - Security controls, cookies, CORS, secrets
  - Shared API, session, or financial contracts
  - Clinical semantics (tooth identity, notation meaning, clinical condition/treatment semantics)
  - Deployment workflows and branch governance
  - Irreversible data operations
- **Constraints**: `SERIAL_ONLY` by default, independent review per ticket, immediate T1, risk-specific T2, full T3, individual PR (1 ticket = 1 PR).

## Clinical Risk Split

To avoid imposing full surgical clinical-semantics overhead on purely presentational rendering:
- `risk:clinical-semantics`: Modifies tooth numbering, notation systems, clinical condition semantics, treatment meanings, or persisted clinical state. Default: `HIGH_RISK`.
- `risk:clinical-ui`: Renderer layout, root visual geometry (source-of-truth unchanged), inspector UI, responsive/RTL layout. Default: `STANDARD` with mandatory visual/screenshot evidence. Escalates to `HIGH_RISK` immediately if semantic data is touched.

## Verification Tiers

- **`T0` (Development Sanity)**: Rapid syntax, typecheck, or lint check during active coding.
- **`T1` (Targeted Ticket Verification)**: Focused unit/integration test for the specific ticket. Mandatory for all production code changes and direct regressions before the wave gate.
- **`T2` (Wave / Phase Gate)**: Comprehensive subsystem lint, test, build, and visual validation executed once at the wave boundary.
- **`T3` (Repository / Protected Integration)**: Full repository CI suites executed on PRs (risk-appropriate) and protected pushes (`staging`/`main`). Operational thresholds are defined by active CI configurations (e.g. `--cov-fail-under`).

## Ticket Lifecycle

```text
DRAFT
  -> READY
  -> IN_PROGRESS
  -> IMPLEMENTED
  -> WAVE_READY
  -> AWAITING_CI
  -> VERIFIED
  -> CLOSED
```

Additional terminal/pause states: `BLOCKED`, `CI_RED`.

- `IMPLEMENTED`: Bounded ticket work returned. FAST/STANDARD tickets reach `IMPLEMENTED` without individual independent reviews.
- `WAVE_READY`: Wave is assembled, ready for wave-level review and T2 verification.
- `AWAITING_CI`: PR is open; AI model stops execution. No polling.
- `VERIFIED`: Wave review and required CI checks have passed.
- `CLOSED`: Traceability recorded.

## Worktree Isolation

- **Concurrent Writers**: 1 concurrent writer = 1 isolated Git worktree and scoped branch. Two write-capable delegates never share a checkout.
- **Serial Wave Reuse**: Serial tickets within the same wave assigned to one implementer reuse a single worktree with distinct, bounded commits per ticket.
- Initial write concurrency cap is 2; raise to 3 only after proven pilot validation.

## PR Strategy

- **Wave PR (FAST / STANDARD)**: One PR per wave combining up to 5 related tickets from the same subsystem, preserving 1 commit per ticket.
- **Individual PR (HIGH_RISK)**: Exactly 1 ticket = 1 PR.
- *Note*: Pilot PRs #120/#122/#123 and #121/#124/#125 demonstrate pilot-only 1-ticket-1-PR baseline evidence, not the daily default for low-risk work.

## Drift-Abort Policy

If an implementer discovers that modifying unlisted production files or crossing subsystem/contract boundaries is necessary:
1. Immediately stop editing.
2. Report the drift to the orchestrator.
3. Orchestrator reclassifies the risk and updates the ticket scope/brief before proceeding.

## CI Interaction: No AI CI Polling

Model-driven polling of GitHub Actions, deployment jobs, or remote workflows is strictly forbidden:
- After pushing a PR or triggering CI, record PR number and commit SHA, set `agent:awaiting-ci`, and stop the model loop.
- Resume occurs on the next invocation by reading the deterministic GitHub status check / label signal (`agent:ci-green` or `agent:ci-red`).

## Emergency path

Emergency work may skip delegation or parallelism when delay would increase harm. It must not skip security, review, tests, tenant/RBAC protections, data-integrity checks, or branch governance.

## Disable and rollback

This workflow is repository tooling and documentation. Removing its workflow documents, ticket/PR templates, orchestration skill, and approved delegate configuration must not require an application-runtime rollback. External tools are removed through their installation mechanism; credentials and trust metadata remain outside the repository.
