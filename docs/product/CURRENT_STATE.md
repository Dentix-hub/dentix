<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Current State Card
Updated by the executor at the end of every task PR (max 10 lines changed). New Claude/Argon chats start from this file.

- Arabic UI polish (2026-10-30): password visibility and patient search controls occupy separate layout slots; remember-me has a larger pointer/keyboard target; quick-start checklist temporarily hidden on Dashboard.
- Revenue/status charts now lazy-load as complete charts so Recharts recognizes series/axes; zero-revenue and empty status data display explicit messages. Existing efficiency, financial values and APIs retained.
- Date picker uses Arabic months/weekdays/periods, Saturday-first RTL calendar and LTR numeric time grids; desktop RTL dialog stays centered. ISO date/month/datetime output unchanged.
- Verification: 44 targeted frontend + 5 existing server persistence/rotation/2FA tests PASS; 8 synthetic browser scenarios PASS (ar/en, 320/390/768/1440px, dark at 390px). Final lint/build/guardrails recorded in docs/reports/arabic-ui-polish-2026-10-30.md.
- Status: DONE locally on fix/arabic-ui-polish; no push, PR, deployment, schema change or live clinic-data change.

- Image backup blocker diagnostics: clinic-admin/SYSTEM_CONFIG-only GET /settings/backup/image-operations reports bounded active job/outbox metadata and incomplete attachment counts, scoped to the authenticated tenant; private/no-store, no patient fields, remote IDs, payloads, raw errors or tokens.
- Verification: 30 targeted diagnostics/archive/readiness/RBAC tests PASS; tenant contamination, role enforcement, read-only behavior, redaction and result bounds covered; Ruff/diff PASS. No queue edits, gate bypass, schema/config changes or deployment.
- Status: PARTIAL; image 404 alone does not identify the backup-blocking job. Staging diagnostic response is required before selecting a recovery action.

- Production archive history fix: exported copies explicitly disclose unresolved legacy treatment provenance only for completed, same-patient/tenant, matching-code procedures; restore reserves absent historical IDs without creating treatments or binding another clinic. Database events remain unchanged.
- Validation: production-snapshot replay now passes all archive compatibility stages for the affected clinic; unrelated attachment issues remain rejected. 84 archive regressions + 13 restricted-role PostgreSQL backup/restore checks PASS; Ruff/diff PASS.
- Drive status now distinguishes structured archive-data failures and reports configuration guidance safely. No migration, encryption-key change, production data repair or deployment. Status: DONE locally; staging and live provider acceptance pending.

- Production backup/chart regressions (2026-10-30): Optional patient age/phone now preserve NULL through export/preview/restore; guarded migration f3c4d5e6a7b8 relaxes only those constraints without rewriting records. Required-field validation remains strict.
- Mixed odontogram: Anatomical permanent-upper / primary-upper / primary-lower / permanent-lower rows retain all supplied teeth, original FDI identities, callbacks and existing single-dentition orientation; primary positions align with permanent successors.
- Verification: 150 backend PASS + 1 existing PostgreSQL-only trigger skip; 13 restricted-role PostgreSQL backup/restore PASS; 360 frontend PASS; 10 synthetic browser checks PASS (ar/en, 320–1440px, aligned/unclipped labels); lint/build/Ruff/guardrails PASS.
- Status: DONE locally; staging acceptance and live Google backup remain pending. No production database/configuration changes or deployment performed.
- PR #332 CI follow-up: application suites passed (1613 backend + 83 PostgreSQL); Safety blocked 12 advisories in locked PyJWT 2.13.0/oauthlib 3.3.1. Updated only those lock entries to 2.15.1/4.0.0; no policy exceptions or CI changes.
- Follow-up verification: frozen sync/lock check PASS; unchanged fail-closed Safety runner PASS (0 reported, existing exceptions retained); 60 auth/Google/RBAC/SDK/security tests PASS + 1 existing TestClient refresh skip. New JWT regression fails on old PyJWT and passes after update. Remote CI pending.

- Final cumulative production review (2026-10-30): technical PASS for main 1b7c1bd -> staging ebb98e4; acceptance recorded by protected review/merge of this review-record PR. Evidence and limits: docs/reports/production-release-review-2026-10-30.md.
- Gates: all final PR #329 CI jobs + exact staging smoke PASS; encrypted DB snapshot, 86-table application restoration and unchanged migration rehearsal PASS. Owner confirmed the one pre-existing local attachment is not required; its DB record is retained.
- Promotion preserves clinical flags and persistent keys; live SMTP/Google provider acceptance remains NOT VERIFIED. Refresh recovery snapshot near cutover; production has not been deployed.

- Lab cost/payment race (2026-10-30): Tenant-scoped PostgreSQL order locks now serialize cost edits with payment creation/allocation in HTTP and service paths; locked reads refresh cached order values. No migration or accounting formula change.
- Verification: regression failed on the prior code; 26 restricted-role PostgreSQL checks (both operation orders, four payment paths, independent orders, finance/RLS) + 77 lab/RBAC regressions PASS, 0 skipped; targeted Ruff and diff checks PASS.
- Status: DONE; PR #329 merged, final CI and exact staging deployment/smoke PASS. Production unchanged; final cumulative review recorded in the release report.

- Marketing visual redesign (2026-10-29): Arabic/English pages now use the app's sky/navy/teal palette, practical clinic-day copy, six actual React screenshots with fictional-data disclosures, self-hosted licensed Cairo, native image enlargement and responsive layouts. SEO, zero-JS public delivery and PWA exclusions retained.
- Verification: 65 targeted Vitest tests PASS; full marketing browser run 63 passed + 2 intentional no-JS skips; final visual/image checks 30 PASS; backend 39 passed + 1 existing refresh-tracking skip; build/lint/guardrails PASS; 120 precache entries. Status: DONE locally, awaiting visual review; no push/deployment.

- HF marketing routing fix (fix/hf-marketing-routes, 2026-10-29): Backend serves /ar and /en as static documents; trailing-slash/index.html aliases redirect 308 with query strings preserved; missing language/marketing/crawl resources return 404. Existing SPA, API and SW behavior preserved.
- Verification: 39 passed + 1 existing skip across marketing HTTP, security-header and auth-flow tests (refresh tracking unavailable in TestClient); targeted Ruff PASS. Status: DONE locally; not pushed/deployed; staging HTTP smoke required after delivery.

- Marketing & Discovery Batch 1 & 2 (feat/marketing-english-page, 2026-10-29): Standalone static landing pages in Arabic (/ar) and English (/en), isolated CSS with LTR/RTL support, WCAG AA contrast, bidirectional hreflang (ar, en, x-default), language switchers, sitemap with both URLs, SW/Vercel clean network bypasses, and dynamic Login discovery link.
- Verification: 158 frontend test files (1042 Vitest tests) PASS; Playwright marketing tests: 53 passed + 2 skipped across 5 viewport projects; full backend unit tests: 1569 passed + 5 skipped (0 failed); 0 lint warnings; 0 new design guardrail violations; 120 precache entries (2.76 MiB). Status: PARTIAL (local review approved; live Vercel & CI PostgreSQL runs pending).

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
- Promotion to main: All 37 slices (S00–S36) complete. Final cumulative technical review: PASS (docs/reports/production-release-review-2026-10-30.md); owner acceptance via protected review-record PR merge, then exact current staging smoke and normal protected promotion.

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
