<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Current State Card
Updated by the executor at the end of every task PR (max 10 lines changed). New Claude/Argon chats start from this file.

- Plan: Odontogram & Clinical VNext (docs/product/ODONTOGRAM_EXECUTION_QUEUE.md)
- Baseline: staging @ 1907061 (PR #291).
- Current task: Staging Log Review (2026-10-25) fixes across Items 1-7 (PR #300 on fix/log-review-2026-10-25).
- Log review fixes: Item 1 (configurable DB pool & prompt session closure), Items 2-4 verified on staging, Item 5 (legacy treatment clinical projection safety), Item 6 (care session 404 UX & expired session redirect), Item 7 (4xx log reason & error stack traces).
- P1 status: PARTIAL (resolver ready; build-info stamping pending Part B merge on main).
- Decisions: D1 (endo/Fractured aliases mapped), D3 (dashboard cache task isolated session), D4 (plain Arabic clinical warnings & collapsed technical codes).
- Polish fixes: A6 (restore FK order & error sanitization), A7 (material stock eager loading & UI state), A8 (reception queue graceful fallback), A9 (SW precache deduplication & cache v2).
- Last merged PR: #304
- Pre-production polish (2026-10-26): PR1 (mobile scroll), PR2 (PWA install reliability), PR3 (default procedure catalog), PR4 (performance diagnostics & instrumentation).
- PR4 status: READY (backend Server-Timing, DB stmt/time/pool metrics, effective pool logger, frontend dev/staging route timing).
- Promotion to main: All 37 slices (S00–S36) complete. Blocked until staging smoke test and the mandatory stronger-model final review are done (DEVELOPMENT_WORKFLOW §6). Final review: PENDING.

## R1 Additions & Completion (feat/r1-completion-and-additions)
- F-17/F-18/F-11/F-05 fixes: plan overlay multi-surface counting, care session translations, safe interim tooth condition update, invoiced charge correction warnings/audits/notifications.
- Edit/reschedule/postpone appointments with conflict detection, concurrency checks, and dedicated UI modals.
- Medical alert badges on patient list and cards with distinct pregnancy warning indicator.
- Multi-tooth sequential procedure application with surface validation and partial-recovery in clinical chart.
- Backup diagnostics and tenant-scoped operational Excel export (.xlsx) with formula injection protection.
