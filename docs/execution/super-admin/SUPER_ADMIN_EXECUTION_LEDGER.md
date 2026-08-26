# Super Admin Hardening — Execution Ledger

Branch: `chore/super-admin-existing-capabilities-hardening`
Baseline Audited Commit: `46584940df522e681e52fac1ec4bc3b7b206793b`

---

## MS-00 — Baseline, branch, and execution ledger
Status: PASS
Commit: f82a15a0
Files changed:
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` (frontend) -> PASS (0 errors, 0 warnings)
- `npm.cmd run design:guardrails` (frontend) -> PASS (73 legacy inventory items, 0 new violations)
- `npm.cmd test -- --run` (frontend) -> PASS (62 test files, 260 tests passed)
- `npm.cmd run build` (frontend) -> PASS (built successfully in 11.05s)
- `uv run ruff check --config ruff.toml backend` -> PASS (All checks passed)
- `$env:PYTHONPATH="." ; uv run pytest backend/tests/test_subscription_lockout_regression.py backend/tests/test_safe_config_modes.py backend/tests/test_logging_sanitizer.py` -> PASS (12 passed in 9.85s)

Manual verification:
- Confirmed current main HEAD is `46584940df522e681e52fac1ec4bc3b7b206793b` (exact audited baseline).
- Created target implementation branch `chore/super-admin-existing-capabilities-hardening`.
- Confirmed clean initial tree before any product code changes.

Notes:
- Baseline established. Ready for microstep execution MS-01 through MS-38.

---

## MS-01 — Overview truth-state repair
Status: PASS
Commit: 267f6606
Files changed:
- `frontend/src/shared/ui/StatCard.jsx`
- `frontend/src/shared/ui/StatCard.test.jsx`
- `frontend/src/features/admin/SuperAdmin/SystemHealth.jsx`
- `frontend/src/features/admin/SuperAdmin/SystemHealth.test.jsx`
- `frontend/src/pages/admin/Overview.jsx`
- `frontend/src/pages/admin/Overview.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/shared/ui/StatCard.test.jsx src/features/admin/SuperAdmin/SystemHealth.test.jsx src/pages/admin/Overview.test.jsx --run` -> PASS (3 test files, 10 tests passed)

Manual verification:
- Removed hardcoded "النظام يعمل بكفاءة عالية" claim from Overview header.
- Replaced initial/error default score 100 in SystemHealth with loading (`...`), error (`—`), and dynamic score.
- Made Overview resilient against admin-stats fetch failure with an explicit error alert and retry button while preserving SystemHealth visibility.
- Added `rose` color tokens to `StatCard.jsx` to prevent expired tenant KPI color mismatch.
- Preserved all 4 existing dashboard KPIs.

Notes:
- Overview and SystemHealth verified to never produce false 100% or healthy states on request failure or initial loading.

---

## MS-02 — Activity routing and tenant deep links
Status: PASS
Commit: 3a2560e6
Files changed:
- `backend/routers/admin_stats.py`
- `frontend/src/features/admin/SuperAdmin/ActivityFeed.jsx`
- `frontend/src/features/admin/SuperAdmin/ActivityFeed.test.jsx`
- `frontend/src/pages/admin/TenantsPage.jsx`
- `frontend/src/pages/admin/TenantsPage.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/ActivityFeed.test.jsx src/pages/admin/TenantsPage.test.jsx --run` -> PASS (2 test files, 5 tests passed)
- `uv run ruff check --config ruff.toml backend` -> PASS (All checks passed)

Manual verification:
- Routed system errors in activity feed from `/admin/system` (dead route) to `/admin/system/logs`.
- Switched ActivityFeed from `window.location.href` to React Router `useNavigate`.
- Only clickable items with real links show cursor pointer, chevron, and keyboard navigation affordance.
- Removed dead "View All" button with no destination.
- Consumed `?id=<tenantId>` search param in `TenantsPage` to automatically open `TenantDetailPanel`.
- Cleaned query parameters upon closing tenant detail panel.

Notes:
- Activity feed items now route cleanly via client-side routing, deep link directly opens tenant details, and no dead affordances remain.

---


## MS-03 — Impersonation request contract
Status: PASS
Commit: 78dfb72b
Files changed:
- `backend/routers/admin_tenants.py`
- `backend/tests/test_admin_impersonation.py`
- `frontend/src/features/admin/SuperAdmin/TenantDetailPanel.jsx`
- `frontend/src/features/admin/SuperAdmin/TenantDetailPanel.test.jsx`
- `frontend/src/pages/admin/TenantsPage.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/TenantDetailPanel.test.jsx src/pages/admin/TenantsPage.test.jsx --run` -> PASS (2 test files, 5 tests passed)
- `uv run ruff check --config ruff.toml backend` -> PASS (All checks passed)
- `$env:PYTHONPATH="." ; uv run pytest backend/tests/test_admin_impersonation.py` -> PASS (3 passed in 8.04s)

Manual verification:
- Added required impersonation reason input with minimum 5 characters requirement to `TenantDetailPanel`.
- Preserved read-only session scope indicator in the UI.
- Sent `reason`, `user_id`, and `scope` via query parameters to the backend endpoint.
- Updated `handleImpersonate` to store the real JWT temporary access token returned from backend instead of literal string marker.
- Surfaced backend error details (400/404) properly via toast messages.
- Removed dead ExternalLink button from `TenantDetailPanel`.

Notes:
- Super Admin impersonation request contract is fully repaired, validated, and tested.

---

## MS-04 — Impersonation authentication and return
Status: PASS
Commit: 53486ee5
Files changed:
- `frontend/src/api/apiClient.js`
- `frontend/src/components/common/ImpersonationBar.jsx`
- `frontend/src/components/common/ImpersonationBar.test.jsx`
- `frontend/src/utils.js`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/components/common/ImpersonationBar.test.jsx src/features/admin/SuperAdmin/TenantDetailPanel.test.jsx --run` -> PASS (2 test files, 6 tests passed)

Manual verification:
- Used dedicated sessionStorage impersonation-token helper/key (`dentix_impersonation_token`) in `frontend/src/utils.js`.
- Configured Axios request interceptor in `apiClient.js` to automatically attach `Authorization: Bearer <token>` when impersonating.
- Preserved original httpOnly Super Admin cookie session untouched.
- Return action safely removes impersonation token, metadata, clears React Query cache, resets tenant store, and navigates to `/admin/tenants`.
- Session mismatch and logout handlers properly clean up impersonation session keys.
- ImpersonationBar renders only when a real impersonation token is active, displaying clinic name and read-only scope status.

Notes:
- Super Admin impersonation session lifecycle (acquire -> simulate -> return) is completely functional and secure without affecting the admin session cookie.

---

## MS-05 — Feature flag wiring
Status: PASS
Commit: a852abe6
Files changed:
- `frontend/src/features/admin/SuperAdmin/FeatureManager.jsx`
- `frontend/src/features/admin/SuperAdmin/FeatureManager.test.jsx`
- `frontend/src/pages/admin/SystemPage.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/FeatureManager.test.jsx --run` -> PASS (1 test file, 3 tests passed)

Manual verification:
- Replaced missing/broken toggle handler in `FeatureManager.jsx` with real PUT `/api/v1/admin/features/:key` request.
- Added optimistic UI updates for instant toggle responsiveness.
- Added automatic rollback on network/server error.
- Replaced browser `alert` calls with shared UI `toast` notifications.
- Passed `tenants` prop from `SystemPage` to `FeatureManager`.

Notes:
- Feature flag toggle and override controls are fully wired to the backend API without no-op switches.

---

## MS-06 — Command palette wiring and safety
Status: PASS
Commit: 80f4acef
Files changed:
- `frontend/src/features/admin/SuperAdmin/SuperAdminCommandPalette.jsx`
- `frontend/src/features/admin/SuperAdmin/SuperAdminCommandPalette.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/SuperAdminCommandPalette.test.jsx --run` -> PASS (1 test file, 4 tests passed)

Manual verification:
- Routed action commands to real active Super Admin paths (`/admin`, `/admin/tenants`, `/admin/users`, `/admin/finance`, `/admin/messages`, `/ai/stats`, `/admin/system/logs`, `/admin/settings`).
- Integrated tenant search using `/api/v1/admin/tenants` with fuzzy/filter matching on name, domain, email, and phone.
- Enabled deep linking directly from search results to `/admin/tenants?id=:id`.
- Replaced 404-prone `/api/v1/admin/system/search` with robust client-side + tenant-endpoint search.
- Hardened keyboard controls and event listeners with cleanup on unmount.

Notes:
- Super Admin command palette now executes real navigation commands and deep links directly into tenant records without dead routes.

---

## MS-07 — Plan feature checklist synchronization
Status: PASS
Commit: 846f96ea
Files changed:
- `frontend/src/features/admin/SuperAdmin/PlansManager.jsx`
- `frontend/src/features/admin/SuperAdmin/PlansManager.test.jsx`
- `frontend/src/features/admin/SuperAdmin/planFeatureUtils.js`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/PlansManager.test.jsx --run` -> PASS (1 test file, 4 tests passed)
- `$env:PYTHONPATH="c:\Users\es\DENTIX"; uv run pytest backend/tests/ -k "subscription or plan"` -> PASS (44 passed)

Manual verification:
- Synchronized recognized feature checklist (`ai_insights`, `multi_branch`, `export_reports`, `patient_portal`, `telehealth`, `custom_branding`).
- Implemented robust JSON array/dict parsing and serialization preserving unknown or custom features.
- Replaced native alerts with shared UI toast notifications.
- Created unit tests verifying feature parsing, custom tag preservation, and plan card rendering.

Notes:
- Plan features checklist matches backend schema and ensures custom feature keys are never dropped.

---

## MS-08 — Audit filter/export/tenant labels
Status: PASS
Commit: c6ddb868
Files changed:
- `backend/routers/system_admin.py`
- `backend/tests/test_admin_system.py`
- `frontend/src/features/admin/SuperAdmin/AuditLogViewer.jsx`
- `frontend/src/features/admin/SuperAdmin/AuditLogViewer.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/AuditLogViewer.test.jsx --run` -> PASS (1 test file, 3 tests passed)
- `uv run ruff check --config ruff.toml backend/routers/system_admin.py` -> PASS (All checks passed)
- `$env:PYTHONPATH="c:\Users\es\DENTIX"; uv run pytest backend/tests/test_admin_system.py` -> PASS (8 passed)

Manual verification:
- Updated `export_audit_logs` endpoint in `backend/routers/system_admin.py` to accept and apply `start_date` and `end_date` date-range filters to exported CSV.
- Mapped `tenant_id` to actual tenant names via `tenants` prop (`tenantMap` / `getTenantLabel`), preventing tenant events from being mislabeled as "System Global".
- Separated network/fetch failure state from empty audit results with a clear error message and retry button.
- Revoked CSV export Object URL with `window.URL.revokeObjectURL(url)`.

Notes:
- CSV export strictly matches visible filters, and tenant events display correct tenant labels.

---

## MS-09 — Finance runtime and mobile safety
Status: PASS
Commit: 0815d80a
Files changed:
- `frontend/src/features/admin/SuperAdmin/FinanceReports.jsx`
- `frontend/src/features/admin/SuperAdmin/PaymentsManager.jsx`
- `frontend/src/features/admin/SuperAdmin/ActiveSubscriptions.jsx`
- `frontend/src/features/admin/SuperAdmin/FinanceRuntime.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/FinanceRuntime.test.jsx --run` -> PASS (1 test file, 3 tests passed)

Manual verification:
- Imported `ShieldCheck` directly in `FinanceReports.jsx` to eliminate reference errors.
- Added zero-overdue state display in `FinanceReports.jsx`.
- Wrapped Payments table and ActiveSubscriptions table in `overflow-x-auto` to prevent layout breaking on 320/360px viewports.
- Added null-safe amount, date, and tenant name rendering across finance components.
- Added i18n support and responsive RTL/LTR direction in `ActiveSubscriptions.jsx`.

Notes:
- Finance dashboard and tables are fully responsive, localized, and resilient against missing/null runtime fields.

## MS-10 — Subscription status semantics
Status: PASS
Commit: b7287dcf

Files changed:
- `backend/routers/admin_stats.py`
- `backend/tests/test_admin_stats_semantics.py`
- `frontend/src/features/admin/SuperAdmin/TenantsManager.jsx`
- `frontend/src/features/admin/SuperAdmin/ActiveSubscriptions.jsx`
- `frontend/src/features/admin/SuperAdmin/SubscriptionSemantics.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/SubscriptionSemantics.test.jsx --run` -> PASS (1 test file, 3 tests passed)
- `uv run ruff check --config ruff.toml backend/routers/admin_stats.py backend/tests/test_admin_stats_semantics.py` -> PASS (All checks passed)
- `$env:PYTHONPATH="c:\Users\es\DENTIX"; uv run pytest backend/tests/test_admin_stats_semantics.py` -> PASS (1 passed)

Manual verification:
- Operational active defined strictly as `is_deleted == False AND is_active == True AND (subscription_end_date IS NULL OR subscription_end_date >= now)`.
- Expired defined strictly as `is_deleted == False AND subscription_end_date < now`.
- Archived/deleted tenants (`is_deleted == True`) excluded from operational counts across dashboard KPIs, tenant tables, and subscriptions.
- Documented chosen definition in backend and frontend unit tests.

Notes:
- Subscription status counts and labels are now 100% unified and consistent across Super Admin.

## MS-11 — Dashboard 12-month analytics
Status: PASS
Commit: f548e938

Files changed:
- `backend/routers/admin_stats.py`
- `backend/tests/test_admin_charts_12m.py`
- `frontend/src/features/admin/SuperAdmin/AdminCharts.jsx`
- `frontend/src/features/admin/SuperAdmin/AdminCharts.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/AdminCharts.test.jsx --run` -> PASS (1 test file, 2 tests passed)
- `uv run ruff check --config ruff.toml backend/routers/admin_stats.py backend/tests/test_admin_charts_12m.py` -> PASS (All checks passed)
- `$env:PYTHONPATH="c:\Users\es\DENTIX"; uv run pytest backend/tests/test_admin_charts_12m.py` -> PASS (1 passed)

Manual verification:
- Restricted revenue and clinic growth to exactly 12 months with chronological zero-filled baseline for missing months.
- Excluded payments and tenants older than 12 months from chart calculations.
- Localized month axis/tooltip labels according to active language (Arabic/English).
- Removed redundant Recharts `<Legend />` tag to eliminate duplication with custom card legends.
- Made plan distribution chart responsive with flexible mobile container (`min-h-[300px] flex-col md:flex-row`).
- Added dark mode styling to tooltips and grid strokes.

Notes:
- 12-month window is strictly bounded, chronologically continuous, and free of redundant legends.

## MS-12 — Finance forecast semantics
Status: PASS
Commit: a752f6b3

Files changed:
- `backend/routers/admin_stats.py`
- `backend/tests/test_admin_finance_forecast.py`
- `frontend/src/features/admin/SuperAdmin/FinanceReports.jsx`
- `frontend/src/features/admin/SuperAdmin/FinanceReportsForecast.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/FinanceReportsForecast.test.jsx --run` -> PASS (1 test file, 1 test passed)
- `uv run ruff check --config ruff.toml backend/routers/admin_stats.py backend/tests/test_admin_finance_forecast.py` -> PASS (All checks passed)
- `$env:PYTHONPATH="c:\Users\es\DENTIX"; uv run pytest backend/tests/test_admin_finance_forecast.py` -> PASS (1 passed)

Manual verification:
- Excluded non-active, expired, and soft-deleted tenants from revenue forecast per normalized semantics (`is_deleted == False AND is_active == True AND (subscription_end_date IS NULL OR subscription_end_date >= now)`).
- Aligned overdue list semantics to include only non-deleted expired clinics.
- Replaced PG-specific `date_trunc` with portable Python datetime aggregation for growth trends.
- Added null and invalid date safety in `FinanceReports.jsx` for churn risks and overdue clinics.

Notes:
- Revenue forecast reflects strictly active subscriptions only, and finance reports are fully resilient against missing/invalid dates.

## MS-13 — Manual payment flow
Status: PASS
Commit: af2763c2

Files changed:
- `frontend/src/pages/admin/FinancePage.jsx`
- `frontend/src/pages/admin/FinancePage.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/pages/admin/FinancePage.test.jsx --run` -> PASS (1 test file, 3 tests passed)

Manual verification:
- Migrated manual payment modal to shared accessible `Modal` primitive with responsive dialog/bottom sheet behavior.
- Added strict client-side validation for tenant ID, plan ID, finite positive amount (`isFinite(amount) && amount > 0`), and valid payment date.
- Added double-submission protection and loading states on submit button.
- Automatically cleared payer (`paid_by`) field when tenant selection changes.
- Preserved user input in form on backend failure and displayed backend error message details.
- Replaced `window.confirm` with shared `ConfirmDialog` primitive for deleting subscription payments.

Notes:
- Manual subscription payment flow is robust, prevents duplicate submits, and uses canonical shared dialogs.

## MS-14 — Plan management
Status: PASS
Commit: 3a992e5d

Files changed:
- `frontend/src/features/admin/SuperAdmin/PlansManager.jsx`
- `frontend/src/features/admin/SuperAdmin/PlansManager.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/PlansManager.test.jsx --run` -> PASS (1 test file, 7 tests passed)

Manual verification:
- Replaced browser `window.confirm` with shared accessible `ConfirmDialog` primitive for plan deletion.
- Added numeric payload sanitizers (`sanitizeNumber`, `sanitizeNullableInt`) preventing NaN values in price, duration, max_users, max_patients, and AI limits.
- Added strict field validation for plan code, arabic name, positive duration, and non-negative price before dispatching API calls.
- Replaced direct `api.delete` with canonical `deleteSubscriptionPlan` SDK function.
- Preserved `is_default`, `is_ai_enabled`, `ai_daily_limit`, and synchronized feature checklists across both create and edit flows.
- Surfaced backend error messages and detail strings in toast notifications.

Notes:
- Plan management is resilient, validates inputs, and uses canonical dialogs and API methods.

## MS-15 — Support inbox
Status: PASS
Commit: cefa575a

Files changed:
- `frontend/src/features/admin/SuperAdmin/SupportInbox.jsx`
- `frontend/src/features/admin/SuperAdmin/SupportInbox.test.jsx`
- `frontend/src/pages/admin/CommunicationsPage.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/SupportInbox.test.jsx --run` -> PASS (1 test file, 5 tests passed)

Manual verification:
- Standardized `setMessages` prop across `SupportInbox.jsx` and `CommunicationsPage.jsx`.
- Replaced browser `alert` with shared accessible `Modal` for reviewing support message sender, clinic, date, priority, and full body.
- Replaced browser `confirm` with shared accessible `ConfirmDialog` primitive for deleting messages.
- Synchronized read status immediately upon viewing unread messages, reflecting immediate unread counter decrements.
- Added graceful error handling and data refreshing on status update failures.
- Preserved existing stats cards (total messages, unread messages, high priority messages).

Notes:
- Support inbox provides seamless viewing, accessible modals, and immediate read state synchronization.

## MS-16 — Targeted notification invariant
Status: PASS
Commit: 8196ef25

Files changed:
- `backend/routers/notifications.py`
- `backend/tests/test_admin_notifications_invariant.py`
- `frontend/src/features/admin/SuperAdmin/NotificationsManager.jsx`
- `frontend/src/features/admin/SuperAdmin/NotificationsManager.test.jsx`
- `frontend/src/pages/admin/CommunicationsPage.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `uv run ruff check --config ruff.toml backend/routers/notifications.py backend/tests/test_admin_notifications_invariant.py` -> PASS (All checks passed)
- `$env:PYTHONPATH = "c:\Users\es\DENTIX"; uv run pytest backend/tests/test_admin_notifications_invariant.py` -> PASS (1 passed, 100% coverage on test)
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/NotificationsManager.test.jsx --run` -> PASS (1 test file, 5 tests passed)

Manual verification:
- Backend enforces that non-global targeted notifications must have a valid, existing `tenant_id` (returns 422 if missing, 404 if nonexistent).
- Backend normalizes `tenant_id` to `None` when `is_global` is `True`.
- Frontend automatically normalizes `tenant_id` to `null` when switching to "All Clinics", and defaults to an available tenant when switching to "Specific Clinic".
- Added double-send protection (`isSending` state and disabled submit button during transmission).
- Replaced notification delete prompt with shared accessible `ConfirmDialog` primitive.
- Surfaced backend error validation details directly in toast alerts.

Notes:
- No ownerless or dangling targeted notification can be created across frontend or backend.

## MS-17 — Settings and global announcement
Status: PASS
Commit: f2423339

Files changed:
- `backend/main.py`
- `frontend/src/features/admin/SuperAdmin/SettingsManager.jsx`
- `frontend/src/features/admin/SuperAdmin/SettingsManager.test.jsx`
- `frontend/src/shared/ui/GlobalBanner.jsx`
- `frontend/src/pages/Support.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `uv run ruff check --config ruff.toml backend/main.py` -> PASS (All checks passed)
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/SettingsManager.test.jsx --run` -> PASS (1 test file, 5 tests passed)

Manual verification:
- Removed stale `(قريباً)` text from Global Announcement settings card since global announcements are fully live in `GlobalBanner`.
- Replaced browser `alert` with canonical toast notifications (`toast.success`, `toast.error`).
- Replaced browser confirmation with shared accessible `ConfirmDialog` primitive for maintenance mode toggle.
- Added state rollback on API failures in `SettingsManager`.
- Verified global announcement pipeline: Super Admin updates `global_announcement` -> `/api/v1/global-settings` -> `GlobalBanner` banner display.
- Replaced obsolete Smart Dental contact fallbacks in `backend/main.py` and `frontend/src/pages/Support.jsx` with canonical `support@dentix.com`.
- Removed uncalculated static "Available now" claim box from `Support.jsx`.

Notes:
- Settings are truthful, resilient, and synchronized with live frontend banners and support contact endpoints.

## MS-18 — Profile update alignment
Status: PASS
Commit: 5534fea1

Files changed:
- `backend/routers/system_admin.py`
- `backend/tests/test_super_admin_profile.py`
- `frontend/src/pages/admin/SystemPage.jsx`
- `frontend/src/pages/admin/SystemPage.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `uv run ruff check --config ruff.toml backend/routers/system_admin.py backend/tests/test_super_admin_profile.py` -> PASS (All checks passed)
- `$env:PYTHONPATH = "c:\Users\es\DENTIX"; uv run pytest backend/tests/test_super_admin_profile.py` -> PASS (1 passed, 100% coverage on test)
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/pages/admin/SystemPage.test.jsx --run` -> PASS (1 test file, 4 tests passed)

Manual verification:
- Integrated `PUT /api/v1/admin/system/profile` endpoint enforcing existing password policy (`validate_password`), length >= 8, complexity, and uniqueness checks.
- Form disables submit when all inputs are empty, and client validation prevents empty submissions.
- Replaced browser `window.confirm` with shared accessible `ConfirmDialog` primitive for profile updates and Google backup uploads.
- Constructed clean payloads with only non-empty, trimmed fields.
- Refreshed client identity in `useAuthStore` upon successful update.
- Cleared password input state immediately following successful profile updates.
- Surfaced detailed backend validation errors in toast notifications on error.

Notes:
- Super Admin profile management conforms to standard password policy, secure error propagation, and reactive auth state synchronization.

## MS-19 — 2FA hardening
Status: PASS
Commit: Pending
Files changed:
- `frontend/src/features/admin/SuperAdmin/TwoFactorSetup.jsx`
- `frontend/src/features/admin/SuperAdmin/TwoFactorSetup.test.jsx`
- `docs/execution/super-admin/SUPER_ADMIN_EXECUTION_LEDGER.md`

Tests/commands:
- `npm.cmd run lint` -> PASS (0 errors, 0 warnings)
- `npm.cmd test -- src/features/admin/SuperAdmin/TwoFactorSetup.test.jsx --run` -> PASS (1 test file, 5 tests passed)

Manual verification:
- Replaced browser `window.confirm` with shared accessible `ConfirmDialog` primitive for disabling 2FA.
- Reset setup state (`setupData`, secret, QR code, verification code) on cancel to prevent stale credentials from leaking or persisting.
- Added strict null guards for `setupData`, `secret`, and `qr_code`.
- Implemented robust clipboard copy with try-catch and informative toasts.
- Standardized Arabic strings with full i18n support and RTL alignment.
- Protected all submission flows against duplicate dispatch and enforced 6-digit code validation.

Notes:
- 2FA setup, validation, cancellation, and disable flows are deterministic, safe, and fully tested.

---







