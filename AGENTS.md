# DENTIX Repository Instructions

## 1. Source of Truth

`PROJECT_STANDARDS.md` is the architectural and engineering source of truth for DENTIX.

`PROJECT_STANDARDS.md` defines the canonical DENTIX architecture and engineering conventions.
This `AGENTS.md` defines cross-runtime execution, safety, and completion discipline.
If this file is ever interpreted in a way that conflicts with `PROJECT_STANDARDS.md` on project architecture, `PROJECT_STANDARDS.md` wins.

Before significant implementation work:
1. Read the relevant existing code.
2. Read `PROJECT_STANDARDS.md` before editing.
3. Preserve existing business rules, API contracts, database behavior, authentication, RBAC, and tenant isolation unless the task explicitly requires a change.

If generic guidance conflicts with DENTIX project standards, DENTIX project standards win.

## 2. Instruction Precedence

Apply guidance in this order:

1. Explicit current user requirement or approved implementation plan.
2. Security, tenant isolation, RBAC, data integrity, and privacy constraints.
3. `PROJECT_STANDARDS.md`.
4. This `AGENTS.md`.
5. Task-specific repository documentation.
6. Relevant `.agents/skills/` instructions.
7. General engineering conventions.

Never use lower-priority guidance to override a higher-priority DENTIX rule.

## 3. Architecture Guardrails

Backend:
- Preserve the Router -> Service -> CRUD -> Database flow.
- Keep business logic in services.
- Preserve tenant-aware execution.
- Do not bypass `tenant_scope.py` or equivalent tenant isolation mechanisms.
- Do not change database schema or Alembic migrations unless the task explicitly requires a schema change.

Frontend:
- Preserve React + Vite.
- Use React Query for server state.
- Use Zustand for appropriate client state.
- Do not introduce Redux.
- Reuse the existing shared UI/design system before creating new primitives.

Mobile:
- Preserve the existing Flutter/Dart architecture and conventions.
- Do not duplicate backend business logic into the mobile client.

## 4. Compatibility Rules

Do not:
- break existing API contracts to simplify implementation,
- remove existing features/routes because they are inconvenient,
- hardcode production data,
- replace real data with mock data when real integration exists,
- bypass permission checks,
- expose cross-tenant data,
- silently alter financial calculations,
- silently change doctor/receptionist visibility behavior,
- add production dependencies without a concrete need.

## 5. Execution Discipline

For multi-step or plan-based work:
- Account for every numbered requirement and acceptance criterion.
- Maintain a task ledger during execution.
- Do not silently skip a step.
- Do not mark a phase complete before its verification passes.
- Re-read remaining tasks after each phase.
- Report final status as DONE, PARTIAL, or BLOCKED.
- PARTIAL or BLOCKED work must never be reported as DONE.

When an approved plan exists, execute the approved plan rather than replacing it with a shorter plan.

For multi-ticket or delegated parallel work, apply `dentix-orchestration` in addition to `dentix-plan-execution`:
- **Execution Modes**:
  - `FAST`: Low-risk test, doc, or isolated presentational UI work (touched-file pilot cap <= 3, single subsystem, no shared contracts/auth/finance/migrations/clinical semantics). Uses T1 targeted checks, orchestrator mechanical inspection, and wave PRs.
  - `STANDARD`: Normal product work (wave budget <= 5 tickets in same subsystem/risk family). Uses T1 for production changes, one independent review per wave at wave boundary, T2 wave gate, and wave PRs.
  - `HIGH_RISK`: Closed list (auth, RBAC, tenancy/RLS, finance/money, migrations/schema lineage, security controls, shared contracts, clinical semantics, deployment/governance, irreversible data). Strict `SERIAL_ONLY` by default, independent review per ticket, full T1/T2/T3 verification, and individual PR.
- **Worktree Isolation**: 1 concurrent writer = 1 isolated worktree. Serial wave tickets by a single writer reuse the same worktree with bounded commits.
- **Drift-Abort**: If actual touched production files exceed the declared touch surface or cross subsystem/contract boundaries, immediately stop and reclassify.
- **No Model CI Polling**: Model-driven CI polling is forbidden. After creating a PR or triggering CI, record metadata, set `agent:awaiting-ci`, and stop the model loop.

## 6. Debugging Discipline

Activate `dentix-systematic-debugging` only upon actual failure or regression; do not preload it on clean paths.
Before fixing a bug:
1. Reproduce or establish evidence of the failure.
2. Identify the root cause.
3. Inspect nearby dependent behavior.
4. Make the smallest correct change.
5. Run relevant regression verification.
6. Do not fix one failure by weakening security, validation, tests, or tenant/RBAC behavior.

## 7. Verification

Use the repository's existing test, lint, build, security, and analysis commands.

Do not invent a universal coverage target. The active CI configuration (e.g. `.github/workflows/ci.yml` `--cov-fail-under`) is the sole operational source of truth for coverage thresholds.

Verification Tiers:
- `T0`: Development sanity (syntax/types/lint).
- `T1`: Targeted ticket verification (mandatory for production changes and direct regressions before wave gate).
- `T2`: Wave/phase verification gate (subsystem tests, lint, build, clinical UI visual evidence).
- `T3`: Repository/protected integration (CI PR checks, HIGH_RISK full suites, protected `staging`/`main` pushes).

When a baseline test already fails:
- record it,
- do not hide it,
- do not claim the migration introduced it unless evidence shows that,
- ensure your change introduces no new failure.

## 8. Git Safety

Do not:
- discard unrelated user changes,
- use destructive reset/clean commands casually,
- invent alternate branches when a requested branch cannot be used,
- commit generated secrets or credentials.

Before declaring work complete:
- inspect `git diff`,
- confirm scope,
- run relevant verification,
- list anything not completed.
