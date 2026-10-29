<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Current State Card
Updated by the executor at the end of every task PR (max 10 lines changed). New Claude/Argon chats start from this file.

- Marketing & Discovery Batch 1 (feat/marketing-arabic-page, 2026-10-29): Implemented standalone static Arabic landing page (/ar) and isolated CSS with WCAG AA contrast (5.48:1 normal, 7.68:1 hover), valid robots.txt & sitemap.xml, precise SW/Vercel network bypasses, and native discovery link in Login (<a href="/ar">).
- Batch 1 Review 2 Updates: Enhanced verify-marketing-artifacts with strict <link> asset resolution & XML root/xmlns validation; hardened Vercel HTTP route tester with strict origin & Content-Type validation; updated PWA lifecycle e2e with waiting assertion, UI update button trigger, explicit timeout rejection, and post-update app route check (60 Vitest / 33 Playwright PASS). Status: READY FOR RE-REVIEW.

- Restore confirmation policy (user request, 2026-10-29): Current-password reauthentication replaces per-restore OTP; active clinic-admin/RBAC, preview actor/digest/token binding and rate limiting remain. Login 2FA settings/flows are unchanged; old clients' optional otp_code remains accepted for compatibility. Wrong password now has a specific Arabic error and the UI explains which account password to use.
- Verification: 49 targeted backend/archive/RBAC/2FA tests + 14 frontend tests PASS; final API assertions rechecked separately. Ruff, targeted ESLint and frontend production build PASS. No live confirmed restore or deployment performed.

- Plan: Odontogram & Clinical VNext (docs/product/ODONTOGRAM_EXECUTION_QUEUE.md)
- Baseline: staging @ 1907061 (PR #291).
- Pre-production auth PR-A (2026-10-27): optional email migration 1e2f3a4b5c6d; symmetric username lookup; JSON registration; no production data rewrite.
- PR-A verification: 37 targeted backend tests + 2 frontend tests passed; disposable PostgreSQL NULL/unique/up/down checks passed; PR-A remote delivery authorized only after green combined full validation.
- PR-A follow-up: new-head fixtures/lineage updated; 61 targeted migration tests passed, 1 existing PostgreSQL-only skip. Combined full-run failures and rechecks are recorded in docs/reports/.
- Final combined full validation (2026-10-27): backend 1431 passed/0 failed/4 existing skips; Vitest 988 passed/0 failed/0 skipped (151 files); ESLint/build PASS. Only PR-A push/PR authorized; PR-B local, no merge.
- Browser-session PR #316 merged (`41991db`). Combined branch `feat/remaining-clinic-workflows` integrates local relaxed password policy + Phases 1–7 (queued RLS-safe password reset, explicit lab choice & atomic writes, AES-256-GCM clinic backup/restore with preview/gate/staff mapping, browser-bound per-clinic Google OAuth, manual Drive backup/restore, and protected Drive patient images with bounded LRU cache); Alembic head `bc78a10d932e`. Status: PARTIAL (local gates PASS; live SMTP/Google smoke pending external setup).
- Current task: Runtime outbox unblock & container ops packaging (2026-10-28).
- Outbox runtime repair (2026-10-28): Packaged `scripts/ops` (guarded backup/restore) in production Docker image; deferred execution imports in backup scheduler and isolated outbox flow from scheduler exceptions; added container image import regression and enabled-worker outbox claim/completion smoke test. Status: DONE.
- Fixes: Surface backend error detail (file size/type) on upload failure; graceful offline/sleep navigation fallback in custom SW (preventing unhandled fetch rejection).
- P1 status: PARTIAL (resolver ready; build-info stamping pending Part B merge on main).
- Decisions: D1 (endo/Fractured aliases mapped), D3 (dashboard cache task isolated session), D4 (plain Arabic clinical warnings & collapsed technical codes).
- Polish fixes: A6 (restore FK order & error sanitization), A7 (material stock eager loading & UI state), A8 (reception queue graceful fallback), A9 (SW precache deduplication & cache v2).
- Last merged PR: #313
- Current brief: Pre-production polish (2026-10-26) + lazy default procedure seeding for pre-existing empty clinics & SW cache recovery (`fix/mobile-white-screen-recovery`).
- Status: READY (lazy default procedure seeding on empty clinic read, non-blocking cache cleanup, SW cache recovery, PERF_DIAGNOSTICS default OFF).
- Promotion to main: All 37 slices (S00–S36) complete. Blocked until staging smoke test and the mandatory stronger-model final review are done (DEVELOPMENT_WORKFLOW §6). Final review: PENDING.

## R1 Additions & Completion (feat/r1-completion-and-additions)
- F-17/F-18/F-11/F-05 fixes: plan overlay multi-surface counting, care session translations, safe interim tooth condition update, invoiced charge correction warnings/audits/notifications.
- Edit/reschedule/postpone appointments with conflict detection, concurrency checks, and dedicated UI modals.
- Medical alert badges on patient list and cards with distinct pregnancy warning indicator.
- Multi-tooth sequential procedure application with surface validation and partial-recovery in clinical chart.
- Backup diagnostics and tenant-scoped operational Excel export (.xlsx) with formula injection protection.
- Restore preview NULL validation fix (2026-10-29): Migration e2b3c4d5e6f7 + models alignment for optional patient clinical notes/history and staff compensation; Alembic head e2b3c4d5e6f7.
- Archive safety & diagnostic hardening: Structured safe diagnostics on ArchiveError (section/field/category/counts without PII/secrets); exporter preflight restore compatibility; legacy JSON numeric adaptation; zero-write rollback verified. Status: DONE.
- Archive reference rejection diagnostics (2026-10-29): Structured safe diagnostics on SQL foreign keys and embedded references (section/field/referenced_section/category/counts without PII/secrets); read-only tenant consistency audit report tool (scripts/maintenance/audit_tenant_archive_consistency.py); router export/preview/confirm diagnostics enriched; preflight & zero-write rollback verified. Status: DONE.
- Deleted-treatment archive recovery (2026-10-29): Explicit same-patient/work-item deletion evidence preserves historical clinical, stock and learning references; restore reserves unused treatment IDs without creating rows or weakening live FK checks. No migration or live-data change.
- Verification: 104 targeted backend tests and 11 restricted-role PostgreSQL tests passed; repeated encrypted restore, legacy JSON preview, ID collisions, rollback/RBAC and financial preservation covered. Live staging preview pending deployment; see docs/reports/archive-deleted-treatment-recovery-2026-10-29.md.
- Learning-history archive repair (2026-10-29): Reproduced the exact `calculation_data.learning_updates.procedure_id` failure after real catalogue deletion; preserve immutable calculation snapshots using reserved absent procedure IDs on restore, while live FK checks remain strict. Resolve only global procedure IDs through the isolated system connection when tenant RLS hides them; no migration or live-data changes.
- Verification: 81 targeted backend/API/RBAC tests + 12 restricted-role PostgreSQL tests passed (0 failures/skips); Ruff/diff checks passed. Live staging acceptance pending delivery/deployment; evidence in docs/reports/archive-learning-history-recovery-2026-10-29.md.
- Pre-delivery adjacent archive review (2026-10-29): HOLD / PARTIAL; four confirmed gaps remain: native session event reference mappings, restored next-visit appointment tokens, unprojected legacy treatment history and lab-order deletion history. Three SQLite diagnostic probes + one encrypted PostgreSQL restore probe reproduced them; see docs/reports/archive-adjacent-reference-review-2026-10-29.md. No remote delivery.
- Adjacent archive recovery implemented (2026-10-29): All four review findings resolved locally: explicit native event/list remapping; same-patient appointment-token remapping; bounded legacy inventory/lab history recovery; atomic lab/treatment deletion with stock reversal and clinical cancellation. Scheduling refresh defect found by real PostgreSQL workflow also fixed; no migration or live-data changes.
- Final pre-delivery review: zero-weight entries in a positive-total closed calculation are preserved; new regression reproduced the rejection before the correction. 214 targeted backend/API/RBAC/service tests + 15 restricted-role PostgreSQL tests passed (0 failures/skips); full backend Ruff and diff checks PASS. Local review DONE; PR delivery authorized, deployment/live acceptance pending. See docs/reports/archive-adjacent-reference-recovery-2026-10-29.md.
