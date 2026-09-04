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

1. Non-negotiable safety, tenant isolation, RBAC, data integrity, and privacy constraints.
2. Explicit current user requirement or approved implementation plan (within safety constraints).
3. `PROJECT_STANDARDS.md` (architecture authority).
4. `docs/engineering/DEVELOPMENT_WORKFLOW.md` (development lifecycle authority).
5. This `AGENTS.md` (cross-runtime execution and safety contract).
6. Active product / domain specifications.
7. Relevant `.agents/skills/` instructions.
8. External skills (optional methodology / transport only).
9. General engineering conventions.

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

For development process and execution lifecycle, follow `docs/engineering/DEVELOPMENT_WORKFLOW.md`.

Core principles:
- Account for every requirement and acceptance criterion.
- Implement surgically within the declared scope.
- Run targeted tests during development.
- Report final status truthfully as `DONE`, `PARTIAL`, or `BLOCKED`.
- `PARTIAL` or `BLOCKED` work must never be reported as `DONE`.
- AI assistants must not poll CI in a loop; stop active execution after opening a PR or triggering CI.

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

The active CI configuration (e.g. `.github/workflows/ci.yml`) is the operational source of truth for required test commands and coverage thresholds.

Verification cadence:
- **During coding**: Run fast, targeted tests for modified files.
- **Before PR**: Run relevant subsystem tests, linter, and build checks.
- **At PR Boundary**: CI is the authoritative integration verification gate.

When a baseline test already fails:
- record it,
- do not hide it,
- do not claim your change introduced it unless evidence shows that,
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
