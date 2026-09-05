---
name: dentix-orchestration
description: Lean orchestration and router for DENTIX multi-agent development. Classifies risk, creates bounded task briefs, coordinates Codex leader and Antigravity implementer roles, and enforces verification and acceptance gates.
---

# DENTIX Lean Multi-Agent Orchestration

`dentix-orchestration` is a **lean router**, not a competing workflow framework. It operates strictly under [DEVELOPMENT_WORKFLOW.md](../../../docs/engineering/DEVELOPMENT_WORKFLOW.md) (the sole development lifecycle authority) and [PROJECT_STANDARDS.md](../../../PROJECT_STANDARDS.md) (the architecture authority).

The orchestration contract reduces decisions and prevents workflow duplication:
**one workflow, one local task, one clear owner, one implementation route, one review boundary, one PR, one CI decision, one release path.**

---

## 1. Non-Ownership Boundaries

`dentix-orchestration` coordinates tasks and enforces safety gates. It must **NOT** own or redefine:
- CI thresholds or coverage percentages (owned by `.github/workflows/ci.yml`),
- Backend architecture (owned by `PROJECT_STANDARDS.md`),
- Frontend architecture (owned by `PROJECT_STANDARDS.md`),
- Security, tenancy, or RBAC semantics (owned by Layer 1 non-negotiable constraints),
- Branch-protection rules or deployment mechanics.

---

## 2. Two Risk Classes

All DENTIX work is classified into exactly two risk tiers:

### A. NORMAL Work
- **Scope**: Ordinary frontend UI, routine backend services/routers, unit/integration tests, documentation, bug fixes, performance tuning, non-sensitive refactors, isolated product changes.
- **Model Roles**:
  - **Codex Leader**: Plans task, verifies preflight, defines bounded task brief, inspects real `git diff`, and conducts final acceptance review.
  - **Antigravity Implementer**: Implements changes on the dedicated local branch, runs targeted local tests, and reports diff.
- **Review Boundary**: Codex Leader acceptance review based on real `git diff`, declared scope, acceptance criteria, and executed test evidence. (This is acceptance review, not independent review).

### B. HIGH_RISK Work
- **Scope**: Material changes to authentication, RBAC, tenant isolation, RLS policies, billing/finance/payment calculations, database schemas, Alembic migrations, irreversible data transformations, clinical semantics, medical records, security controls, branch governance, or major shared contracts.
- **Writer Policy**:
  - **Sensitive Core**: Authored strictly by **Codex High-Risk Writer**.
  - **Antigravity Adjacent Scope**: Allowed only for tests, documentation, fixtures, presentation-only UI around unchanged contracts, or mechanical support files outside the sensitive core.
- **Review Policy**: Requires a **separate, read-only reviewer context** (Codex Leader, Codex High-Risk Writer, Fresh/Independent Reviewer). A writer reviewing its own summary is strictly forbidden.

---

## 3. Duplicate-Work Guard (Preflight Reconciliation)

Before beginning any substantial implementation:
1. **Inspect Local Branches**: Check for existing branches covering the same task or ticket.
2. **Inspect Remote Branches**: Perform read-only check of `origin` tracking branches.
3. **Inspect Open PRs**: Verify no active PR already implements the feature.
4. **Inspect Ticketed Work**: Search Git history across all refs:
   ```bash
   git log --all --oneline --grep="<TICKET_ID>"
   ```
5. **Reconciliation Decision**: If unreconciled prior work exists, **STOP NEW IMPLEMENTATION**. Choose exactly one explicit path:
   - *Continue*: Resume the existing branch.
   - *Reconcile*: Merge or rebase existing progress.
   - *Supersede*: Explicitly document why previous work is superseded.
   - *Salvage*: Cherry-pick valuable commits into current branch.
   - *Archive*: Move historical work to archive branch.
   *Never create a second implementation silently.*

---

## 4. Delegate Write Safety Contract (Task Brief)

Before delegating execution to an implementer or automated write process, record a structured **Task Brief**:

```text
task_id:         <human-readable identifier, e.g. DTX-CHART-01>
current_branch:  <dedicated branch, e.g. feature/..., fix/..., chore/...>
base_sha:        <starting commit SHA>
status_before:   <clean git status snapshot>
allowed_paths:   <explicit list of directories/files allowed to be modified>
forbidden_paths: <explicit list of off-limits files/areas, e.g. schemas, migrations>
risk_class:      <NORMAL | HIGH_RISK>
timeout:         <bounded execution time limit>
task_brief:      <actionable acceptance criteria and specific test commands>
```

---

## 5. Snapshot, Rollback & Failure Contract

After implementer execution:
1. Inspect `git status --porcelain` against `status_before`.
2. Inspect real `git diff` against `base_sha`.
3. Reject any modification touching `forbidden_paths`.
4. Run targeted verification commands.

### On Failure, Timeout, or Crash:
- If surgical rollback is provable:
  - Restore only delegate-modified paths.
  - Delete only delegate-created files proven absent in `status_before`.
  - Verify working tree matches `status_before`.
- If surgical rollback is not provable:
  - **STOP IMMEDIATELY**.
  - Preserve the diff for developer inspection.
  - Report `FAILED` or `PARTIAL` status with exact failure context.
  - Require explicit human reconciliation.
  - **STRICT PROHIBITION**: Never use `git reset --hard` or `git clean -fd` blindly.

---

## 6. Native Skill Routing Discipline

Do not preload all skills indiscriminately. Load only skills triggered by the active domain:
- Multi-agent coordination / task routing: `dentix-orchestration`
- Multi-phase plan execution: `dentix-plan-execution`
- FastAPI / backend: `dentix-backend-fastapi`
- React / frontend: `dentix-frontend-react`
- Flutter / mobile: `dentix-mobile-flutter`
- Schema / migrations: `dentix-database-migrations`
- Auth / RBAC / tenancy: `dentix-security-tenancy-rbac`
- Performance profiling: `dentix-performance`
- Verification execution: `dentix-testing-verification`
- Actual test/runtime failure: `dentix-systematic-debugging` (failure-only)
- Independent review / sensitive diffs: `dentix-code-review`

---

## 7. PR Boundary & No AI CI Polling

- When local verification passes, prepare the single PR into `staging`.
- **HARD PROHIBITION**: AI assistants must not poll CI in a loop. Active execution stops once a PR is opened or CI is triggered.
