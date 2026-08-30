---
name: dentix-orchestration
description: Orchestrate approved multi-ticket DENTIX work across dependencies, isolated delegates, worktrees, independent review, and repository verification without replacing domain-specific native skills.
---

# DENTIX Orchestration Discipline

## Purpose

Orchestrate approved DENTIX work across atomic tickets, dependencies, isolated delegates, worktrees, independent review, and repository verification without replacing domain-specific DENTIX skills.

Use this skill with `dentix-plan-execution` when work contains multiple tickets, delegated implementation, or parallel execution. Repository authorities and domain skills remain the policy source; delegate and review tools are execution transport only.

## Delegate domain policy

Select and require the existing native skill that owns each ticket's domain:

```text
backend task    -> dentix-backend-fastapi
frontend task   -> dentix-frontend-react
mobile task     -> dentix-mobile-flutter
security task   -> dentix-security-tenancy-rbac
migration task  -> dentix-database-migrations
verification    -> dentix-testing-verification
review          -> dentix-code-review
plan execution  -> dentix-plan-execution
performance     -> dentix-performance
debugging       -> dentix-systematic-debugging
```

Do not restate or weaken those skills. When several domains apply, require every relevant skill.

## Required orchestration algorithm

1. Read the complete source plan or specification and repository authorities.
2. Build a ledger mapping every requirement and acceptance criterion to a bounded ticket or justified `N/A`.
3. Resolve every ticket dependency before dispatch.
4. Assign one or more risk classifications.
5. Assign exactly one parallel classification: `PARALLEL_SAFE`, `PARALLEL_AFTER:<ticket>`, or `SERIAL_ONLY`.
6. Build dependency-ordered execution waves.
7. Create a self-contained, ticket-specific brief containing base SHA, scope, non-goals, touch surface, skills, risk, acceptance, verification, forbidden actions, and report format.
8. Dispatch only ready tickets into separate worktrees or equivalent isolated checkouts.
9. Independently inspect every returned diff and check acceptance criteria one by one.
10. Rerun repository-defined verification independently; implementer evidence is untrusted until reviewer verification.
11. Integrate only verified work through repository branch governance. Never merge automatically.
12. Recalculate the remaining dependency graph after every return, contract change, or integration.
13. Reconcile against the original source and report final status strictly as `DONE`, `PARTIAL`, or `BLOCKED`.

## Isolation and parallel safety

- Every write-capable delegate owns one isolated worktree and scoped branch.
- Never allow two write-capable delegates to edit the same checkout.
- Same-file or same-contract uncertainty collapses parallel work into serial work.
- Auth, RBAC, tenant isolation/RLS, finance, related migrations, central state, shared contracts, and deployment work default to `SERIAL_ONLY` unless independence is explicitly proven.
- The validated operating cap is three simultaneous write-capable delegates. Lower it whenever risk, dependencies, shared seams, or review capacity require; never exceed it.

Example waves:

```text
Wave 0: foundational contract
Wave 1: A + B in parallel
Wave 2: C after A
Wave 3: D after A+B+C
```

## Evidence and integration rules

- An implementer report is a claim, not verification evidence.
- The orchestrator must inspect `git status`, the full diff, unexpected files, and `git diff --check`.
- A distinct reviewer applies `dentix-code-review` without editing while acting as reviewer.
- The orchestrator reruns targeted and required broad checks using `dentix-testing-verification` and current CI commands.
- A ticket cannot move directly from `IMPLEMENTED` to `CLOSED`; independent verification is required.
- Delegates and review tooling must never merge, close, or release on behalf of the orchestrator. A bounded implementer commit is allowed only when the accepted brief explicitly authorizes it.
