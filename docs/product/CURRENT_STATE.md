<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Current State Card
Updated by the executor at the end of every task PR (max 10 lines changed). New Claude/Argon chats start from this file.

- Plan: Odontogram & Clinical VNext (docs/product/ODONTOGRAM_EXECUTION_QUEUE.md)
- Baseline: staging @ 1907061 (PR #291).
- Pre-production auth PR-A (2026-10-27): optional email migration 1e2f3a4b5c6d; symmetric username lookup; JSON registration; no production data rewrite.
- PR-A verification: 37 targeted backend tests + 2 frontend tests passed; disposable PostgreSQL NULL/unique/up/down checks passed; PR-A remote delivery authorized only after green combined full validation.
- PR-A follow-up: new-head fixtures/lineage updated; 61 targeted migration tests passed, 1 existing PostgreSQL-only skip. Combined full-run failures and rechecks are recorded in docs/reports/.
- Final combined full validation (2026-10-27): backend 1431 passed/0 failed/4 existing skips; Vitest 988 passed/0 failed/0 skipped (151 files); ESLint/build PASS. Only PR-A push/PR authorized; PR-B local, no merge.
- Browser-session slice (local, PARTIAL): remember-me session mode and password visibility; review findings corrected; independent re-review pending. See docs/reports/browser-session-mode-2026-10-27.md.
- Current task: Upload error detail surfacing & service worker navigation fallback hardening (fix/upload-error-and-sw-fallback).
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
