# Dentix Super Admin — Executor Protocol

Repository: `Dentix-hub/dentix`
Baseline audited commit: `46584940df522e681e52fac1ec4bc3b7b206793b`
Target implementation branch: `chore/super-admin-existing-capabilities-hardening`

## Mission

Repair, connect, optimize, test, and visually normalize the **existing** Dentix Super Admin capabilities.

## Absolute scope rule

**DO NOT ADD NEW PRODUCT FEATURES.**

You may:
- repair broken existing behavior,
- connect an existing UI to an existing API,
- expose a value/control only when the same capability is already visibly represented by the current UI,
- remove dead/misleading UI,
- improve reliability, performance, responsive behavior, accessibility, dark mode, i18n, and visual hierarchy,
- add tests for existing behavior.

You may NOT:
- invent new admin modules,
- create new dashboards,
- create new billing/security/AI concepts,
- surface orphan backend-only operations as new UI buttons without explicit product approval,
- redesign database/business rules merely for aesthetics.

## Important orphan-capability guard

The repository contains backend/API capabilities that are not necessarily part of the current Super Admin UI, including examples such as:
- purge-deleted-patients helper/API,
- subscription checkout/webhook surfaces,
- duplicate/compatibility admin routes,
- multiple backup API families.

Do **not** add new UI for these just because they exist in code.

## Execution discipline

1. Create `chore/super-admin-existing-capabilities-hardening` from the current `main`.
2. Before changing a microstep, re-read every file listed in that microstep.
3. Implement exactly one microstep at a time.
4. Do not opportunistically refactor unrelated modules.
5. Add/update focused regression tests in the same microstep when practical.
6. Run the microstep's required verification before marking it complete.
7. Make one commit per microstep:
   `super-admin(ms-XX): <short description>`
8. Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.
9. Continue through all microsteps. If one is blocked:
   - mark it `BLOCKED`,
   - record exact reason and evidence,
   - continue with independent steps,
   - never claim the full plan is complete.
10. Never merge to `main`. Push only the implementation branch for review.

## Required ledger entry per step

```md
## MS-XX — <title>
Status: PASS | PARTIAL | BLOCKED
Commit: <sha>
Files changed:
- ...

Tests/commands:
- `<command>` -> PASS/FAIL

Manual verification:
- ...

Notes:
- ...
```

## No-fake-completion rule

A page loading is not proof that a capability works.

For stateful features verify:
- loading,
- data,
- empty,
- request failure,
- action success,
- action failure,
- stale-state behavior,
- mobile where relevant.

For mutations verify both the visible UI result and backend persistence/response.

## Standard focused commands

Frontend:
```bash
cd frontend
npm run lint
npm test -- --run
npm run build
npm run design:guardrails
```

Backend:
```bash
uv run ruff check backend
uv run pytest <focused tests>
```

Do not run the entire slow suite after every tiny change. Use focused tests per microstep and full gates at checkpoints/final gate.


---

# Dentix Super Admin — Triple Check Findings

Audited baseline: `46584940df522e681e52fac1ec4bc3b7b206793b`

This report reconciles the original Super Admin plan with a third code-level pass across frontend surfaces, API client behavior, backend routes, schemas, and services.

## Newly confirmed high-impact defects

### 1. Impersonation is broken end-to-end
- Backend requires `reason` with at least 5 characters.
- Frontend calls the endpoint without `reason`.
- Backend returns a temporary Bearer access token.
- Frontend ignores the returned token and stores the literal string `impersonating`.
- Main authentication uses httpOnly cookies.
- API client does not currently attach the impersonation Bearer token.
- Return-to-admin flow removes the marker but does not restore/switch an auth credential.

### 2. Audit pagination contract mismatch
- Frontend state/request uses `page`.
- Backend accepts `skip` and `limit`.
- Unknown `page` query parameter is ignored.
- UI can show page 2 while still receiving page 1 data.

### 3. Audit CSV export ignores date filters
- Frontend sends start/end dates for export.
- Backend export endpoint does not accept/use them.
- Exported CSV can disagree with the visible filtered table.

### 4. Audit tenant label mismatch
- Frontend expects `tenant_name`.
- Backend audit result currently returns `tenant_id`, not `tenant_name`.
- UI falls back to `System Global`, which can mislabel tenant-scoped events.
- Existing `tenants` data is already passed to AuditLogViewer and can be used for display mapping.

### 5. Feature-flag tenant override is disconnected
- `SystemPage` fetches tenants.
- `FeatureManager` accepts `tenants`.
- `SystemPage` renders `<FeatureManager />`.

### 6. Feature override semantics are ambiguous
Current selector automatically applies the inverse of the global state instead of making the existing boolean override explicit.

### 7. Feature update API is present
The current “API Update Missing” frontend message is stale. `PUT /admin/features/{key}` exists.

### 8. Feature rollout validation is weak
Frontend create default and backend default differ, and 0–100 validation is not explicit.

### 9. Support Inbox local mark-read update is broken
Parent passes `setMessages`; child receives `_setMessages`.

### 10. Notification target invariant is missing
UI and backend both permit `is_global=false` with no tenant.

### 11. Finance Reports empty-overdue branch can crash
`ShieldCheck` is rendered but is not imported.

### 12. Tenant detail contains a dead ExternalLink button
Visible control has no handler.

### 13. Payments table is not horizontally protected
Unlike several other admin tables, it lacks an overflow wrapper.

### 14. Dashboard activity routing has broken/dead paths
- System errors link to `/admin/system`.
- Tenant deep link `?id=` is not consumed.
- Some view-all controls are dead.

### 15. Health false-success states remain
Hardcoded health success and default score 100 can mask failures.

### 16. Security assurance is hardcoded
Security panel can display fixed “High” assurance independent of data.

### 17. Dynamic Tailwind status classes are unsafe
HealthAlerts constructs color classes dynamically.

### 18. AI active-model metric is hardcoded
Value `3` is not derived from the current response.

### 19. AI dead controls exist
Top users and recent logs include view-all actions without working destinations.

### 20. AI period semantics are inconsistent
Selected period affects some values while usage trends stay fixed to 30 days.

### 21. AI zero requests are represented as 100% success
No activity must not be presented as successful activity.

### 22. AI tool filter backend contract is defective
The canonical mapped SQL field is `tool`; `response_tool` is only a Python compatibility property and must not be used as a SQL filter expression.

## Confirmed working / do not rebuild

- Public Global Settings maps `global_announcement` to `banner`.
- Support phone/email/WhatsApp/working-hours keys map through the public global-settings endpoint.
- Security stats endpoint exists.
- Security chart endpoint exists.
- Feature create/update/override endpoints exist.
- Super Admin global search endpoint exists.
- AuditLogViewer is already rendered inside the Security tab.
- API client unwraps standard success/data response envelopes.
- Bearer authentication is supported and takes precedence over the httpOnly access-token cookie.
- Backend already enforces read-only impersonation scope for non-safe HTTP methods.

## Do-not-surface findings

These may exist in backend/API code but must not automatically become new UI:
- purge-deleted-patients,
- checkout/webhook subscription APIs,
- compatibility duplicate admin routes,
- unrelated clinic backup controls.


---

# Dentix Super Admin — Microstep Execution Index

Baseline audited commit: `46584940df522e681e52fac1ec4bc3b7b206793b`
Implementation branch: `chore/super-admin-existing-capabilities-hardening`

Read `00_EXECUTOR_PROTOCOL.md` first. Execute MS-00 → MS-38 in order.

| Step | Title | Dependency |
|---|---|---|
| MS-00 | Baseline, branch, and execution ledger | None |
| MS-01 | Overview truth-state repair | None |
| MS-02 | Activity routing and tenant deep links | MS-01 |
| MS-03 | Impersonation request contract | MS-02 |
| MS-04 | Impersonation authentication and return | MS-03 |
| MS-05 | Feature flag tenant wiring | None |
| MS-06 | Feature rollout validation | MS-05 |
| MS-07 | Audit pagination contract | None |
| MS-08 | Audit filter/export/tenant labels | MS-07 |
| MS-09 | Finance runtime and mobile safety | None |
| MS-10 | Subscription status semantics | None |
| MS-11 | Dashboard 12-month analytics | MS-10 |
| MS-12 | Finance forecast semantics | MS-10 |
| MS-13 | Manual payment flow | None |
| MS-14 | Plan management | None |
| MS-15 | Support inbox | None |
| MS-16 | Targeted notification invariant | None |
| MS-17 | Settings and global announcement | None |
| MS-18 | Profile update alignment | None |
| MS-19 | 2FA hardening | None |
| MS-20 | Backup status truthfulness | None |
| MS-21 | Security partial failures and IP validation | None |
| MS-22 | Shared health query | MS-01 |
| MS-23 | Background jobs | MS-22 |
| MS-24 | Sessions | None |
| MS-25 | System logs | None |
| MS-26 | AI backend accuracy | None |
| MS-27 | AI frontend truthfulness | MS-26 |
| MS-28 | Super Admin shell | None |
| MS-29 | Overview information architecture | MS-01, MS-11, MS-22, MS-23 |
| MS-30 | Tenant and user UI consistency | MS-02, MS-03, MS-04 |
| MS-31 | Shared admin feedback primitives | None |
| MS-32 | Formatting and i18n | None |
| MS-33 | Mobile, dark, accessibility, motion | None |
| MS-34 | Request efficiency | Functional steps complete |
| MS-35 | Frontend regression suite | None |
| MS-36 | Backend regression suite | None |
| MS-37 | Super Admin E2E critical paths | MS-35, MS-36 |
| MS-38 | Final release gate | All previous microsteps |

---

# DENTIX SUPER ADMIN — AGENT START PROMPT

You are the implementation agent. Execute the entire pack; you are not the reviewer.

Repository: `Dentix-hub/dentix`
Target branch: `chore/super-admin-existing-capabilities-hardening`

Read:
1. `00_EXECUTOR_PROTOCOL.md`
2. `01_TRIPLE_CHECK_REPORT.md`
3. `02_MASTER_MICROSTEP_INDEX.md`
4. all `microsteps/MS-*.md` in numeric order.

Rules:
- Execute MS-00 through MS-38.
- One step at a time; one commit per step.
- Never merge to main.
- No new product features.
- A green build is not proof that a runtime branch works.
- If already fixed, prove it and ledger it as ALREADY SATISFIED; do not make meaningless edits.
- If blocked, record exact evidence and continue with independent steps.
- Keep the execution ledger current.
- Finish with MS-38.

Final response must include branch, commit range, MS-00..MS-38 status table, exact failed/skipped tests, changed-file summary, and confirmation main was not merged.


---

# MS-00 — Baseline, branch, and execution ledger

## Objective
Establish a reproducible baseline before any repair.

## Dependencies
None

## Files to inspect/change
- `frontend/package.json`
- `pyproject.toml`
- `.github/workflows/*`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

## Tasks
1. Confirm current main HEAD and record whether it descends from the audited baseline.
2. Create the target branch from current main.
3. Run frontend lint, tests, design guardrails, and production build.
4. Run backend Ruff and relevant existing tests.
5. Record pre-existing failures exactly; do not fix unrelated failures.
6. Create the execution ledger.

## Required verification
- Clean git status before edits.
- All baseline command results recorded.

## Definition of done
- [ ] Baseline commit/environment/pre-existing failures documented.
- [ ] No product code changed.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-00): baseline, branch, and execution ledger"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-01 — Overview truth-state repair

## Objective
Eliminate false healthy/success states from the Super Admin landing page.

## Dependencies
None

## Files to inspect/change
- `frontend/src/pages/admin/Overview.jsx`
- `frontend/src/features/admin/SuperAdmin/SystemHealth.jsx`
- `frontend/src/features/admin/SuperAdmin/DashboardStats.jsx`
- `frontend/src/shared/ui/StatCard.jsx`

## Tasks
1. Remove hardcoded healthy status from Overview.
2. Represent health as loading/known/error/unknown, never default score 100.
3. Make failed stats/health requests visibly different from empty/success.
4. Fix expired KPI color mismatch if `rose` is unsupported by StatCard.
5. Preserve the existing four KPIs.

## Required verification
- Health success/warning/critical/error component tests.
- Admin-stats failure test.

## Definition of done
- [ ] No request failure can look healthy or 100%.
- [ ] Overview remains usable when one dataset fails.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-01): overview truth-state repair"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-02 — Activity routing and tenant deep links

## Objective
Make visible activity navigation truthful and SPA-safe.

## Dependencies
MS-01

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/ActivityFeed.jsx`
- `frontend/src/pages/admin/TenantsPage.jsx`
- `backend/routers/admin_stats.py`

## Tasks
1. Route system errors to `/admin/system/logs`.
2. Use React Router for in-app links.
3. Only show click/chevron for valid links.
4. Consume `?id=<tenantId>` and open existing TenantDetailPanel.
5. Remove dead View All unless an existing route is valid.
6. Clean query state when tenant details close.

## Required verification
- Tenant activity deep-link test.
- Error activity route test.
- No-link activity noninteractive test.

## Definition of done
- [ ] Every visible activity affordance has a valid existing destination.
- [ ] No ordinary admin full-page reload.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-02): activity routing and tenant deep links"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-03 — Impersonation request contract

## Objective
Repair reason/scope/token acquisition for the existing impersonation feature.

## Dependencies
MS-02

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/TenantDetailPanel.jsx`
- `frontend/src/pages/admin/TenantsPage.jsx`
- `backend/routers/admin_tenants.py`

## Tasks
1. Add required impersonation reason input (minimum 5 chars) to the existing action.
2. Keep scope read_only; communicate it without adding a new workflow.
3. Send reason/user_id/scope with Axios params.
4. Use returned real access_token; never store literal marker text.
5. Surface backend 400/404 detail.
6. Remove dead ExternalLink unless a proven configured destination already exists.

## Required verification
- Short reason blocks request.
- Valid reason sends expected params.
- Backend missing reason 400; valid reason token test.

## Definition of done
- [ ] Valid request obtains real temporary token.
- [ ] No dead ExternalLink remains.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-03): impersonation request contract"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-04 — Impersonation authentication and return

## Objective
Make temporary Bearer auth work while preserving original Super Admin cookie session.

## Dependencies
MS-03

## Files to inspect/change
- `frontend/src/api/apiClient.js`
- `frontend/src/utils.js`
- `frontend/src/components/common/ImpersonationBar.jsx`
- `frontend/src/pages/admin/TenantsPage.jsx`

## Tasks
1. Use a dedicated sessionStorage impersonation-token helper/key.
2. Attach Authorization Bearer while impersonation token exists.
3. Do not overwrite original httpOnly Super Admin cookie.
4. Return removes impersonation token and clears tenant/query cache before returning to admin.
5. Logout/session-mismatch cleanup removes impersonation token.
6. Bar renders only for real impersonation state.
7. Do not weaken backend read-only enforcement.

## Required verification
- Bearer present during impersonation and absent after return.
- E2E: enter read-only, GET works, mutation rejected, return restores Super Admin.

## Definition of done
- [ ] Impersonation works across navigation/reload for the browser session.
- [ ] Return restores Super Admin context.
- [ ] Read-only remains enforced.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-04): impersonation authentication and return"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-05 — Feature flag tenant wiring

## Objective
Make existing global and tenant override controls usable.

## Dependencies
None

## Files to inspect/change
- `frontend/src/pages/admin/SystemPage.jsx`
- `frontend/src/features/admin/SuperAdmin/FeatureManager.jsx`

## Tasks
1. Pass fetched tenants into FeatureManager.
2. Remove stale API Update Missing message.
3. Make tenant override explicit Enable/Disable using existing boolean API.
4. Keep create/global-toggle behavior.
5. Disable mutation controls while pending.

## Required verification
- Tenant options render.
- Global toggle.
- Tenant enable override.
- Tenant disable override.
- API failure.

## Definition of done
- [ ] Tenant override is populated and explicit.
- [ ] No stale API-missing message.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-05): feature flag tenant wiring"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-06 — Feature rollout validation

## Objective
Normalize the existing rollout percentage contract.

## Dependencies
MS-05

## Files to inspect/change
- `backend/schemas/system.py`
- `backend/routers/admin_features.py`
- `backend/services/feature_service.py`
- `frontend/src/features/admin/SuperAdmin/FeatureManager.jsx`

## Tasks
1. Enforce rollout range 0..100.
2. Use a safe existing-field update schema instead of arbitrary dict if needed.
3. Align frontend/backend create default after inspecting current seeded intent.
4. Permit editing the already existing rollout field only.
5. Prevent arbitrary setattr updates.

## Required verification
- -1/101 rejected; 0/50/100 accepted.
- Frontend valid rollout update.

## Definition of done
- [ ] One validated rollout contract.
- [ ] Update cannot write arbitrary attributes.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-06): feature rollout validation"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-07 — Audit pagination contract

## Objective
Fix page navigation to use backend skip/limit correctly.

## Dependencies
None

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/AuditLogViewer.jsx`
- `backend/routers/system_admin.py`
- `backend/services/security_service.py`

## Tasks
1. Compute skip=(page-1)*limit in frontend.
2. Stop sending ignored page param.
3. Keep backend current_page/pages.
4. Reset page on filters.
5. Bound page-number UI if page count is large.

## Required verification
- Page1 skip0.
- Page2 skip=limit.
- Filter reset skip0.

## Definition of done
- [ ] Page navigation changes rows and matches backend current page.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-07): audit pagination contract"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-08 — Audit filter/export/tenant labels

## Objective
Make visible audit table and CSV represent the same state.

## Dependencies
MS-07

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/AuditLogViewer.jsx`
- `backend/routers/system_admin.py`

## Tasks
1. Accept/pass start_date and end_date in existing export endpoint.
2. Apply same visible filters to CSV.
3. Map tenant_id to names using existing tenants prop.
4. Show request failure separately from no results.
5. Revoke export object URL.
6. Use shared modal primitives where practical.

## Required verification
- Date-filter export test.
- Tenant-name mapping test.
- Fetch-failure test.
- Export smoke.

## Definition of done
- [ ] CSV matches visible filters.
- [ ] Tenant events are not mislabeled System Global.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-08): audit filter/export/tenant labels"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-09 — Finance runtime and mobile safety

## Objective
Remove branch-only runtime failures and overflow.

## Dependencies
None

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/FinanceReports.jsx`
- `frontend/src/features/admin/SuperAdmin/PaymentsManager.jsx`
- `frontend/src/features/admin/SuperAdmin/ActiveSubscriptions.jsx`

## Tasks
1. Fix missing ShieldCheck import/use.
2. Add Payments table overflow wrapper.
3. Null-safe amount/date/name rendering.
4. i18n ActiveSubscriptions labels/status.
5. Locale-aware dates/currency.
6. Explicitly test zero overdue clinics.

## Required verification
- Zero-overdue render.
- 320/360px payments no document overflow.
- Arabic/English subscriptions.

## Definition of done
- [ ] No FinanceReports branch ReferenceError.
- [ ] Finance tables usable on small screens.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-09): finance runtime and mobile safety"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-10 — Subscription status semantics

## Objective
Use one existing-state definition for active/expired/archived.

## Dependencies
None

## Files to inspect/change
- `backend/routers/admin_stats.py`
- `frontend/src/features/admin/SuperAdmin/TenantsManager.jsx`
- `frontend/src/features/admin/SuperAdmin/ActiveSubscriptions.jsx`
- `frontend/src/features/admin/SuperAdmin/DashboardStats.jsx`

## Tasks
1. Define operational active consistently with existing expiry/grace policy.
2. Exclude archived/deleted from operational counts.
3. Align tenant table, subscriptions and dashboard KPIs.
4. Do not add new status enum.
5. Document chosen definition in tests/comments.

## Required verification
- Backend active/expired/disabled/archived cases.
- Frontend status cases.

## Definition of done
- [ ] Same tenant state has consistent label/count across Super Admin.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-10): subscription status semantics"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-11 — Dashboard 12-month analytics

## Objective
Make existing dashboard charts match stated time window.

## Dependencies
MS-10

## Files to inspect/change
- `backend/routers/admin_stats.py`
- `frontend/src/features/admin/SuperAdmin/AdminCharts.jsx`

## Tasks
1. Restrict revenue/growth to intended last 12 months.
2. Handle missing months consistently.
3. Localize month labels.
4. Format revenue axes/tooltips.
5. Remove redundant donut legend/custom duplicate.
6. Fix mobile fixed-height plan distribution.
7. Fix dark grid/tooltip.

## Required verification
- Backend >12-month exclusion.
- Arabic/English chart smoke.
- Dark/mobile smoke.

## Definition of done
- [ ] Chart window and labels agree.
- [ ] No duplicate plan representation.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-11): dashboard 12-month analytics"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-12 — Finance forecast semantics

## Objective
Make existing reports use normalized subscription status and safe null handling.

## Dependencies
MS-10

## Files to inspect/change
- `backend/routers/admin_stats.py`
- `frontend/src/features/admin/SuperAdmin/FinanceReports.jsx`

## Tasks
1. Exclude non-active/expired/archived tenants from forecast per normalized semantics.
2. Align overdue list semantics.
3. Null-safe churn last_active.
4. Keep forecast labelled estimate.
5. Keep existing report sections only.

## Required verification
- Forecast active vs expired test.
- Null last_active frontend test.
- Empty reports.

## Definition of done
- [ ] Forecast reflects current active subscriptions only.
- [ ] No null-date crash.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-12): finance forecast semantics"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-13 — Manual payment flow

## Objective
Harden current subscription-payment recording.

## Dependencies
None

## Files to inspect/change
- `frontend/src/pages/admin/FinancePage.jsx`
- `frontend/src/features/admin/SuperAdmin/PaymentsManager.jsx`

## Tasks
1. Use shared Modal if compatible.
2. Validate tenant/plan/finite amount/date.
3. Disable duplicate submission.
4. Clear payer when tenant changes.
5. Show backend validation detail.
6. Use ConfirmDialog for delete.
7. Refresh only required data where safe.

## Required verification
- Invalid form.
- Double-click prevention.
- Success/failure payment.
- Delete confirm.

## Definition of done
- [ ] No duplicate payment request.
- [ ] Failures preserve useful form state.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-13): manual payment flow"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-14 — Plan management

## Objective
Stabilize current create/edit/delete/default/AI plan settings.

## Dependencies
None

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/PlansManager.jsx`
- `frontend/src/pages/admin/FinancePage.jsx`
- `backend/routers/admin_subscriptions.py`

## Tasks
1. Replace browser alert/confirm.
2. Prevent NaN numeric payloads.
3. Validate price/duration/limits.
4. Use existing deleteSubscriptionPlan import.
5. Preserve default and AI fields.
6. Surface backend constraints.

## Required verification
- Create/edit/default/AI-limit/delete allowed/delete failure tests.

## Definition of done
- [ ] All current plan actions have valid payloads and explicit feedback.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-14): plan management"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-15 — Support inbox

## Objective
Repair view/read/delete state synchronization.

## Dependencies
None

## Files to inspect/change
- `frontend/src/pages/admin/CommunicationsPage.jsx`
- `frontend/src/features/admin/SuperAdmin/SupportInbox.jsx`

## Tasks
1. Rename _setMessages to setMessages consistently.
2. Update read state correctly after API success.
3. Use shared Modal instead of alert.
4. Use ConfirmDialog for delete.
5. Add mutation pending state.
6. Keep existing stats cards.

## Required verification
- Unread->read.
- Already read.
- Read failure.
- Delete.

## Definition of done
- [ ] Unread count updates immediately and correctly.
- [ ] No browser alert for message view.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-15): support inbox"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-16 — Targeted notification invariant

## Objective
Guarantee current targeted notifications always have a real tenant.

## Dependencies
None

## Files to inspect/change
- `frontend/src/pages/admin/CommunicationsPage.jsx`
- `frontend/src/features/admin/SuperAdmin/NotificationsManager.jsx`
- `backend/schemas/system.py`
- `backend/routers/notifications.py`

## Tasks
1. Frontend requires tenant when non-global.
2. Normalize tenant_id when switching global.
3. Disable duplicate send.
4. Backend requires tenant_id for non-global.
5. Backend checks tenant exists.
6. ConfirmDialog for delete.
7. No new target modes.

## Required verification
- Global valid.
- Targeted valid.
- Missing tenant rejected.
- Nonexistent tenant rejected.
- Duplicate send prevented.

## Definition of done
- [ ] No ownerless targeted notification can be created.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-16): targeted notification invariant"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-17 — Settings and global announcement

## Objective
Make existing settings truthful with existing public consumers.

## Dependencies
None

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/SettingsManager.jsx`
- `frontend/src/shared/ui/GlobalBanner.jsx`
- `frontend/src/pages/Support.jsx`
- `backend/main.py`

## Tasks
1. Remove stale coming-soon announcement text.
2. Use toast instead of alert.
3. ConfirmDialog for maintenance.
4. Preserve/rollback local state on save failure.
5. Verify global_announcement save -> public banner -> GlobalBanner.
6. Keep confirmed support-key mapping.
7. Replace obsolete Smart Dental fallback contact/domain with current neutral/Dentix config fallback.
8. Remove static Available now claim if not actually calculated; do not add scheduling logic.

## Required verification
- Announcement mapping integration.
- Save failure.
- Support public-settings fallback.

## Definition of done
- [ ] No stale coming-soon claim.
- [ ] Saved announcement appears through existing flow.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-17): settings and global announcement"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-18 — Profile update alignment

## Objective
Respect existing backend password policy and identity state.

## Dependencies
None

## Files to inspect/change
- `frontend/src/pages/admin/SystemPage.jsx`
- `backend/routers/system_admin.py`

## Tasks
1. Use shared confirmation.
2. Show backend password validation details.
3. Do not send empty fields unnecessarily.
4. Disable all-empty submit.
5. Refresh identity state if current auth store supports it.
6. Clear password after completion.

## Required verification
- Empty form.
- Weak password error visible.
- Successful username/email update.

## Definition of done
- [ ] No generic success after validation failure.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-18): profile update alignment"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-19 — 2FA hardening

## Objective
Stabilize existing setup/verify/disable.

## Dependencies
None

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/TwoFactorSetup.jsx`

## Tasks
1. Shared confirmation for disable.
2. Clear secret/code on cancel.
3. Guard missing setupData.
4. Handle clipboard failure.
5. i18n current strings.
6. Prevent duplicate submissions.

## Required verification
- Setup success/failure.
- Invalid code.
- Cancel clears secret.
- Disable.
- Clipboard failure.

## Definition of done
- [ ] No stale secret after cancel/success.
- [ ] Flow deterministic.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-19): 2fa hardening"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-20 — Backup status truthfulness

## Objective
Distinguish connected/started/completed/failed for existing Google backup.

## Dependencies
None

## Files to inspect/change
- `frontend/src/pages/admin/SystemPage.jsx`
- `backend/routers/admin_system.py`

## Tasks
1. Consume existing last_backup fields.
2. 202/processing means started, not completed.
3. Prevent duplicate trigger.
4. Display last result/date.
5. Clean OAuth query params for success/error.
6. Do not re-enable raw HTTP restore/export.

## Required verification
- Connected/unconnected.
- Processing trigger.
- Last success/failure.
- OAuth cleanup.

## Definition of done
- [ ] UI never claims completion based only on accepted background task.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-20): backup status truthfulness"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-21 — Security partial failures and IP validation

## Objective
Keep security controls usable if one dataset fails.

## Dependencies
None

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/SecurityPanel.jsx`
- `backend/routers/admin_system.py`
- `backend/routers/system_admin.py`
- `backend/services/security_service.py`

## Tasks
1. Fetch stats/chart/IP list independently.
2. Remove/derive fixed High assurance.
3. Validate IP server-side with standard parser.
4. Shared toast/dialog for block/unblock.
5. Fix dark chart tooltip/grid.
6. Keep existing security features only.

## Required verification
- Partial failures.
- Valid IPv4/IPv6.
- Invalid IP.
- Unblock failure.
- Dark chart.

## Definition of done
- [ ] One API failure does not blank/misrepresent other security data.
- [ ] No hardcoded assurance.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-21): security partial failures and ip validation"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-22 — Shared health query

## Objective
Unify health semantics while preserving Overview and Security presentations.

## Dependencies
MS-01

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/SystemHealth.jsx`
- `frontend/src/features/admin/SuperAdmin/HealthAlerts.jsx`
- `frontend/src/lib/queryClient.js or a narrowly scoped health hook`

## Tasks
1. One React Query key for health endpoint.
2. Both presentations use same cached result.
3. Static class map for health colors; no dynamic Tailwind strings.
4. 30-60s polling unless 10s requirement is proven.
5. Pause/reduce hidden-tab polling.
6. Manual checks invalidate health query.

## Required verification
- All health statuses.
- Shared query reuse.
- Failure->unknown.
- Manual invalidation.

## Definition of done
- [ ] No contradictory health states.
- [ ] No dynamic Tailwind status strings.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-22): shared health query"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-23 — Background jobs

## Objective
Make existing jobs telemetry responsive and null-safe.

## Dependencies
MS-22

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/SystemHealth.jsx`
- `backend/routers/admin_security.py`

## Tasks
1. Overflow wrapper.
2. Null-safe duration/name/triggered_by.
3. Localized statuses.
4. Error distinct from no jobs.
5. Zero jobs != 100% success.
6. Refresh after manual checks.
7. One primary/one secondary check action visually.

## Required verification
- Zero jobs.
- Fetch failure.
- Null duration.
- Mobile table.
- Manual refresh.

## Definition of done
- [ ] No crash or fake success from missing jobs.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-23): background jobs"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-24 — Sessions

## Objective
Harden current global session search/terminate.

## Dependencies
None

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/SessionManager.jsx`
- `backend/routers/admin_system.py`
- `backend/services/security_service.py`

## Tasks
1. Null-safe search.
2. ConfirmDialog terminate.
3. Disable duplicate terminate.
4. Locale labels/timestamps.
5. Visible background refresh.
6. Verify current-session termination behavior without inventing policy.

## Required verification
- Null fields.
- Search.
- Terminate success/failure.
- Refresh state.

## Definition of done
- [ ] No null crash or duplicate terminate.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-24): sessions"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-25 — System logs

## Objective
Polish existing log list/detail/delete/clear/export/pagination.

## Dependencies
None

## Files to inspect/change
- `frontend/src/pages/admin/SystemLogs.jsx`

## Tasks
1. Explicit fetch error.
2. Clipboard failure.
3. Revoke export URL.
4. Correct page after final-row delete.
5. Responsive header actions.
6. Locale timestamp.
7. Preserve all existing actions.

## Required verification
- Empty/error.
- Delete final row.
- Clear.
- Clipboard.
- Export cleanup.

## Definition of done
- [ ] Empty and error distinct.
- [ ] Pagination valid after mutation.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-25): system logs"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-26 — AI backend accuracy

## Objective
Correct existing AI analytics semantics.

## Dependencies
None

## Files to inspect/change
- `backend/ai/analytics/service.py`
- `backend/routers/ai_admin.py`
- `backend/models/ai_audit.py`

## Tasks
1. Zero requests -> no-data/null success rate, not 100.
2. Trends obey today/week/month.
3. Tool filter uses mapped SQL `tool` column.
4. Validate existing period set.
5. Prefer recorded cost sum if authoritative; otherwise retain clearly estimated semantics.
6. Do not add active-model metric.

## Required verification
- Zero requests.
- Today/week/month bounds.
- Tool filter.
- Invalid period.
- Cost semantics.

## Definition of done
- [ ] AI API is truthful and documented filters work.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-26): ai backend accuracy"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-27 — AI frontend truthfulness

## Objective
Display only real AI metrics/actions.

## Dependencies
MS-26

## Files to inspect/change
- `frontend/src/features/admin/SuperAdmin/AIAdminDashboard.jsx`
- `frontend/src/pages/admin/AIStatsPage.jsx`

## Tasks
1. Remove hardcoded Active Models card unless real existing response field exists.
2. Remove dead View All buttons unless existing routes support them.
3. No-activity success shows dash/no activity.
4. Use corrected period semantics.
5. Dark-mode chart fixes.
6. Reduce nonfunctional hover motion.
7. Keep existing analytics sections.

## Required verification
- Period renders.
- Zero usage.
- No dead buttons.
- Dark/mobile.

## Definition of done
- [ ] No hardcoded/dead AI metric or action.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-27): ai frontend truthfulness"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-28 — Super Admin shell

## Objective
Use platform-admin context instead of clinic/patient context.

## Dependencies
None

## Files to inspect/change
- `frontend/src/layouts/Layout.jsx`
- `frontend/src/shared/ui/GlobalSearch.jsx`
- `frontend/src/features/admin/SuperAdmin/SuperAdminCommandPalette.jsx`
- `frontend/src/locales/ar/translation.json`
- `frontend/src/locales/en/translation.json`

## Tasks
1. Do not render patient GlobalSearch as Super Admin primary search.
2. Reuse existing SuperAdminCommandPalette; preserve Ctrl/Cmd+K.
3. Fix duplicate/misleading sidebar labels.
4. Unique labels for current routes.
5. i18n command palette hardcoded Arabic/RTL.
6. Wire existing status query only if current filter exists; otherwise simplify suggestion route.

## Required verification
- Super Admin header.
- Clinic role patient search unchanged.
- Arabic/English sidebar.
- Keyboard palette.

## Definition of done
- [ ] Super Admin shell no longer behaves like clinic workspace.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-28): super admin shell"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-29 — Overview information architecture

## Objective
Reorder only existing content and calm the visual hierarchy.

## Dependencies
MS-01, MS-11, MS-22, MS-23

## Files to inspect/change
- `frontend/src/pages/admin/Overview.jsx`
- `frontend/src/features/admin/SuperAdmin/AdminCharts.jsx`
- `frontend/src/features/admin/SuperAdmin/ActivityFeed.jsx`
- `frontend/src/shared/ui/StatCard.jsx`

## Tasks
1. Order compact title/real health -> 4 KPIs -> health/activity -> analytics -> plan distribution -> jobs.
2. Remove AI coming-soon teaser.
3. Balance desktop columns.
4. Remove lift/rotate from static KPIs.
5. Prefer current semantic tokens/radii/shadows.
6. No new widget.

## Required verification
- Desktop/mobile visual smoke.
- Static KPI no false click affordance.

## Definition of done
- [ ] Dashboard contains only existing useful data and no new widget.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-29): overview information architecture"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-30 — Tenant and user UI consistency

## Objective
Normalize remaining existing tenant/user actions.

## Dependencies
MS-02, MS-03, MS-04

## Files to inspect/change
- `frontend/src/pages/admin/TenantsPage.jsx`
- `frontend/src/features/admin/SuperAdmin/TenantsManager.jsx`
- `frontend/src/features/admin/SuperAdmin/TenantDetailPanel.jsx`
- `frontend/src/pages/admin/UsersPage.jsx`
- `frontend/src/features/admin/SuperAdmin/UsersManager.jsx`

## Tasks
1. Use archive wording for reversible delete.
2. Keep permanent delete strongly destructive.
3. Hide idempotency key while still generating/sending internally.
4. Shared confirmations/modals.
5. Remove hardcoded `.dentix.com` display unless actual configured domain.
6. Axios params for user search.
7. Localize roles/fallbacks.
8. Clarify search loading.
9. Do not add purge-deleted-patients UI.

## Required verification
- Archive/restore/delete.
- Renewal idempotency payload.
- User search/i18n.
- Mobile actions.

## Definition of done
- [ ] All existing actions remain available and safer.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-30): tenant and user ui consistency"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-31 — Shared admin feedback primitives

## Objective
Remove browser-native alerts/confirms from in-scope Super Admin.

## Dependencies
None

## Files to inspect/change
- `frontend/src/pages/admin/*`
- `frontend/src/features/admin/SuperAdmin/*`
- `frontend/src/shared/ui/*`

## Tasks
1. Limit changes to in-scope Super Admin.
2. Replace remaining alert/window.confirm with toast/Modal/ConfirmDialog.
3. Danger style only for destructive actions.
4. Shared dialogs handle focus/escape.
5. Do not rewrite unrelated clinic UI.

## Required verification
- Search in-scope files for remaining browser-native calls.
- Focused dialog tests.

## Definition of done
- [ ] Admin feedback is consistent/testable.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-31): shared admin feedback primitives"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-32 — Formatting and i18n

## Objective
Remove mixed-language and browser-locale inconsistencies.

## Dependencies
None

## Files to inspect/change
- `frontend/src/locales/ar/translation.json`
- `frontend/src/locales/en/translation.json`
- `frontend/src/utils/*`
- `in-scope Super Admin components`

## Tasks
1. Create/reuse formatters for EGP/integer/percent/month/date/time/duration.
2. Translate remaining user-facing hardcoded strings.
3. Translate role/status at presentation boundary.
4. Keep technical values raw.

## Required verification
- Representative Arabic/English tests.
- No missing translation keys in exercised paths.

## Definition of done
- [ ] Super Admin usable end-to-end in Arabic or English.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-32): formatting and i18n"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-33 — Mobile, dark, accessibility, motion

## Objective
Verify existing workflows across viewports/themes/input modes.

## Dependencies
None

## Files to inspect/change
- `All in-scope Super Admin frontend files`
- `frontend/e2e/mobile-responsive.spec.ts`
- `frontend/e2e/ui-regression.spec.ts`

## Tasks
1. Test 320/360/390/430/768/1024/1280+.
2. Arabic+English.
3. Light+dark.
4. Fix document horizontal overflow.
5. Practical touch targets.
6. Accessible icon labels.
7. Focus-visible/dialog keyboard behavior.
8. Respect reduced motion.

## Required verification
- Responsive Playwright.
- Dark smoke.
- Keyboard smoke.

## Definition of done
- [ ] No critical workflow desktop-only/light-only.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-33): mobile, dark, accessibility, motion"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-34 — Request efficiency

## Objective
Reduce duplicated requests after correctness is stable.

## Dependencies
Functional steps complete

## Files to inspect/change
- `frontend/src/lib/queryClient.js`
- `in-scope Super Admin data components`

## Tasks
1. No wholesale rewrite.
2. Use React Query where it removes duplication/stale state.
3. Priority health/overview/security/sessions/comms/platform-finance.
4. Targeted invalidation.
5. Lazy-load reports tab.
6. Avoid refetching unrelated datasets after mutations.

## Required verification
- Request-count smoke.
- Invalidation tests.
- No stale-state regression.

## Definition of done
- [ ] Lower request load without weakening correctness.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-34): request efficiency"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-35 — Frontend regression suite

## Objective
Cover high-risk discovered Super Admin regressions.

## Dependencies
None

## Files to inspect/change
- `frontend/src/tests/* or colocated tests`
- `frontend/e2e/*`

## Tasks
1. Cover health/errors.
2. Tenant deep links/impersonation.
3. Flags/override.
4. Audit pagination/export UI.
5. Finance empty branches.
6. Support read/notification target.
7. Settings/backup/security/sessions/logs.
8. AI zero/period/dead controls.
9. Prefer behavior tests.

## Required verification
- Run focused new tests.
- Run full frontend tests, lint, build.

## Definition of done
- [ ] Known triple-check regressions have automated frontend coverage where feasible.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-35): frontend regression suite"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-36 — Backend regression suite

## Objective
Lock corrected backend contracts.

## Dependencies
None

## Files to inspect/change
- `backend/tests/*`

## Tasks
1. Status semantics.
2. 12-month stats.
3. Forecast.
4. Feature rollout/override.
5. Notification target invariant.
6. Audit pagination/filter/export.
7. IP validation.
8. AI zero/period/tool filter.
9. Impersonation reason/read-only.

## Required verification
- Focused tests.
- Full pytest if environment permits.
- Ruff.

## Definition of done
- [ ] Every corrected backend contract has regression coverage.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-36): backend regression suite"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-37 — Super Admin E2E critical paths

## Objective
Prove workflows, not isolated components.

## Dependencies
MS-35, MS-36

## Files to inspect/change
- `frontend/e2e/super-admin-existing-capabilities.spec.ts`
- `existing E2E helpers`

## Tasks
1. Smoke all Super Admin routes.
2. Assert no uncaught exception/dead spinner/required 404-500/document overflow.
3. Safe isolated mutations only.
4. Impersonation enter/read-only/return.
5. Audit page navigation.
6. Feature override and restore.
7. Notification target validation.
8. Never permanent-delete real data.

## Required verification
- Run E2E spec in configured test environment.

## Definition of done
- [ ] Critical existing workflows proven end-to-end.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-37): super admin e2e critical paths"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# MS-38 — Final release gate

## Objective
Produce reviewable branch evidence without merging.

## Dependencies
All previous microsteps

## Files to inspect/change
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`
- `all changed files`

## Tasks
1. Run lint.
2. Run design guardrails.
3. Run full frontend tests.
4. Run frontend build.
5. Run backend Ruff/tests.
6. Run Super Admin E2E.
7. Review diff for feature creep.
8. Search dead buttons/native alerts/broken `/admin/system`/hardcoded model metric.
9. Confirm no new product capability.
10. Push branch.
11. Write final PASS/PARTIAL/BLOCKED table and commit range.
12. Do not merge.

## Required verification
- All final commands with recorded output.

## Definition of done
- [ ] Branch is evidence-backed and reviewable.
- [ ] No completion claim with failing required gate.

## Commit
```bash
git add <only files for this step>
git commit -m "super-admin(ms-38): final release gate"
```

Append evidence to `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`.

## Stop condition
Do not mark PASS if required verification fails. Record PARTIAL/BLOCKED with evidence, then continue only with independent steps.


---

# Dentix Super Admin — Independent Reviewer Protocol

Use this after the implementation agent finishes `chore/super-admin-existing-capabilities-hardening`.

## Review
1. Compare baseline to final SHA.
2. Verify no feature creep.
3. Verify every Triple Check defect against actual code.
4. Cross-check every ledger PASS with code/tests.
5. Prioritize:
   - impersonation Bearer/cookie/return/read-only,
   - audit skip/limit and date-filter export,
   - tenant audit labels,
   - explicit feature override,
   - notification backend invariant,
   - health unknown/error,
   - active/expired semantics,
   - AI SQL tool filter,
   - no hardcoded model metric/dead controls.
6. Inspect tests for fake assertions.
7. Check final GitHub Actions/CI.
8. Check mobile/dark/i18n regressions.
9. Approve merge only when release gate is green.

Verdict per step: PASS / PARTIAL / FAIL / OUT-OF-SCOPE.
For every non-PASS item, cite exact file/function evidence.
