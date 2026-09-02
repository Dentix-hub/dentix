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
CI
      ↓
REVIEW / ACCEPTANCE WHEN NEEDED
      ↓
MERGE
      ↓
DELETE FEATURE BRANCH
```

---

## 2. Branching & Environments

* **`main`**: Protected canonical production branch.
* **`staging`**: Protected canonical integration branch.
* **Feature Branches**: Ephemeral, short-lived branches created from and merged into `staging`. Delete feature branches immediately after successful merge.

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
* **PR Boundary (CI)**: GitHub Actions CI is the authoritative integration verification gate.
* **Integrity**: Never weaken validation, assertions, or test suites merely to make CI green.

---

## 5. Review & CI Interaction

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

## 6. Authority & Legacy Plans

* **Product Plans & Specs**: Authoritative for product requirements, scope, clinical decisions, and acceptance criteria.
* **GitHub Issues**: Authoritative for live task tracking and milestone checklists when used.
* **Pull Requests**: Authoritative for code review and integration state.
* **Protected Git History**: Authoritative truth for executable code.
* **Locked Legacy Plans**: Historical execution mechanics (such as obsolete role matrices, micro-ticket waves, or complex orchestration state machines in earlier plans) are superseded by this document. Product requirements and acceptance criteria in locked plans remain 100% authoritative.
