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
- **Test integrity**: Never weaken, skip, or rewrite a test assertion to make a genuinely failing test pass. A failing test reveals a real defect until proven otherwise; silently altering an assertion to hide that failure is equivalent to fabricating a test result.

## 3. Slice Rules

- **Stay in scope**: Solve only the requested task. Do not refactor unrelated code.
- **Protect governance**: Do not edit governance or CI files unless the task explicitly requires it.
- **Stop after PR**: Stop immediately after opening the PR and reporting its URL (CI polling: see §8).
- **Rollout flags**: New clinical features must go behind the existing clinical rollout flag.
- **Tenant table tests**: Every new tenant-scoped table requires an explicit isolation test.

## 4. Execution Routing

- **Clear task**: execute directly.

- **NORMAL work**: Standard changes. Targeted verification during implementation. One real diff inspection before commit.
- **HIGH_RISK work** (auth, RBAC, tenant isolation, RLS, finance/ledger/payments, migrations/schema, irreversible data, clinical semantics, major shared contracts): Activate the relevant DENTIX safety skill. Run relevant verification. Eslam decides per PR: accept after his staging test, or escalate to a stronger-model review. A mandatory stronger-model review of the whole plan precedes promotion to main (see DEVELOPMENT_WORKFLOW).

## 5. Completion Discipline

- Account for every requirement and acceptance criterion. Do not silently shrink scope.
- Do not substitute real implementation with TODO stubs or dummy mocks.
- Report final status as `DONE`, `PARTIAL`, or `BLOCKED`. Never mark work as `DONE` if requirements remain unaddressed.

## 6. Git Safety

- **Preflight reconciliation**: Before starting new implementation on a slice or feature scope, check for existing work covering it: `git branch -a`, `git log --all --oneline --grep="<slice-id>"`, and open PRs. If unreconciled prior work exists, stop and choose one explicit path (continue the existing branch, reconcile/rebase it, or document why it's superseded) rather than silently creating a second parallel implementation.
- **No orphaned local work**: A branch or worktree holding unmerged work must not be left idle across sessions without a remote copy (push the task branch to origin when a PR was requested, otherwise create a verified git bundle). Local-only implementation work is not considered safely stored.
- Do not discard unrelated user changes.
- Do not use destructive reset/clean commands casually.
- Do not invent alternate branches when a requested branch cannot be used.
- Before declaring work complete: inspect `git diff`, confirm scope, run relevant verification, list anything not completed.

## 7. Progressive Disclosure

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

## 8. Remote Boundaries

Local reversible implementation is autonomous once requested.
Push/PR only when remote delivery is included in the user's request.
Merge, deploy, protected-branch, and destructive actions require explicit authorization.
AI assistants must not poll CI in a loop; stop active execution after opening a PR or triggering CI.
