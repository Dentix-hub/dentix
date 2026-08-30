---
name: dentix-orchestration
description: Orchestrate approved multi-ticket DENTIX work across dependencies, isolated delegates, worktrees, independent review, and repository verification without replacing domain-specific native skills.
---

# DENTIX Orchestration Discipline

## Purpose

Orchestrate approved DENTIX work across atomic tickets, dependencies, execution modes (`FAST`, `STANDARD`, `HIGH_RISK`), isolated delegates, worktrees, wave review gates, and repository verification without replacing domain-specific DENTIX skills.

Use this skill with `dentix-plan-execution` when work contains multiple tickets, delegated implementation, or parallel execution. Repository authorities and domain skills remain the policy source; delegate and review tools are execution transport only.

## Execution Modes & Budgets

Every ticket is assigned an execution mode:
- **`FAST`**: Tests-only, docs-only, or isolated presentational UI. Touched-file pilot cap <= 3 files, single subsystem, no shared contracts, no auth/RBAC/tenancy/finance/migrations/clinical semantics. Uses T1 targeted checks, orchestrator mechanical inspection, and wave PR.
- **`STANDARD`**: Normal product features/fixes. Wave budget <= 5 tickets in the same subsystem/risk family, no HIGH_RISK tickets mixed in. Uses T1 for production changes, one independent review per wave at `WAVE_READY`, T2 wave gate, and wave PR.
- **`HIGH_RISK`**: Auth, RBAC, tenancy/RLS, finance/money, migrations/schema lineage, security controls, shared contracts, clinical semantics, deployment/governance, irreversible data. Strict `SERIAL_ONLY` by default, independent review per ticket, full T1/T2/T3 verification, and individual PR (1 ticket = 1 PR).

## Clinical Risk Split
- `risk:clinical-semantics`: Tooth identity, notation meanings, condition/treatment semantics. Default: `HIGH_RISK`.
- `risk:clinical-ui`: Rendering layout, tooth geometry (unchanged source of truth), inspector UI, responsive/RTL layout. Default: `STANDARD` with mandatory visual/screenshot evidence.

## Delegate Domain Policy

Select and require only the native skill that owns each ticket's domain:

```text
backend task    -> dentix-backend-fastapi
frontend task   -> dentix-frontend-react
mobile task     -> dentix-mobile-flutter
security task   -> dentix-security-tenancy-rbac
migration task  -> dentix-database-migrations
performance     -> dentix-performance
debugging       -> dentix-systematic-debugging (failure-only)
review          -> dentix-code-review (wave boundary for STANDARD, per-ticket for HIGH_RISK)
verification    -> dentix-testing-verification (gate-triggered)
plan execution  -> dentix-plan-execution
```

Do not restate or weaken those skills. Do not force generic orchestration/review skill lists into simple delegate briefs.

## Required Orchestration Algorithm

1. Read the complete source plan or specification and repository authorities once before dispatch.
2. Build a ledger mapping every requirement and acceptance criterion to a bounded ticket or justified `N/A`.
3. Assign execution mode (`FAST`, `STANDARD`, `HIGH_RISK`), risk tags, and parallel classification (`PARALLEL_SAFE`, `PARALLEL_AFTER:<ticket>`, `SERIAL_ONLY`).
4. Build dependency-ordered execution waves (`wave_id`).
5. Create a self-contained brief for every ready ticket with base SHA, scope, non-goals, declared touch surface, skills, risk, acceptance, and T1 requirements.
6. Dispatch only ready tickets into isolated worktrees. Serial wave tickets assigned to one implementer reuse the same worktree with bounded commits.
7. Implementer enforces drift-abort: stop immediately if unlisted production files or cross-contract changes are needed.
8. Inspect returned diffs. FAST/STANDARD tickets advance to `IMPLEMENTED` without individual independent reviews.
9. At wave completion (`WAVE_READY`), execute wave gate:
   - FAST: Orchestrator mechanical diff/scope inspection.
   - STANDARD: One independent wave review using `dentix-code-review` (distinct reviewer).
   - HIGH_RISK: Review per ticket.
   - Run T2 wave/phase verification.
10. Open wave PR (FAST/STANDARD) or single PR (HIGH_RISK). Set `agent:awaiting-ci` and stop the model loop. Model-driven CI polling is forbidden.
11. On CI completion signal (`agent:ci-green`), integrate via protected branch governance. Never merge automatically.
12. Recalculate the remaining dependency graph immediately on drift or contract changes; otherwise at wave boundaries.
13. Reconcile against the original source and report final program status strictly as `DONE`, `PARTIAL`, or `BLOCKED`.

## Isolation and Parallel Safety

- 1 concurrent writer = 1 isolated Git worktree and scoped branch. Never allow two concurrent writers to edit the same checkout.
- Serial tickets in one wave reuse a single worktree for that implementer.
- Same-file or same-contract uncertainty collapses parallel work into serial work.
- Auth, RBAC, tenant isolation/RLS, finance, related migrations, central state, shared contracts, and deployment work default to `SERIAL_ONLY`.
- Initial write-capable concurrency is at most two; raise to three only after proven pilot validation.

## Evidence and Integration Rules

- An implementer report is a claim, not verification evidence.
- The orchestrator inspects `git status`, full diff, unexpected files, and `git diff --check`.
- A distinct reviewer applies `dentix-code-review` without editing while acting as reviewer.
- Broad verification is rerun using `dentix-testing-verification` governed by active CI commands.
- Delegates and review tooling must never merge, close, or release on behalf of the orchestrator.
