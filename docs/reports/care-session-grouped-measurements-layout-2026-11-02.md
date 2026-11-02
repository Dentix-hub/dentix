# Grouped canal entry and patient/session layout

Status: implementation, visual review and local verification DONE. Remote CI and deployed staging acceptance remain pending.

## Confirmed defects and corrections

Before implementation, `WorkingLengthEntryTable.batch.test.jsx` reproduced the missing public action: the two-canal entry had no **Save canal measurements** button. Each row required a separate save. Existing observations were then rendered as compressed pills or raw structured JSON across the workspace, history and continuation surfaces. The fixed procedure strip also consumed most of a narrow visit dialog.

| Requested outcome | Result |
| --- | --- |
| Enter/save canals together | A single entry table and save action handles the entered canals. Length, file size, taper, root, tooth, reference and notes remain distinct for every canal. Unedited selected canals are optional. |
| Safe retry | Validate every entered row before the first write; disable concurrent saves; retain failed input and skip already successful records on retry. Finishing/closing the active workspace is blocked while its measurements are saving. |
| Complete readable saved information | A shared summary groups observations by procedure and tooth, with explicit length/file/taper columns and wrapping root/reference/notes. Legacy combined file values are displayed as separate size/taper without modifying stored records. Superseded records and reasoned amendment actions remain available under existing permissions. |
| Current and historical workflows | Both use the same entry and summary. Historical additions remain local until the visit is submitted; removed queued measurements can be added again. Current visits use the existing observation API. |
| Patient page | Patient actions and chart controls align in responsive grids. The active visit card wraps metadata and retains diagnostic-image access. Continuation displays its measurement group once, with notes separately expandable. |
| Visit dialog | One canonical close control; procedure selection/resources scroll with the content; procedure status remains editable for the selected procedure. Long titles wrap, and measurement inputs/numbers keep their direction in Arabic. |
| History and finish | The same complete measurement table appears in procedure breakdowns, the visit timeline and the finish sheet. Procedure history becomes labeled cards on mobile and remains a table on desktop. Arabic statuses and compact labels replace mixed display text. |

One user action still uses the existing individual observation requests. This is intentionally **not an atomic server batch**: successful records remain saved if a later request fails, and the entry sheet identifies unsaved input for retry. No new endpoint, schema, migration, rollout setting, role rule or clinical-history rewrite is introduced.

Terminology follow-up: the owner requested English clinical terms written phonetically in Arabic rather than anatomical Arabic translations. Roots, reference points, chart surface labels and treatment tooltips now use names such as ميزيال، ديستال، باكال، لينجوال، بالاتال and ميزيو باكال كاسب. Stored IDs, surface/canal codes, reference values and English resources remain unchanged. The follow-up passed 27 existing resource, Arabic-reader, summary and treatment-editor tests, plus ESLint and whitespace checks; logs: `/tmp/dentix-phonetic-terms/`.

CI follow-up: the [Frontend Tests job at `f5752c1`](https://github.com/Dentix-hub/dentix/actions/runs/41459521921/job/125324762782) failed in `ClinicalChartWorkspace.test.jsx` because its focus-isolation test still expected `بعيد (D)`. Local reproduction confirmed the same failure (1 failed, 6 passed). The expected display literal now matches the owner's requested `ديستال (D)`; the `46:D` selection, unaffected historical chart, inspector tooth and all other isolation assertions remain unchanged. Final verification passed **118 tests across 6 files**, targeted ESLint and whitespace checks (exit code 0). Logs: `/tmp/dentix-pr344-ci/`. Application code, CI configuration and test coverage requirements were not changed for this correction; fresh remote CI remains pending.

## Verification

- Baseline reproduction: one failing UI test, specifically unable to find the single save action. Sanitized evidence: `/tmp/dentix-session-layout/reproduction.log`.
- Final targeted UI suite: **122 passed across 19 files**, exit code 0. Coverage includes multi-canal payloads, preflight validation, partial failure/retry without duplicate writes, double-click protection, local removal/requeue, blocking finish during save, independent procedure state, read-only legacy records, amendment permissions, appointments, image access and patient actions.
- Synthetic Chromium browser: **8 passed**, exercising the real `PatientDetails` tree and session dialogs with intercepted HTTP responses and fictional data. Arabic light at 320/390/768/1440px, Arabic dark at 390/1280px, English light at 390/1440px. Each checks patient page, save-all payloads, finish sheet, expanded history, timeline and retrospective entry; no page errors or horizontal document/table clipping.
- ESLint (zero warnings), production/PWA/marketing build, diff design guardrails and whitespace checks passed. The final image-badge check preserved an existing feature; its assertion was retained. Formatting is confined to the new/reworked entry, summary and banner code.
- No backend implementation changed; existing observation endpoint contracts and server permission enforcement are used unchanged. The regression checks original input observations remain untouched by display.

UI command from `frontend/`:

```sh
npm test -- src/features/care-sessions/ src/tests/CareSessionRctWorkflow.test.jsx src/tests/CareSessionResumeEngine.test.jsx src/tests/TreatmentHistoryCareSessions.test.jsx src/tests/CareSessionAppointmentIntegration.test.jsx src/tests/ClinicalAttachmentViewers.test.jsx src/tests/PatientInfoCard.test.jsx src/tests/CareSessionDisabledNotice.test.jsx src/pages/PatientDetails.workspace.test.jsx src/pages/PatientDetails.chartRoots.test.jsx src/i18n.resources.test.js
npm run lint
npm run build
node scripts/check-design-system-guardrails.mjs --diff-base=origin/staging
```

Local logs, browser harness and screenshots: `/tmp/dentix-session-layout/` (`ui-verified.log`, `browser-final.log`, `lint-verified.log`, `build-verified.log`). Browser evidence is a synthetic UI check, not deployed staging acceptance or a production data test.

## Staging acceptance (about 10 minutes, fictional test patient)

1. Open an Arabic patient file on a phone. Check the patient buttons, chart controls, active session actions and wrapped long names. Open the visit workspace with several procedures selected and verify the form has useful scrolling space.
2. Choose an RCT procedure. Enter different lengths, file sizes, tapers and notes for MB and ML; add a custom canal if needed. Press **Save canal measurements** once and verify both full rows appear in one tooth group. Repeated clicking must not duplicate records.
3. Switch procedures and verify the tooth, pending entry and saved measurements stay with the correct procedure. Check the selected procedure's status control remains usable.
4. Open Finish Visit and inspect the full canal group and notes. Cancel without finalizing if the test visit is still needed.
5. Open history, expand a procedure's sessions, then switch to the visit timeline. Verify all fields and correction buttons, including an old combined MAF value, remain readable. Confirm the mobile cards and desktop table retain editing actions.
6. Record a historical visit: queue multiple canal measurements with one action, remove/re-add a queued measurement, then submit the visit once. Verify this does not create separate visits or interrupt the active visit.
7. Check dark mode, Arabic/English and narrow/desktop sizes. The document must not overflow horizontally; session controls and table values must remain readable.

Remote CI, merging and deployed staging acceptance remain separate from the local implementation results.
