<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Repository Instructions

## 1. Authority

- Architecture authority: `PROJECT_STANDARDS.md`
- Lifecycle authority: `docs/engineering/DEVELOPMENT_WORKFLOW.md`
- Product requirements: Active product and domain specifications
- CI requirements: `.github/workflows/ci.yml`

`PROJECT_STANDARDS.md` wins on architecture. `DEVELOPMENT_WORKFLOW.md` wins on lifecycle.

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
- **Stop after PR**: Stop immediately after opening the PR and reporting its URL. Do not poll CI.
- **Rollout flags**: New clinical features must go behind the existing clinical rollout flag.
- **Tenant table tests**: Every new tenant-scoped table requires an explicit isolation test.

## 4. Verification & Git Safety

- Run targeted tests for changed files before opening a PR.
- PR CI is the authoritative verification gate.
- AI never merges to `staging` or promotes to `main`; Eslam verifies on staging and promotes.
- Progressive disclosure: reference `.agents/skills/` on-demand for security, migrations, testing, and review.
