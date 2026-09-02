---
name: dentix-code-review
description: Review DENTIX diffs or implementations for correctness, regressions, tenant/RBAC security, API compatibility, data integrity, missing tests, maintainability, and scope compliance.
---

# DENTIX Code Review Discipline

## Review Activation Cadence
Review diffs thoroughly when requested or when changes touch sensitive domains:
- Authentication, authorization, or RBAC
- Tenant isolation and Row Level Security (RLS)
- Financial transactions, invoicing, and ledger logic
- Database schemas and Alembic migrations
- Clinical semantics and medical record integrity
- Shared cross-subsystem contracts

## Severity Classification Model

Every finding must be categorized by severity:
- **`CRITICAL`**: Cross-tenant data leak, authentication/authorization bypass, security vulnerability, irreversible data loss, or corrupt financial calculation.
- **`HIGH`**: Broken core business workflow, regression in public API contract, missing tenant filtering, unhandled exception in critical path, or missing migration.
- **`MEDIUM`**: Inadequate error handling, unoptimized database query (N+1), race condition in UI state, missing test coverage, or edge-case defect.
- **`LOW`**: Minor code quality flaw, non-standard naming, dead code, redundant calculation, or suboptimal logging.
- **`NOTE`**: Architectural suggestion, optional refactoring opportunity, or documentation enhancement.

## Review Priority Sequence
Evaluate code diffs in this strict hierarchical order:
1. **Scope & Acceptance Criteria**: Are all requested features/fixes implemented without missing requirements?
2. **Multi-Tenant & RBAC Security**: Does every database query enforce `tenant_id`? Are router endpoints properly guarded?
3. **Data Integrity & Financial Logic**: Are clinic invoices, doctor commissions, and ledger entries accurately calculated?
4. **API & Database Compatibility**: Are backward-compatible contracts and Alembic migrations preserved?
5. **Business Logic & Error Handling**: Are edge cases, invalid inputs, and failure modes handled cleanly?
6. **State & Concurrency**: Are React Query caches invalidated correctly? Are async operations safely awaited?
7. **Test Coverage**: Are unit and integration tests present and passing?
8. **Style & Readability**: Follows clean, idiomatic conventions (evaluated last).

## Review Output Format
For every actionable finding, provide:
- **Location**: `[file_path:line_number]`
- **Severity**: `CRITICAL` | `HIGH` | `MEDIUM` | `LOW` | `NOTE`
- **Impact**: Clear explanation of the defect or security implication.
- **Remediation**: Concrete, code-level suggestion for resolution.
