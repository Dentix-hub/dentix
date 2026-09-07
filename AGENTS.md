<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Repository Instructions

## 1. Authority

| Concern | Canonical Owner |
|---|---|
| Architecture & engineering conventions | `PROJECT_STANDARDS.md` |
| Development lifecycle, Git, PR, CI, release | `docs/engineering/DEVELOPMENT_WORKFLOW.md` |
| Product requirements & acceptance criteria | Active product / domain specifications |
| CI thresholds & required commands | `.github/workflows/ci.yml` |

`PROJECT_STANDARDS.md` wins on architecture. `DEVELOPMENT_WORKFLOW.md` wins on lifecycle.
This file (`AGENTS.md`) defines safety invariants, execution routing, and completion discipline.

If generic guidance conflicts with DENTIX project standards, DENTIX project standards win.

## 2. HARD Invariants

These are non-negotiable. No task, plan, or convenience may override them.

- **Tenant isolation**: Every query touching clinic data must scope by `tenant_id` via `tenant_scope.py`. Do not bypass tenant isolation mechanisms.
- **Server-side RBAC**: Enforce permissions on every endpoint using existing auth dependencies. Never rely solely on frontend UI hiding.
- **Privacy & clinical integrity**: Protect patient PII, medical records, and clinical semantics.
- **Financial integrity**: Do not silently alter financial calculations, doctor commissions, or ledger entries.
- **Data safety**: Do not change database schema or Alembic migrations unless the task explicitly requires it. Never edit applied migrations.
- **API compatibility**: Do not break existing API contracts, remove features/routes, or replace real data with mocks.
- **Secrets**: Never commit generated secrets or credentials.
- **Truthful verification**: Every claimed test result must be backed by executed commands and real exit codes. Report `DONE`, `PARTIAL`, or `BLOCKED` truthfully.

## 3. Architecture Defaults

Detailed conventions are in `PROJECT_STANDARDS.md`. Key constraints:

- **Backend**: Router → Service → CRUD → Database. Keep routers focused on HTTP semantics and delegation. Business logic in services. Tenant-aware execution throughout.
- **Frontend**: React + Vite. React Query for server state. Zustand for client state. No Redux. Reuse shared UI before creating new primitives.
- **Mobile**: Flutter/Dart with existing feature-driven architecture. Do not duplicate backend business logic in the mobile client.

## 4. Execution Routing

```
Clear task → execute directly.
Unclear task → use relevant planning skill when clarification adds value.
Delegate only when delegation is materially cheaper or safer than inline execution.
```

- **NORMAL work**: Standard changes. Targeted verification during implementation. One real diff inspection before commit.
- **HIGH_RISK work** (auth, RBAC, tenant isolation, RLS, finance/ledger/payments, migrations/schema, irreversible data, clinical semantics, major shared contracts): Activate the relevant DENTIX safety skill. Run relevant verification. Require independent review.

## 5. Completion Discipline

- Account for every requirement and acceptance criterion. Do not silently shrink scope.
- Do not substitute real implementation with TODO stubs or dummy mocks.
- Report final status as `DONE`, `PARTIAL`, or `BLOCKED`. Never mark work as `DONE` if requirements remain unaddressed.

## 6. Verification

Follow `docs/engineering/DEVELOPMENT_WORKFLOW.md` for verification cadence:

- **During coding**: Run fast, targeted tests for modified files.
- **Before PR**: Run relevant subsystem tests, linter, and build checks.
- **At PR boundary**: CI is the authoritative integration verification gate.
- Do not rerun expensive verification at the same confidence boundary when no relevant code changed.
- When a baseline test already fails: record it, do not hide it, do not claim your change introduced it, ensure no new failure.

## 7. Git Safety

- Do not discard unrelated user changes.
- Do not use destructive reset/clean commands casually.
- Do not invent alternate branches when a requested branch cannot be used.
- Before declaring work complete: inspect `git diff`, confirm scope, run relevant verification, list anything not completed.

## 8. Progressive Disclosure

Do not preload governance and skills. Default context is this file + user request + relevant code.

Load additional material only on trigger:

| Trigger | Load |
|---|---|
| Architecture uncertainty | `PROJECT_STANDARDS.md` |
| Auth / RBAC / tenancy / RLS | `dentix-security-tenancy-rbac` skill |
| Migration / schema | `dentix-database-migrations` skill |
| Verification gate selection | `dentix-testing-verification` skill |
| HIGH_RISK review | `dentix-code-review` skill |
| Git / PR / release | `docs/engineering/DEVELOPMENT_WORKFLOW.md` |

## 9. Remote Boundaries

Local reversible implementation is autonomous once requested.
Push/PR only when remote delivery is included in the user's request.
Merge, deploy, protected-branch, and destructive actions require explicit authorization.
AI assistants must not poll CI in a loop; stop active execution after opening a PR or triggering CI.
