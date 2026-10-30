# DENTIX Remaining Clinic Workflows — Cumulative Implementation & Reviewer Handoff Report (2026-10-27)

**Overall Status:** `PARTIAL` (All local implementation, unit/integration suites, restricted PostgreSQL FORCE RLS/concurrency suites, frontend lint/build/guardrails/Vitest suites, and migration checks PASS; live external SMTP and live Google Console/Drive round-trip checks remain pending Eslam's external credential configuration).

---

## 1. Branch, Base, Lineage, Bundles & Reconciled Commits

- **Implementation branch:** `feat/remaining-clinic-workflows`
- **Base (`origin/staging`):** `41991dbd5bd3aff5c367252dd9e848f7aaf69108` (merge of PR #316 `feat/browser-session-mode`)
- **Locally reconciled password-policy commits:** Reused implementation and test changes from `feat/relaxed-password-policy` (`f75124f` and `f2626c3`) in commit `6b043e0` without importing stale state-card or historical full-run claims.
- **Linear Alembic Migration Lineage (Single Head Verified):**
  `0d1e2f3a4b5c` → `1e2f3a4b5c6d` (optional user email) → `ed137fa8c304` (user session `remember_me`, staging base) → `9ab047d5613e` (`lab_choice` columns on `treatments` and `clinical_work_items`) → `ba7526e3a901` (`treatments` request idempotency columns/index) → `c38f91a2d47b` (`tenant_data_operations` table + RLS) → `d42a71e9bc83` (PostgreSQL per-tenant restore transaction gate triggers) → `e82c19f5a406` (`tenants` Google connection fields + `google_oauth_attempts` table + RLS) → `f17a93c60e24` (`tenants` Google folder reservation columns) → `ab52d9c807a1` (`tenant_data_operations` remote file ID & archive digest) → `bc78a10d932e` (`attachments` Drive metadata columns & storage UUID index — **single head**).
- **Verified Local Git Bundles (untracked, preserved in workspace root):**
  - `remaining-clinic-workflows-wip.bundle`
  - `remaining-clinic-workflows-diagnosis.bundle`
  - `remaining-clinic-policy.bundle`
  - `remaining-clinic-inventory.bundle`
  - `remaining-clinic-reset-wip.bundle`, `remaining-clinic-reset-followup.bundle`
  - `remaining-clinic-lab-wip.bundle`, `remaining-clinic-rules-wip.bundle`, `remaining-clinic-schema-wip.bundle`, `remaining-clinic-lab-archive-wip.bundle`
  - `remaining-clinic-archive-registry-wip.bundle`, `remaining-clinic-archive-references-wip.bundle`, `remaining-clinic-archive-validation-wip.bundle`
  - `remaining-clinic-restore-preview-wip.bundle`, `remaining-clinic-restore-gate-wip.bundle`, `remaining-clinic-restore-engine-wip.bundle`, `remaining-clinic-link-check-wip.bundle`, `remaining-clinic-legacy-adapter-wip.bundle`, `remaining-clinic-backup-flow-wip.bundle`
  - `remaining-clinic-google-connection-wip.bundle`, `remaining-clinic-drive-backup-wip.bundle`, `remaining-clinic-drive-images-wip.bundle`

---

## 2. Slice-by-Slice Implementation, Root Cause, Rollout/Rollback & Evidence

### Slice 0 — Relaxed Password Policy Reconciliation (`6b043e0`)
- **Before & Root Cause:** `staging` required a special character and a `zxcvbn` score in `backend/core/password_policy.py` and frontend validators, while the relaxed policy (8–64 chars, at least one letter and one digit, weak-password blocklist) was on unmerged local branch `feat/relaxed-password-policy`.
- **Changes & Entry Points:** Reconciled `backend/core/password_policy.py`, `backend/schemas/auth.py`, `backend/schemas/tenant.py`, `frontend/src/utils/passwordPolicy.js`, `RegisterClinic.jsx`, `ResetPassword.jsx`, `SecuritySettings.jsx`, `UsersManager.jsx`, and `Tenants.jsx`. Retained PR #316's accessible password visibility toggle in `ResetPassword.jsx`.
- **Regression Tests:** `backend/tests/test_password_policy.py`, `frontend/src/tests/passwordPolicy.test.js`, `frontend/src/tests/reset_password.test.jsx`.

### Slice 1 — Browser Session Mode ("Remember Me") & Password Visibility (`origin/staging` PR #316 `41991db`, verified on combined head)
- **Before & Root Cause:** Web login always emitted persistent cookies (`Max-Age`/`Expires`), `UserSession` always used a fixed 7-day expiry, and login/registration lacked accessible show/hide password controls.
- **Changes & Entry Points:**
  - `remember_me` optional form field (defaults to `True` for legacy/native callers; web `Login.jsx` sends explicit `false` when unchecked).
  - Stored on `UserSession.remember_me` (migration `ed137fa8c304`), carried through signed 2FA temporary token (`pending_2fa` scope denied on ordinary endpoints), and preserved across `/api/v1/auth/refresh` rotations.
  - Persistent mode sets `Max-Age`/`Expires` within `REFRESH_TOKEN_EXPIRE_DAYS`; session mode omits `Max-Age`/`Expires` on auth, session-hint, and CSRF cookies. Note: closing a single tab does not end a browser session, and browser session restoration can restore session cookies across browser restarts.
  - Accessible `type="button"` show/hide controls with `aria-pressed` and Arabic labels on `Login.jsx`, `RegisterClinic.jsx`, and `ResetPassword.jsx`.
- **Rollout & Rollback:** Additive migration `ed137fa8c304` (parent `1e2f3a4b5c6d`). Do not roll back to a server revision that ignores `UserSession.remember_me` while non-persistent sessions are active without revoking sessions first, or a refresh would convert session cookies into persistent cookies.
- **Regression & PG Evidence:** `backend/tests/test_remember_me.py`, `backend/tests/test_session_mode_migration.py`, `backend/ci_tests/test_auth_cookie_flow_http.py` (6 passed on restricted PostgreSQL `NOBYPASSRLS`), `frontend/src/tests/Login.test.jsx`, `frontend/src/tests/RegisterClinic.visibility.test.jsx`, `frontend/src/tests/AuthProvider.2fa.test.jsx`.

### Slice 2 — Password Reset Workflow (`d0ed83a`, `77847e1`, `0a67bed`, `0408299`)
- **Before & Proven Root Cause:**
  1. **Runtime reproduction on restricted PostgreSQL:** Anonymous `POST /api/v1/auth/forgot-password` queried `models.User` without a tenant context; under PostgreSQL `FORCE ROW LEVEL SECURITY`, zero rows were visible, returning HTTP 200 without invoking any email sender.
  2. **Static findings:** `password_reset.py` selected Firebase reset links when Firebase was initialized even though login authenticates against `User.hashed_password`; SMTP failures leaked different status codes; `DEBUG` logged raw reset links.
- **Changes & Entry Points:**
  - Narrow, audited email-only and reset-token-digest bootstrap helpers in `backend/services/auth_bootstrap.py` (`resolve_password_reset_email_identity`, `resolve_password_reset_token_identity`) that resolve identity under `bypass_rls()`, reject orphaned clinic users, bind the resolved tenant context, and re-read under normal tenant/RLS enforcement.
  - Local reset token path only (32-byte random `secrets.token_urlsafe(32)`, SHA-256 digest stored in `PasswordResetToken.token`, 15-minute expiry, single-use).
  - Encrypted short-lived delivery payload queued via `DomainEvent` (`password_reset.email_requested`) and processed by `backend/workers/handlers.py`, eliminating SMTP timing oracle and scrubbing encrypted payloads on supersession, delivery, expiry, or retry exhaustion.
  - Transactional row-locked token consumption + `User.hashed_password` update (validated via shared password policy) + `UserSession` revocation while preserving `is_2fa_enabled` and `otp_secret`.
  - Static universal guidance displayed on `ForgotPassword.jsx`: `لو حسابك بدون بريد إلكتروني، اطلب من مدير العيادة تعيين كلمة مرور جديدة`.
  - Verified same-tenant admin password update in `backend/routers/users.py` enforces tenant scope, shared password policy, and session revocation.
- **Rollout & Rollback:** No schema change required (uses `password_reset_tokens` and `domain_events`). If SMTP delivery fails in production, disable new reset requests with a clear Arabic message while keeping clinic admin password reset active; never fall back to unsynchronized Firebase password links.
- **Regression & PG Evidence:** `backend/ci_tests/test_password_reset_identity_rls.py` (8 passed on restricted PostgreSQL covering clinic user, super_admin, orphan denial, end-to-end fake mail capture → reset → login, session revocation, 2FA preservation, replay/concurrent consumption, supersession scrubbing, and cross-tenant admin denial), `backend/tests/test_reset_email_redaction.py`, `frontend/src/tests/ForgotPassword.help.test.jsx`.

### Slice 3 — Explicit Laboratory Choice & Atomic Treatment/Lab Writes (`40c2e14`, `874340b`, `d4f813c`, `d845e49`, `32b0c86`)
- **Write Entry Points Audited & Covered:**
  1. `POST /api/v1/treatments` (`TreatmentService.create_treatment`)
  2. `PUT /api/v1/treatments/{id}` (`TreatmentService.update_treatment`)
  3. `POST /api/v1/patients/{id}/teeth/{tooth}/treatments` (`TreatmentService.create_multi_procedure_treatment`)
  4. `POST /api/v1/lab-orders` & `PUT /api/v1/lab-orders/{id}` (`backend/routers/laboratories.py` & `LabService`)
  5. `POST /api/v1/clinical/patients/{id}/work-items/{wi_id}/lab-handoff` (`backend/routers/clinical_workspace.py`)
  6. `POST /api/v1/clinical/patients/{id}/commands` (`ClinicalCommandService.record_procedure` / `correct_work_item`)
  7. `ClinicalService` (`backend/services/clinical_service.py`) & AI tool callers (`backend/ai/tools.py` — AI never auto-selects `in_clinic` for lab-required procedures).
- **Changes & Rules Implemented:**
  - Added nullable `lab_choice` (`external_lab` | `in_clinic`) to `treatments` and `clinical_work_items` (migration `9ab047d5613e`, no backfill of historical records) and tenant-scoped `request_key` + `request_fingerprint` on `treatments` (migration `ba7526e3a901`).
  - Authoritative rules in `backend/clinical/lab_choice.py` and `backend/clinical/lab_links.py` gated behind `clinical_vnext_native_writes`:
    - Lab-required procedure (`PROS_CROWN`, `PROS_BRIDGE`, `IMPLANT_CROWN`, `PROS_DENTURE`, legacy equivalents, or custom prosthodontic categories) without explicit `lab_choice` → HTTP 422 in plain Arabic.
    - `in_clinic` with any lab order, cost (including explicit `0`), `paid_now`, shade, material, delivery date, or lab notes → HTTP 422.
    - `external_lab` creates treatment + linked `LabOrder` + optional initial `LabPayment` atomically in a single transaction (`LabService.create_lab_order(..., commit=False)`).
    - Switching an existing treatment with an active lab order to `in_clinic` is blocked (HTTP 422) until the order is settled/cancelled.
  - Frontend `QuickTreatmentSheet.jsx` & `useTreatmentOperations.js` updated with explicit `بدون معمل (داخل العيادة)` option, inline validation, hidden lab cost/payment fields when `in_clinic` is chosen, and single atomic save request (removed split second POST `/api/v1/lab-orders`).
- **Rollout & Rollback:** Migrations `9ab047d5613e` and `ba7526e3a901`. Gated by `clinical_vnext_native_writes`. Rollback preserves stored `lab_choice`, `LabOrder`, and `LabPayment` rows.
- **Regression & PG Evidence:** `backend/tests/test_lab_choice_rules.py`, `backend/tests/test_treatment_lab_atomic.py`, `backend/ci_tests/test_treatment_lab_atomic_pg.py`, `frontend/src/features/clinical-chart/tests/QuickTreatmentSheet.labChoice.test.jsx`, `frontend/src/features/patients/hooks/useTreatmentOperations.test.js`.

### Slice 4 — Complete & Safe Clinic Backup/Restore Engine (`1c06e99`, `cf4824f`..`612083f`, `1fa1316`, `20e8bb9`)
- **Before & Root Cause:** Legacy export/import omitted `material_sessions`, `stock_movements`, and `procedure_material_weights`, lacked authenticated encryption, wiped and re-created `models.User` rows from JSON, and had no database-wide lock against concurrent clinic writes during restore.
- **Changes & Entry Points:**
  - **Authenticated Envelope (`backend/services/tenant_archive.py`):** AES-256-GCM encrypted archive (`DENTIX_TENANT_ARCHIVE`, format version 1) with authenticated header/AAD binding `magic`, `format_version`, `schema_revision`, `backup_uuid`, `exported_at`, `tenant_id`, `installation_id` (`DENTIX_INSTALLATION_ID`), `key_id` (`TENANT_BACKUP_KEY_ID`), `section_counts`, and `payload_sha256`. Supports key rotation via `TENANT_BACKUP_PREVIOUS_KEYS_JSON` and enforces bounded streaming read up to `TENANT_BACKUP_MAX_BYTES` (default 100 MiB).
  - **Complete Registry & Validation (`tenant_archive_registry.py`, `tenant_archive_embedded_refs.py`, `tenant_archive_identity.py`):** Covers all 43 clinic business tables + `staff_references` (financial staff attributes `commission_percent`, `fixed_salary`, `per_appointment_fee`, `hire_date` separated from credentials/roles/permissions). Validates all scalar types, SQL FKs, embedded JSON references (`TREATMENT:<id>`, `Link:LabOrder:<id>`, clinical event payloads), and requires explicit same-tenant staff identity resolution before deletion.
  - **Legacy JSON Adapter (`tenant_archive_legacy.py`):** Safely adapts legacy v1.0 JSON backups, strips any legacy credential/role fields, backfills missing inventory sections as empty lists while disclosing `missing_sections` and `legacy_unverified=True` in preview.
  - **Preview, Single-Use Confirmation & DB Transaction Gate (`tenant_restore_preview.py`, `tenant_restore_coordinator.py`, migrations `c38f91a2d47b` & `d42a71e9bc83`):**
    - Requires clinic `admin` role + `SYSTEM_CONFIG` + fresh current password/2FA verification.
    - Preview stores encrypted validated payload in `tenant_data_operations` (RLS-enforced) with 10-minute expiry bound to `tenant_id`, `actor_id`, and `confirmation_digest`.
    - PostgreSQL constraint trigger `dentix_guard_tenant_restore_write()` blocks concurrent writes to clinic tables on the restoring tenant while allowing other tenants to operate normally.
- **Rollout & Rollback:** Migrations `c38f91a2d47b` and `d42a71e9bc83`. Never roll back to the unauthenticated/raw-user-import restore path.
- **Regression & PG Evidence:** `backend/tests/test_tenant_archive.py`, `backend/ci_tests/test_tenant_data_operations_rls.py`, `backend/ci_tests/test_restore_transaction_gate_pg.py`, `backend/ci_tests/test_tenant_archive_restore_pg.py`, `frontend/src/features/settings/SettingsTabs/BackupSettings.test.jsx`.

### Slice 5 — Per-Clinic Google Connections (`c0e70bf`)
- **Before & Root Cause:** OAuth relied on process-global state, lacked PKCE/browser binding, accepted authenticated POST callback without state validation, selected folders by name, and could allow `GOOGLE_SERVICE_ACCOUNT_JSON` to take precedence over clinic OAuth.
- **Changes & Entry Points:**
  - Migrations `e82c19f5a406` & `f17a93c60e24` add `google_account_sub`, `google_account_email`, `google_connection_status` (`disconnected` | `connected` | `needs_reconnect`), `google_connection_generation`, `google_root_folder_id`, `google_backup_folder_id`, `google_image_folder_id`, `google_pending_*` folder reservation columns on `tenants`, and RLS-protected `google_oauth_attempts`.
  - Restricted to clinic `admin` + `SYSTEM_CONFIG`. Requests only `drive.file`, `openid`, `email` with PKCE (`S256`) and per-attempt state bound to an HttpOnly browser cookie (`dentix_google_oauth`), user, tenant, and `DENTIX_INSTALLATION_ID`.
  - Verifies Google ID token `sub` and granted scopes; provisions isolated `DENTIX` -> `Backups` and `Images` folders with appProperties ownership metadata and pre-reserved IDs; blocks switching Google accounts when existing Drive images belong to a different `google_account_sub`; ignores `GOOGLE_SERVICE_ACCOUNT_JSON` in clinic Drive operations.
  - Disconnect clears local refresh token and increments `google_connection_generation` without revoking project-wide Google grants shared by other clinics.
  - Displays required Arabic notice in `BackupSettings.jsx`: `الملفات محفوظة في حساب Google الخاص بالعيادة، والعيادة مسؤولة عن صلاحيات الوصول إلى هذا الحساب`.
- **Regression & PG Evidence:** `backend/ci_tests/test_google_oauth_attempt_rls.py`, `backend/ci_tests/test_clinic_google_callback_pg.py`, `backend/tests/test_clinic_google_connection.py`.

### Slice 6 — Manual Drive Backup, Listing & Restore (`bbdfc18`)
- **Changes & Entry Points:**
  - Migration `ab52d9c807a1` adds `remote_file_id` and `archive_digest` to `tenant_data_operations`.
  - `POST /api/v1/settings/backups/drive` queues a durable `drive_backup` operation (`backend/services/clinic_drive_backup.py`), exports from a consistent DB snapshot, encrypts with Phase 4's AES-256-GCM engine, releases the DB transaction before network I/O, reserves a stable Drive file ID for idempotent retries, and cleans up encrypted staging data on completion/failure.
  - `GET /api/v1/settings/backups/drive` lists only verified files inside the clinic's `google_backup_folder_id` matching tenant/installation `appProperties`.
  - `POST /api/v1/settings/backups/drive/{file_id}/preview` downloads with hard byte limits, verifies folder/appProperties and AES-256-GCM authenticity, and feeds Phase 4's preview/confirmation coordinator.
  - Classifies `invalid_grant` (`needs_reconnect`), `storageQuotaExceeded` (plain Arabic quota message without disconnecting), and transient/rate-limit errors (bounded exponential backoff honoring `Retry-After`).
- **Regression & PG Evidence:** `backend/ci_tests/test_drive_backup_operations_pg.py`.

### Slice 7 — Store New Patient Images on Drive (`7318eb6`)
- **Changes & Entry Points:**
  - Migration `bc78a10d932e` adds `storage_provider`, `storage_uuid`, `drive_original_id`, `drive_thumbnail_id`, `original_size`, `original_sha256`, `thumbnail_sha256`, `google_account_sub`, `connection_generation`, and `storage_status` to `attachments`.
  - When clinic Google Drive is connected, supported image uploads (`POST /api/v1/upload`) validate pixel/size limits (`backend/services/drive_image_processing.py`), preserve original medical bytes untouched, generate a separate JPEG thumbnail, stage an idempotent `drive_image_upload` operation (`backend/services/drive_image_operations.py`), and return a protected DENTIX content path `/api/v1/upload/drive/{storage_uuid}/content` (never exposing Drive IDs or tokens in DTOs). Non-image attachments (PDF/DICOM) remain on existing storage; when Drive is configured, Drive failures return clear Arabic errors and never silently fall back to local/Cloudinary storage.
  - Protected retrieval (`GET /api/v1/upload/drive/{storage_uuid}/content` and `?variant=thumbnail`) enforces user auth → tenant scope → patient visibility → attachment ownership AND active clinic Google connection before ETag/304 or Range (`206 Partial Content`) handling, with `Cache-Control: private, no-store` and bounded in-memory LRU cache (`DRIVE_IMAGE_CACHE_MAX_BYTES` default 64 MiB, 8 MiB max item, `DRIVE_IMAGE_CACHE_TTL_SECONDS` default 300s, single-flight deduplication, keyed by `(tenant_id, storage_uuid, sha256, variant, connection_generation)`).
  - Cache is cleared on disconnect/reconnect/delete/restore; service worker excludes `/api/`; `AuthProvider.jsx` clears protected image blob URLs on logout; `ProtectedImage.jsx` displays `الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف` when a remote image is unavailable.
  - Deletions queue retryable `drive_image_delete` / compensating `drive_image_cleanup` operations that verify `appProperties` ownership before deleting remote originals/thumbnails.
  - Backup/restore preserves `storage_uuid` and Drive metadata across regenerated patient IDs and reports unavailable attachments in restore preview.
- **Regression & PG Evidence:** `backend/ci_tests/test_drive_images_pg.py`, `backend/tests/test_drive_image_cache.py`, `backend/tests/test_drive_image_processing.py`, `frontend/src/features/clinical-attachments/components/ProtectedImage.test.jsx`.

---

## 3. Backup Coverage Matrix & Exclusions

### Included Clinic Business Tables (43 tables + `staff_references`)

| Category | Tables Included in Authenticated Clinic Archive |
|---|---|
| Staff Business References (`staff_references`) | `users` subset: `id`, `username`, `full_name`, `email`, `commission_percent`, `fixed_salary`, `per_appointment_fee`, `hire_date` (mapped to live same-tenant users; never overwrites credentials/roles/permissions) |
| Patients & Legacy Clinical | `patients`, `appointments`, `treatments` (incl. `lab_choice`), `treatment_sessions`, `tooth_status`, `prescriptions`, `saved_medications`, `attachments` (incl. Drive metadata & `storage_uuid`, no image bytes) |
| Clinical VNext & Odontogram | `clinical_work_items` (incl. `lab_choice`), `clinical_work_item_targets`, `clinical_treatment_plans`, `clinical_treatment_plan_phases`, `clinical_treatment_plan_items`, `care_sessions`, `care_session_steps`, `clinical_events`, `clinical_event_targets`, `care_observations`, `workflow_templates`, `next_visit_requests`, `clinical_attachment_links`, `clinical_projection_coverages`, `clinical_charges`, `procedure_chart_styles` |
| Catalog, Pricing & Finance | `procedures`, `insurance_providers`, `price_lists`, `price_list_items`, `payments`, `expenses`, `salary_payments` |
| Dental Laboratory | `laboratories`, `lab_orders`, `lab_payments` |
| Inventory & Smart Consumption | `warehouses`, `materials`, `batches`, `stock_items`, `material_sessions`, `stock_movements`, `procedure_material_weights`, `material_learning_logs`, `treatment_material_usages` |

### Explicitly Excluded Tables (Preserved / Never Wiped or Imported from Clinic Backup)

| Category | Excluded Tables / Columns & Reason |
|---|---|
| Identity & Access Control | `users.hashed_password`, `users.otp_secret`, `users.is_2fa_enabled`, `users.role`, `users.permissions`, `users.patient_visibility_mode`, `users.can_view_other_doctors_history`, `user_sessions`, `password_reset_tokens`, `login_history`, `push_subscriptions`, `user_onboarding_state` |
| Security & Audit Evidence | `audit_logs`, `security_events`, `blocked_ips`, `system_errors`, `ai_logs` |
| Platform, Billing & Queue State | `tenants`, `subscription_plans`, `subscription_payments`, `subscription_checkouts`, `subscription_renewal_requests`, `feature_flags`, `tenant_features`, `system_settings`, `daily_system_stats`, `material_categories` (global catalog resolved by ID/name), `notifications`, `notification_reads`, `support_messages`, `background_jobs`, `domain_events`, `tenant_data_operations`, `google_oauth_attempts` |

---

## 4. Final Verification Gate Evidence

All commands executed on the combined head:

1. **Alembic Single Head & Model/Migration Drift Check:**
   - `DATABASE_URL='postgresql://dentix_ci_system@/dentix_full_test?host=/tmp&port=55432' .venv/bin/alembic -c backend/alembic.ini heads` → `bc78a10d932e (head)` (exit `0`).
   - `DATABASE_URL='postgresql://dentix_ci_system@/dentix_full_test?host=/tmp&port=55432' SECRET_KEY='test-secret-key-for-ci-only-at-least-32' PYTHONPATH=. .venv/bin/python -m backend.scripts.check_migration_drift` → `No structural model/migration drift detected.` (exit `0`).
2. **Backend Ruff & Bandit Security Gate:**
   - `.venv/bin/ruff check --config ruff.toml backend` → `All checks passed!` (exit `0`).
   - `.venv/bin/bandit -r backend/ -lll -x backend/tests,backend/scripts --format txt` → `No issues identified.` (exit `0`).
3. **Restricted PostgreSQL (`NOBYPASSRLS` app / `BYPASSRLS` system) Full `backend/ci_tests/` Suite:**
   - `SECRET_KEY='test-secret-key-for-ci-only-at-least-32' DATABASE_URL='postgresql://dentix_ci_app@/dentix_full_test?host=/tmp&port=55432' SYSTEM_DATABASE_URL='postgresql://dentix_ci_system@/dentix_full_test?host=/tmp&port=55432' ENVIRONMENT=test PYTHONPATH=. .venv/bin/python -m pytest -p no:ddtrace -o addopts='' -q --tb=short --confcutdir=backend/ci_tests backend/ci_tests/`
   - **Result:** `61 passed, 0 failed, 0 skipped` (exit `0`).
4. **Full Backend Test Suite (`backend/tests/`):**
   - Intermediate run surfaced 20 failures across 9 files (2 RLS/tenant-scope registry lists missing `TenantDataOperation`/`GoogleOAuthAttempt`, 2 SQLite historical migration fixtures missing `google_refresh_token`/`attachments` columns in synthetic table creation, 2 work-item lab link checks on display names/empty target lists, 1 legacy procedure token link check on `"Crown Zirconia"`, 11 mock-session checks in `TreatmentService`, and 2 legacy `import_service.py` calls expecting `users.hashed_password` placeholder). All were fixed without weakening any test assertion.
   - Final full run: `SECRET_KEY='test-secret-key-for-ci-only-at-least-32' ENVIRONMENT=test PYTHONPATH=. .venv/bin/python -m pytest -p no:ddtrace -o addopts='' -q --tb=short backend/tests/`
   - **Result:** `1487 passed, 0 failed, 4 skipped` (exit `0`).
   - **Skip reasons (all 4 pre-existing):**
     1. `backend/tests/test_auth_flow.py`: TestClient `request.client.host` rate-limiter fixture limitation on refresh endpoint.
     2. `backend/tests/test_clinical_core_schema.py`: Live PostgreSQL trigger check skipped when `TEST_DATABASE_URL` is SQLite (covered in `backend/ci_tests/`).
     3. `backend/tests/test_clinical_Idempotency_and_concurrency.py` (2 tests): Live PostgreSQL concurrency checks skipped when `TEST_DATABASE_URL` is SQLite (covered in `backend/ci_tests/`).
5. **Frontend Guardrails, ESLint, Vite Build & PWA Artifact Baseline:**
   - `cd frontend && npm run design:guardrails` → exit `0`.
   - `cd frontend && node scripts/check-design-system-guardrails.mjs --diff-base=origin/staging` → `No newly-added guarded violations detected.` (exit `0`).
   - `cd frontend && npm run lint` → exit `0` (0 warnings, 0 errors).
   - `cd frontend && npm run build && node scripts/pwa-artifact-report.mjs dist` → exit `0` (`All required PWA artifacts present`).
6. **Full Frontend Vitest Suite (`155` files):**
   - Intermediate run had 1 failure in `src/tests/deploymentAssets.test.js` due to an unnecessary edit to `frontend/vercel.json`; restored `frontend/vercel.json` to match `origin/staging`.
   - Final run: `cd frontend && npm test -- --run` (and `npx vitest run src/tests/deploymentAssets.test.js`) → `155 passed (155 files), 999 passed, 0 failed, 0 skipped` (exit `0`).

---

## 5. External Configuration & Manual Setup Checklist for Eslam

### Environment Variables to Configure in Staging / Production
- **Existing settings verified:**
  - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`: Environment-specific OAuth 2.0 Web Client credentials (separate Google projects for testing/staging vs production).
  - `GOOGLE_REDIRECT_URI`: Exact HTTPS callback URL (`/api/v1/settings/drive/callback`) registered on that environment's Google OAuth client.
  - `BACKEND_PUBLIC_URL`, `FRONTEND_URL`: Allowlisted backend and frontend origins.
  - `ENCRYPTION_KEY`: Persistent 32-byte URL-safe base64 Fernet key for OAuth tokens and short-lived encrypted operation payloads.
  - `GOOGLE_API_TIMEOUT`: Applied network timeout in seconds (default `30`).
  - `APP_URL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` (and supported aliases).
  - `REFRESH_TOKEN_EXPIRE_DAYS`, `MAX_UPLOAD_SIZE_MB` (default `10`).
- **New settings introduced in this branch:**
  - `TENANT_BACKUP_ENCRYPTION_KEY`: URL-safe base64 encoding of 32 random bytes (separate from `ENCRYPTION_KEY` and platform operational backup keys).
  - `TENANT_BACKUP_KEY_ID`: Non-secret active key identifier (e.g. `clinic-archive-v1`).
  - `TENANT_BACKUP_PREVIOUS_KEYS_JSON`: Optional JSON object mapping retired `key_id` strings to their 32-byte URL-safe base64 keys for decrypting older clinic archives after rotation.
  - `DENTIX_INSTALLATION_ID`: Stable environment identifier (e.g. `dentix-staging` vs `dentix-production`); must be persisted across restarts and saved with offline recovery material.
  - `TENANT_BACKUP_MAX_BYTES`: Maximum archive and decoded payload size in bytes (default `104857600` = 100 MiB).
  - `DRIVE_IMAGE_CACHE_MAX_BYTES`: Per-process in-memory LRU cap for Drive images (default `67108864` = 64 MiB; per-item cap 8 MiB).
  - `DRIVE_IMAGE_CACHE_TTL_SECONDS`: In-memory LRU TTL in seconds (default `300`).

### Eslam'sStaging Click Path (Under 15 Minutes per Feature)
1. **Browser Sessions & Password Visibility (< 5 min):**
   - Open Login, toggle the password eye button (verify no form submission), log in with "تذكرني" unchecked, reload, close and reopen browser (recording browser session-restore setting), then repeat with "تذكرني" checked and 2FA enabled.
2. **Password Reset (< 5 min):**
   - On `/forgot-password`, verify static Arabic guidance for no-email accounts. Submit a test account email, open the emailed link, set a new 8+ char alphanumeric password, and verify old sessions are revoked while 2FA remains intact.
3. **Explicit Lab Choice (< 10 min):**
   - In Patient Chart (`QuickTreatmentSheet`), select `Crown`: verify Save is disabled until either an external lab or `بدون معمل (داخل العيادة)` is selected. Save one `in_clinic` crown (no lab fields shown) and one `external_lab` crown with `paid_now`, confirming one atomic request creates treatment, lab order, and payment.
4. **Google Connection & Drive Backup/Restore (< 15 min):**
   - In Settings → Backup, connect a clinic Google account (verify `DENTIX/Backups` and `DENTIX/Images` folders are created), trigger "نسخ احتياطي الآن", wait for completion, preview the backup (reviewing counts, staff mappings, and exclusions), confirm with current password/2FA, and verify business data restores while login credentials remain unchanged.
5. **Drive Patient Images (< 10 min):**
   - Upload a patient image (PNG/JPEG) while Drive is connected; verify thumbnail and lightbox load from `/api/v1/upload/drive/{uuid}/content` without exposing Drive IDs. Disconnect Google Drive in Settings and verify the image shows `الصورة غير متاحة حاليًا، تأكد من ربط جوجل درايف`; reconnect the same Google account and verify the image loads again and deletes cleanly.

---

## 6. Remaining Items for Independent Review & Live Acceptance
- **Independent cumulative review:** Pending examination of the final PR diff and this report by the reviewing assistant.
- **Live external smoke checks (`PARTIAL` until executed by Eslam with live credentials):**
  1. Live SMTP password-reset email delivery round-trip on staging.
  2. Live Google OAuth consent, folder provisioning, Drive archive upload/list/restore, Drive patient image upload/view/delete, and Google Account-side revocation on dedicated test accounts.
