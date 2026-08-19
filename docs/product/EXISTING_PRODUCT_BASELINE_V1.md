# DENTIX — Existing Product Baseline V1

**Program:** Plan 03 — Existing Product Forensic Improvement  
**Base branch:** `staging`  
**Execution branch:** `refactor/plan-03-existing-product-forensic-improvement`  
**Acceptance model:** existing-product improvements only; no intentional schema/API/product-rule redesign.

## Baseline statement

This document records the accepted existing Dentix product baseline after the Plan 03 forensic pass. The executable code, migrations, route contracts, RBAC matrix and automated tests remain authoritative if documentation conflicts.

Plan 03 found and corrected several high-severity defects that were not visible in the initial rapid scorecard. No unresolved P0/P1 finding is intentionally carried into this baseline. Remaining items are P2/P3 consistency, accessibility or legacy-architecture debt and are explicitly non-blocking for this merge.

## Preserved product contracts

- Existing database schema and migration history preserved.
- Existing public API paths and primary payload contracts preserved.
- Authentication/session model preserved.
- Tenant isolation strengthened; no clinic-scoped route may silently fall back to tenant `1`.
- Existing RBAC matrix remains the authority for user actions, including AI tool execution.
- Existing financial semantics, stock semantics and clinical workflow intent preserved.
- Existing PWA rule remains: API traffic is `NetworkOnly`; application assets may be cached.
- Plan 02 canonical overlay/design-system and visual regression foundation remains authoritative.

## Module closeout

### Patients — accepted baseline

- Patient directory/search/detail paths remain tenant- and visibility-scoped through the existing patient visibility service.
- Recent Patient Workspace V2 baseline and existing regression coverage remain accepted.
- No new P0/P1 was established during Plan 03.
- Accepted P2: the patient-detail tooth-selector remains a local overlay rather than the canonical dialog primitive.

### Appointments — improved and accepted

- Preserved HTTP 404 on missing update instead of converting it to 500.
- Status and delete no-ops now return 404 instead of false success.
- Pending audit work is rolled back on no-op mutations.
- Focused router regressions added.

### Clinical / Dental — improved and accepted

- Fixed repeated treatment-edit stock reversal accumulation by reconciling only the outstanding stock effect of the treatment reference.
- Stock reversal remains idempotent while allowing later usage under the same treatment reference to be reversed correctly.
- Treatment and stock-session overlays migrated to the canonical Dentix dialog foundation with consumer regressions.

### Inventory — improved and accepted

- Removed unsafe `tenant_id or 1` behavior from clinic-scoped inventory boundaries.
- Added explicit tenant-context requirements.
- Added ownership validation for warehouse/material/batch/session/weight mutations where IDs cross service boundaries.
- Smart inventory availability checks no longer accept cross-tenant material/session IDs.
- Debug exposure was constrained at the route boundary.
- Existing stock movement/reversal semantics remain unchanged except for the proven correctness fix above.

### Users / RBAC — improved and accepted

- Closed tenant-user privilege escalation paths.
- Tenant user-management cannot create or promote users into the platform `super_admin` role.
- Backend tenant-user administration now aligns with the existing frontend admin boundary rather than allowing Manager access through `SYSTEM_CONFIG` alone.
- Missing delete returns 404 and self-delete protection is enforced.

### Labs — improved and accepted

- Linked treatment lookup now uses an exact `Link:LabOrder:<id>` identity instead of substring matching; order `1` can no longer match order `10`/`11` treatment links.
- Lab-order and linked-treatment create/update are handled as one transaction rather than committing the order before linkage synchronization.
- Tenant and patient-visibility boundaries remain enforced.

### Dashboard / Analytics — improved and accepted

- Dashboard business-day/timezone and doctor visibility contracts preserved.
- Profitability no longer treats every `Payment.tenant_id IS NULL` record as belonging to the current tenant; legacy attribution is derived through the tenant-owned patient relationship.
- Process-global business event counters are platform telemetry and are no longer exposed to clinic users as tenant business metrics.

### Settings / Pricing / Insurance / Backup — improved and accepted

- Global procedures remain readable by clinics but are read-only from tenant procedure mutation routes.
- Procedure deletion cascades are tenant-scoped.
- Price-list procedure/provider references are validated against global-or-current-tenant ownership as appropriate.
- Google Drive OAuth callback state is signed, short-lived and identity-bound instead of trusting predictable `user_<id>` or raw role strings.
- Tenant backup settings reject missing tenant context cleanly.

### Super Admin — improved and accepted

- Canonical Super Admin Google Drive authorization now generates the same signed/expiring identity-bound OAuth state required by the shared callback.
- The later-registered `system_admin` compatibility router still contains overlapping legacy endpoints; for overlapping method/path pairs FastAPI resolves the earlier `admin_system` route. This duplicate compatibility surface is accepted P2 cleanup debt, not a P0/P1 merge blocker.
- Platform routes continue to require explicit `super_admin` role checks.

### Finance / Billing / Expenses — improved and accepted

- Smart cost-analysis endpoints require explicit tenant context rather than silently falling back to tenant `1`.
- Payment list/create/today/debtors/delete boundaries require tenant context.
- Missing payment delete returns 404 and rolls back the pending audit unit instead of reporting false success.
- Missing expense delete is detected before the audit unit is created/committed, preventing false audit records.
- Existing Finance V2 financial-truth and visibility semantics remain authoritative.

### AI — improved and accepted

- AI tool execution now re-enforces the equivalent domain permission before invoking the handler. `AI_CHAT` alone cannot bypass `FINANCIAL_READ/WRITE`, `CLINICAL_READ/WRITE`, patient, appointment or system permissions.
- Agent session state now receives the authenticated `user_id`; active-patient/session state is separated per user inside a tenant instead of falling back to `user_id=1`.
- Existing confirmation policy, read-only kill switch, request validation, PII scrubbing and tenant-aware handlers remain in place.

### Auth / Public / PWA — accepted baseline

- Auth middleware resolves the database user and tenant context rather than trusting request-side tenant selection.
- Non-super-admin authenticated users without a tenant are rejected.
- Read-only impersonation scope is enforced at the authenticated request boundary.
- Subscription expiry continues to block state-changing requests while preserving allowed reads according to the existing contract.
- PWA API runtime caching remains `NetworkOnly`; no API response is intentionally served from service-worker cache.
- No additional P0/P1 was established during this pass.

## Cross-product consistency closeout

The forensic pass established one repeated defect class and removed it from the audited high-risk paths: clinic-scoped code must never convert missing tenant context into a concrete fallback tenant. The shared `require_tenant_id()` helper is the preferred boundary behavior for clinic-scoped routes that can be reached by platform accounts.

Mutation endpoints audited in this plan now distinguish missing/no-op mutations from successful writes rather than emitting false-green responses in the corrected Appointments, Finance and Users paths.

AI is treated as another product entry point, not a privileged bypass: domain RBAC applies before tool execution.

## Accepted non-blocking debt

- Patient detail tooth-selector local overlay.
- Appointment icon-control/accessibility and legacy Kanban visual-token debt.
- Several older Inventory/Labs/Users/Super-Admin surfaces still use legacy visual patterns; Plan 02 guardrails prevent newly-added regressions, but Plan 03 intentionally avoided mass redesign after correctness/security gates were green.
- Duplicate Super Admin compatibility routes should eventually be consolidated.
- `DENTIX_UI_PRINCIPLES.md` is still absent; executable shared UI/tokens and Plan 02 contracts remain the UI authority.
- Vercel preview build-rate limiting observed during Plan 03 is an external provider/quota condition, not a product-code defect.

## Acceptance gate

This baseline is mergeable only when the final Plan 03 pull-request revision passes the repository-required automated gate: backend tests/coverage, Bandit, Safety, frontend build/tests, production critical Playwright, UI visual regression and design-system guardrails. GitHub Actions on the merge-candidate revision are the source of truth for that final gate.
