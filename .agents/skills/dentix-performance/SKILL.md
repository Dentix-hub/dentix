---
name: dentix-performance
description: Diagnose or improve DENTIX performance for slow API endpoints, patient pages, frontend rendering, network waterfalls, SQL queries, caching, bundle behavior, or Flutter responsiveness.
---

# DENTIX Performance Optimization Guide

## Performance Principles
1. **Measure Before Optimizing**: Never guess bottlenecks. Base all optimizations on concrete execution timing, query logs, or memory profiles.
2. **Preserve Integrity & Security**: Never sacrifice multi-tenant isolation, authorization, or financial accuracy in exchange for raw speed.
3. **Isolate Changes**: Modify one performance variable at a time and measure the delta against the established baseline.

## Diagnostic & Optimization Layers

### 1. Database & SQLAlchemy Layer
- **N+1 Query Elimination**: Use `selectinload` or `joinedload` for eager relationship loading where appropriate.
- **Index Optimization**: Ensure filter columns in WHERE clauses (`tenant_id`, `created_at`, `doctor_id`, `status`) utilize composite indices.
- **Pagination & Query Limits**: Enforce bounded limit/offset or cursor-based pagination for large datasets (patients, audit logs).

### 2. FastAPI & Backend Async Layer
- Ensure all I/O calls (database, external webhooks, Redis cache) use non-blocking `async`/`await`.
- Utilize Redis caching for expensive, read-heavy aggregated metrics while invalidating on writes.
- Offload long-running operations (PDF report generation, bulk notification emails) to background task workers.

### 3. Frontend React & UI Layer
- Optimize React Query cache stale times to eliminate duplicate network requests.
- Lazy load non-critical routes and modal dialogs with `React.lazy` and `Suspense`.
- Minimize unnecessary component re-renders using `useMemo`, `useCallback`, and atomic Zustand selector hooks.

### 4. Mobile Flutter Layer
- Avoid unnecessary widget subtree rebuilds by scoping Riverpod `ref.watch` to specific state properties.
- Use `ListView.builder` for infinite or large lists to prevent memory bloat.

## Performance Reporting Format
When completing an optimization, document:
```text
Performance Optimization Report:
- Target Component: <module / endpoint / page>
- Baseline Metric: <measured time / query count before>
- Optimized Metric: <measured time / query count after>
- Method Applied: <indexing / caching / lazy loading / query join>
- Regression Verification: <test suite execution result>
```
