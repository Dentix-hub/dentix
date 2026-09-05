<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Development Workflow

## 1. Overview & Core Lifecycle

DENTIX follows a single, lean, and deterministic development lifecycle:

```text
PLAN / REQUEST
      ↓
ONE ACTIVE FEATURE
      ↓
ONE TEMPORARY FEATURE BRANCH
      ↓
IMPLEMENT
      ↓
TARGETED LOCAL TESTS
      ↓
ONE PR → staging
      ↓
AUTHORITATIVE PR CI
      ↓
REVIEW / ACCEPTANCE WHEN NEEDED
      ↓
MERGE → staging
      ↓
STAGING DEPLOYMENT + PRODUCTION-LIKE SMOKE
      ↓
PROMOTE staging → main WHEN RELEASE-READY
      ↓
PRODUCTION DEPLOYMENT + HEALTH VERIFICATION
      ↓
DELETE TEMPORARY BRANCHES
```

---

## 2. Branching & Environments

* **`main`**: Protected canonical production branch.
* **`staging`**: Protected canonical integration branch.
* **Feature Branches**: Ephemeral, short-lived branches created from and merged into `staging`. Delete feature branches immediately after successful merge.
* **Production Promotion**: Normal production promotion is the current protected `staging` revision into `main`. Do not create a new main-alignment PR after every small feature unless a release is actually intended.
* **Direct `main` Exceptions**: `hotfix/*` and documented `release/*` reconciliation branches remain exceptional paths and must undergo fresh CI because they are not trusted `staging` promotions.

---

## 3. Execution Rules

1. **One Feature at a Time**: Work on one active feature or bugfix per working session.
2. **Issue Discipline**:
   * Small, self-contained fixes do not require a GitHub Issue.
   * Large, multi-session, or product-significant work uses **one GitHub Issue containing a checklist**.
   * Do not create one GitHub Issue per micro-task.
3. **Checkout vs. Worktrees**:
   * Normal serial development uses the primary checkout and a standard branch.
   * Worktrees are not the default; use isolated worktrees only when executing genuinely concurrent, independent write operations.
4. **Task Decomposition**:
   * Keep task breakdown inside the working session or issue checklist.
   * Implementers handle changes end-to-end rather than fragmenting across multiple handoff boundaries.

---

## 4. Verification & Testing

* **During Implementation**: Run fast, targeted unit/integration tests covering the exact changed files and functions.
* **Before PR**: Run relevant subsystem tests, linter, or production build checks when appropriate.
* **PR → `staging` Boundary**: GitHub Actions CI is the authoritative code-validation gate. The deterministic classifier runs only the relevant suites for ordinary changes and forces full validation for sensitive/high-risk changes.
* **Protected Push After Merge**: Do **not** rerun the already-passed full test/build matrix merely because the PR was merged. The protected-branch `Dentix CI` run acts as a lightweight handoff so CD can deploy the exact merged revision.
* **`staging` Runtime Gate**: The deployed staging revision must pass `Dentix CD - HF staging smoke` before it can use the trusted `staging → main` promotion path.
* **`staging → main` Promotion**: Reuse the exact already-validated staging revision. Heavy CI jobs and duplicate secret/mobile builds may be skipped; governance, provenance, branch protection, and staging-smoke evidence remain mandatory.
* **Direct `main` Hotfix/Release**: A `hotfix/*` or `release/*` branch that does not come directly from current `staging` must run fresh CI under the normal classifier rules.
* **Explicit Override**: Applying a supported HIGH_RISK label to a `staging → main` PR intentionally forces fresh full CI if a second validation is desired.
* **Integrity**: Never weaken validation, assertions, RLS/security/finance/clinical checks, or deployment smoke merely to make CI green or faster.

This model is **validate once, promote the validated revision**, not **rerun the same suite at every branch hop**.

---

## 5. Release & Promotion Rules

1. Merge feature/fix work into `staging` only through a protected PR.
2. Let the merge-triggered lightweight `Dentix CI` hand the exact staging revision to CD.
3. Require successful staging deployment and production-like smoke for that exact revision.
4. Promote to `main` from **current `staging`** when release-ready; promotion governance verifies that the PR head is still the protected staging head and that staging smoke succeeded.
5. Do not repeat Backend, Frontend, E2E, RLS, responsive, stale-asset, container, Flutter, or secret scans solely because the same validated revision is moving from `staging` to `main`.
6. After merge to `main`, use the lightweight protected-push CI handoff to trigger the existing production CD and health verification.
7. If the candidate is not the exact current `staging` revision, treat it as a new validation candidate rather than claiming promotion reuse.

---

## 6. Review & CI Interaction

* **Normal Changes**: Standard product/UI changes rely on targeted testing, PR diff inspection, and passing CI.
* **Sensitive Changes**: Mandatory independent review is required when changes materially touch:
  * Authentication, RBAC, or permissions
  * Tenant isolation or Row Level Security (RLS)
  * Finance, invoices, payments, or ledger calculations
  * Database schemas, Alembic migrations, or irreversible data operations
  * Clinical data semantics or medical records
  * Major shared API/UI contracts
* **No AI CI Polling**: AI assistants must not poll CI in a loop. After opening a PR or triggering CI, report the PR URL and stop active execution.

---

## 7. Authority & Legacy Plans

* **Product Plans & Specs**: Authoritative for product requirements, scope, clinical decisions, and acceptance criteria.
* **GitHub Issues**: Authoritative for live task tracking and milestone checklists when used.
* **Pull Requests**: Authoritative for code review and integration state.
* **Protected Git History**: Authoritative truth for executable code.
* **Locked Legacy Plans**: Historical execution mechanics (such as obsolete role matrices, micro-ticket waves, or complex orchestration state machines in earlier plans) are superseded by this document. Product requirements and acceptance criteria in locked plans remain 100% authoritative.
