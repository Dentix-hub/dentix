# DENTIX AI Development Workflow V2

## Purpose and authority

This workflow turns an approved DENTIX goal into traceable tickets, isolated implementation, independent review, and repository verification. It is an orchestration contract only. It does not change application behavior, API contracts, database behavior, tenant isolation, RBAC, clinical rules, or financial rules.

When instructions conflict, apply this precedence exactly:

1. Explicit current user requirement or approved implementation plan.
2. Security, tenant isolation, RBAC, data integrity, and privacy constraints.
3. `PROJECT_STANDARDS.md`.
4. Root `AGENTS.md`.
5. Task-specific repository documentation.
6. Relevant native `.agents/skills/` instructions.
7. General engineering conventions.

External delegate or review tooling is transport or an execution engine. It is never a DENTIX policy authority and cannot override this precedence.

## Roles and decision rights

### User / Product Authority

- Defines the goal, product decisions, approved scope, and acceptance intent.
- Approves meaningful scope expansion and decisions that require new authority.

### Orchestrator

- Inspects repository truth and reads the complete source plan or specification.
- Builds and maintains the ticket ledger, dependency graph, risk classification, and execution waves.
- Produces self-contained delegate briefs and dispatches only ready tickets.
- Reviews returned diffs, reruns verification independently, and decides whether work is ready for integration.
- Never treats an implementer's final report as proof and never bypasses repository gates.

### Implementer

- Edits only within one bounded ticket or explicitly approved batch in its assigned isolated worktree.
- Applies the relevant native DENTIX domain skills, respects the declared touch surface, and reports unexpected dependencies or scope expansion.
- Runs targeted checks and returns structured evidence, but cannot verify, merge, close, or release its own work.

### Independent Reviewer

- Reviews requirements against the actual diff in a distinct read-only session or lane.
- Applies `.agents/skills/dentix-code-review/SKILL.md`, including tenant/RBAC, data-integrity, compatibility, and test review.
- Does not edit while acting as reviewer and does not relay a merge or commit on behalf of the orchestrator.

### CI

- Runs the repository-defined checks and supplies authoritative technical gate evidence.
- A green implementer-local check does not replace required CI.

### Release

- Enforces the governed path `scoped branch -> staging -> main`.
- Production promotion occurs from `staging` to `main`, except documented branch-governance exceptions.
- No implementer, reviewer, or orchestration tool may merge automatically.

## Ticket lifecycle

Every executable ticket moves through this lifecycle:

```text
DRAFT
  -> READY
  -> IN_PROGRESS
  -> IMPLEMENTED
  -> REVIEW_REQUIRED
  -> VERIFIED
  -> CLOSED
```

`IMPLEMENTED -> CLOSED` is forbidden. `IMPLEMENTED` means the bounded implementation returned; it does not mean acceptance criteria or repository gates passed. A ticket becomes `VERIFIED` only after the orchestrator checks every acceptance criterion, an independent review is complete, and required verification is rerun against the actual diff. Only verified work may be closed.

## Ticket contract and completion evidence

Each AI-executable ticket must state its source plan, problem, objective, scope, non-goals, dependencies, parallel classification, expected touch surface, acceptance criteria, required native skills, risk, verification, and completion evidence. Acceptance criteria must be observable and checklist-based.

The expected touch surface is a review boundary, not permission to omit necessary tests. If an unlisted production file is required, the implementer must stop or explicitly report the scope expansion. Completion evidence includes the actual diff, exact commands and exit statuses, acceptance results, review findings and resolutions, CI state, and known limitations.

## Worktree isolation

- Every write-capable delegate uses its own Git worktree or equivalent isolated checkout and its own scoped branch.
- Two write-capable delegates must never edit the same checkout.
- The orchestrator records the repository, worktree, branch, and base SHA in every delegate brief.
- Delegates cannot edit, commit, merge, or clean another delegate's worktree.
- The orchestrator owns integration and checks `git status`, the full diff, unexpected files, and `git diff --check` after every return.

## Dependency graph

Before dispatch, the orchestrator must:

1. Map every approved requirement to at least one ticket or an explicit justified `N/A`.
2. Record each ticket's dependencies and affected contracts/files.
3. Reject cycles or unresolved prerequisites.
4. Dispatch only tickets whose dependencies are verified.
5. Recalculate the graph after every execution wave or contract change.
6. Reconcile completed tickets against the original plan so no requirement disappears during decomposition.

Tickets should have one coherent objective, one primary seam or module, observable acceptance, and bounded verification. They must be neither uncontrolled multi-day mega-phases nor line-by-line fragments that cannot independently pass acceptance.

## Parallel-safety classification

Every ticket must be exactly one of:

- `PARALLEL_SAFE`: proven independent of all tickets in the same wave.
- `PARALLEL_AFTER:<ticket>`: dispatchable only after the named dependency is verified.
- `SERIAL_ONLY`: must not overlap another write-capable ticket.

No ticket is implicitly parallel-safe. Same-file or same-contract uncertainty collapses parallel work into serial work. Authentication, RBAC, tenant isolation/RLS, finance, related migrations, shared API contracts, central state, deployment workflow, and unsettled shared seams default to `SERIAL_ONLY` unless independence is explicitly proven. The initial pilot permits at most two simultaneous write-capable delegates; the cap may rise to three only after successful validation.

## Risk classification

Every ticket has one or more of these risk tags:

- `LOW`
- `NORMAL`
- `CLINICAL`
- `FINANCE`
- `AUTH_RBAC`
- `TENANCY_RLS`
- `DATABASE_MIGRATION`
- `DEPLOYMENT`
- `SECURITY`

Risk determines required skills, reviewer expertise, serialization, and verification. High-risk work remains serial by default and must not weaken security, privacy, tenant isolation, RBAC, data integrity, or branch governance for speed.

## Execution algorithm

1. Read the complete approved source and repository authorities.
2. Build the full ticket ledger and requirement-coverage map.
3. Resolve dependencies, risks, parallel safety, and execution waves.
4. Create a self-contained brief for every ready ticket.
5. Dispatch only into isolated worktrees.
6. Inspect each returned diff and unexpected scope independently.
7. Apply native DENTIX review policy and rerun required repository checks.
8. Integrate only verified work through a PR to `staging`.
9. Recalculate the remaining graph and run an anti-skip reconciliation after every wave.
10. Report the final program status strictly as `DONE`, `PARTIAL`, or `BLOCKED`.

## GitHub execution conventions

Recommended lifecycle labels are `agent:ready`, `agent:blocked`, `agent:in-progress`, `agent:review`, and `agent:verified`. Parallel labels are `parallel:safe` and `parallel:serial`. Risk labels are `risk:clinical`, `risk:finance`, `risk:auth-rbac`, `risk:tenancy-rls`, `risk:database`, `risk:deployment`, and `risk:security`. Inspect existing labels before creating only those that are missing; never rename unrelated labels.

Map an issue to one scoped branch whose prefix reflects the work:

```text
Issue #341 feature -> feat/dtx-341-odontogram-root-rendering
Issue #342 fix     -> fix/dtx-342-patient-cache-invalidation
Issue #343 tests   -> test/dtx-343-finance-regression-coverage
```

The issue number and source requirement IDs must remain visible in the delegate brief and PR evidence.

Example dependency waves:

```text
Wave 0: foundational contract
Wave 1: A + B in parallel
Wave 2: C after A
Wave 3: D after A+B+C
```

## Emergency path

Emergency work may skip delegation or parallelism when delay would increase harm. It must not skip security, review, tests, tenant/RBAC protections, data-integrity checks, or branch governance.

## Disable and rollback

This workflow is repository tooling and documentation. Removing its workflow documents, ticket/PR templates, orchestration skill, and approved delegate configuration must not require an application-runtime rollback. External tools are removed through their installation mechanism; credentials and trust metadata remain outside the repository.
