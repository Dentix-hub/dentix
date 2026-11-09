# Session rollout discovery, multiple canals and master file taper

Status: implementation and local verification DONE. Remote CI and deployed staging acceptance remain pending.

## Findings and resulting behavior

The previous UI correction only hid legacy session creation when the browser detected native writes. `/settings/features` returned explicit tenant settings but omitted the effective global `clinical_vnext_native_writes` rollout. A clinic could therefore use the native session API while its treatment editor displayed the legacy form. Feature discovery now uses the same feature service as the native APIs, including explicit tenant opt-out. No rollout setting is changed.

Treatment editing opens unified visits when native writes are available. The old inline notes/date/save-session form is removed regardless of flag discovery; existing legacy session records remain read-only and legacy API contracts remain available. A disabled native rollout still denies native writes.

The historical-visit dialog was already the new retrospective workflow, but only exposed a generic single-measurement entry. Selecting an RCT procedure now opens the existing canal selector and working-length editor. Doctors can select several anatomical canals or add custom canals, queue a distinct measurement for each, and record the historical visit once. Tooth and procedure identity remain attached to each measurement. Custom-canal entry is safe inside the outer visit form, including the Enter key.

Master file size and taper are independent inputs in both current and historical visits. Optional taper is a positive numeric value, stored in the existing observation JSON with length, reference point, file size, canal and root. History, continuation, visit summaries and correction forms display it. Legacy combined values such as `#25 / .04` remain readable; the correction editor separates the fields when creating a reasoned amendment. Original records remain unchanged. No database migration is needed.

Newly exposed canal controls have Arabic root/reference labels while preserving the original stored clinical codes and reference values.

## Verification

All commands below completed with exit code 0 for their final stated selection:

| Gate | Evidence |
| --- | --- |
| Backend feature discovery, care-session services, continuation/RCT, v2 workflow and RBAC | 73 passed, 0 skipped. Includes global-only native rollout, explicit tenant opt-out, two canals with different sizes/tapers, continuation, summary and immutable amendment checks. |
| UI subsystem | 100 passed across 13 files, including Arabic labels, current/historical multi-canal entry, parent-handler integration, taper corrections and read-only legacy history. |
| Synthetic Chromium browser | Passed at 390px and 1280px in Arabic: queued two canal measurements, submitted their separate tapers, added a custom canal without submitting the visit, retained read-only legacy records, and opened unified visits. No page errors or horizontal document overflow. Local fixture data and intercepted API responses; this is not deployed staging acceptance. |
| Static and build | Targeted backend Ruff, frontend ESLint with zero warnings, production/PWA/marketing build, diff-based design guardrails and whitespace checks passed. |

Backend selection, from repository root:

```sh
PYTHONPATH=. .venv/bin/pytest backend/tests/test_care_session_feature_discovery.py backend/tests/services/test_care_session_service.py backend/tests/services/test_care_session_resume_and_rct_scenario.py backend/tests/services/test_care_session_workflow_unification_v2.py backend/tests/test_rbac.py -o addopts='' -q --tb=short --show-capture=no
```

UI selection, from `frontend/`:

```sh
npm test -- src/features/care-sessions/ src/tests/CareSessionRctWorkflow.test.jsx src/tests/CareSessionResumeEngine.test.jsx src/tests/TreatmentHistoryCareSessions.test.jsx src/features/clinical-chart/tests/QuickTreatmentSheet.unified.test.jsx src/features/clinical-chart/tests/QuickTreatmentSheetAndPayload.test.jsx src/i18n.resources.test.js
npm run lint
npm run build
node scripts/check-design-system-guardrails.mjs --diff-base=origin/staging
```

Execution logs and synthetic browser screenshots: `/tmp/dentix-canal-taper-fix/`. Final frontend acceptance: `ui-final-verified.log`; backend: `backend-final.log`; browser: `browser.log`. No behavior assertion was removed or weakened to hide a failure. The former legacy-create test now asserts the explicitly requested read-only replacement.

## Staging acceptance path (about 10 minutes)

1. In a clinic whose native rollout is enabled globally without a tenant override, reload the Arabic patient page. Edit a treatment and verify the unified visit button appears and the old inline Add/Save Session form does not. Existing old notes remain readable.
2. Open Record Past Visit, select a single-tooth RCT procedure, and verify its tooth fills automatically. Select MB and ML, then add a custom canal such as MM. Adding the canal with Enter must not submit the visit.
3. Enter different lengths, file sizes and tapers, for example MB `20 / #25 / 0.04` and ML `21 / #30 / 0.06`. Save each measurement, record the visit, and verify history retains both canal identities and tapers. These are test values, not treatment recommendations.
4. Resume the procedure in a current visit. Verify carried measurements and taper display. Record another canal and finish the visit; verify its history/summary includes taper.
5. Correct a taper with a reason. Verify the effective value changes in subsequent reads while the original measurement remains in the audit trail. Also open a legacy combined MAF value and verify its correction fields separate size and taper.
6. Using an already disabled clinic/test fixture, verify native writes remain disabled and the treatment editor does not revive the old creation form. No production flag changes are required for this test.

No clinic data repair, schema change, financial change, remote merge or deployment was performed as part of implementation.
