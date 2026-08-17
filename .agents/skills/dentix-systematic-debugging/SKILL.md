---
name: dentix-systematic-debugging
description: Diagnose and fix DENTIX bugs, exceptions, incorrect behavior, failed requests, slow pages, failing tests, build errors, or regressions using evidence-first root-cause analysis.
---

# DENTIX Systematic Debugging Guide

## 4-Phase Root-Cause Analysis (RCA)

### Phase 1: Problem Definition & Reproduction
- Define the exact discrepancy between **Expected Behavior** and **Observed Behavior**.
- Create a deterministic reproduction step or test case.
- Collect raw logs, stack traces, request payloads, and network responses.

### Phase 2: Failure Layer Isolation
Identify which layer in the DENTIX stack originated the defect:
1. **Frontend**: UI state, React Query cache, component rendering, event handlers.
2. **API/Router**: HTTP endpoint, request validation, parameter parsing, auth middleware.
3. **Service Layer**: Business logic, tenant filtering, status transitions, calculation algorithms.
4. **CRUD / Database**: SQL query construction, joins, constraints, migration mismatch.
5. **Mobile**: Riverpod state provider, Dio network interceptor, navigation route.

### Phase 3: Root Cause Hypothesis & Evidence Validation
- Trace the data and control flow backwards from the point of failure to the origin.
- Formulate a precise hypothesis explaining why the bug occurs.
- Validate the hypothesis against actual logs/debugger output before writing any fix.

### Phase 4: Surgical Fix & Regression Verification
- Implement the minimal, correct code change that resolves the root cause.
- Do NOT make speculative edits across multiple files simultaneously.
- Run the reproduction test to verify the fix passes.
- Run adjacent module test suites to ensure zero collateral regressions.

## Forbidden Anti-Patterns
- **Swallowing Exceptions**: Never use empty `except Exception:` blocks or return fake status codes.
- **Weakening Security**: Never bypass authentication, RBAC, or tenant checks to "resolve" an access bug.
- **Mocking Out Real Tests**: Never change test assertions to fit broken behavior unless the original test requirement was proven invalid.
- **Unrelated Refactoring**: Never modify unrelated code while fixing a specific bug.
