<!-- CLASSIFICATION: ACTIVE -->
# Care-session boundary corrections — 2026-10-31

Scope: the two confirmed findings in the review of `194bc91`, R4-01 and R4-02. **Both corrections are DONE locally.** This is not a claim of full-plan or staging acceptance. Work continues on the existing feature branch; PR #339 was already merged, and these local changes are preserved in a verified Git bundle.

## R4-01: bounded historical activity identity

Free-form historical activities now receive a server-owned identity through `backend/clinical/step_identity.py`. Complete display titles remain supported up to 255 characters. Short existing ASCII-derived identities remain compatible; long and non-Latin labels receive a bounded prefix plus a digest of the complete normalized Unicode label. Different long titles sharing the same prefix remain distinct, and repeating the same activity retains its identity and increments its occurrence.

Explicit valid identifiers are preserved, including template-defined `step_1` identifiers. The historical entry modal sends complete titles without deriving database identifiers in JavaScript. Historical steps are validated through their typed schema rather than falling back to unvalidated dictionaries. Invalid lengths/blank titles return validation errors; legacy code-only input still uses that code as its label.

No stored historical record is rewritten. No schema or migration change is needed. The existing 64-character identifier columns remain unchanged.

## R4-02: clinic-local calendar contract

The dashboard now sends `calendar_date_from` and `calendar_date_to` as `YYYY-MM-DD`. The authenticated clinic's persisted IANA timezone is resolved by the backend. Existing tenant-day helpers produce an inclusive start and exclusive next-local-midnight end in UTC. Both boundaries therefore follow the clinic calendar, including 23/25-hour days.

Existing `date_from`/`date_to` datetime filters remain exact instant bounds, including a literal midnight end. The former heuristic that guessed calendar intent from the hour component was removed. Calendar and datetime filters cannot be mixed in one request; ambiguous or reversed calendar ranges return 422. The route retains its existing permission and rollout gates, patient visibility and tenant scoping.

Frontend contract tests were updated to assert calendar-date parameters, rather than an invented UTC end-of-day timestamp. The prior clinical assertions remain covered by server and HTTP boundary tests; they were not weakened to allow a failing date range.

## Verification

Before implementation, the new regression file failed its 12 non-PostgreSQL cases; its PostgreSQL case failed with VARCHAR(64) truncation. After correction:

- **247 selected backend tests passed, zero skipped.** Selection covered the new boundary file, care-session v2/prior/service/resume/appointment suites, delivery integrity, clinical catalogue, archive, RBAC and tenant-time helpers.
- **39 final compatibility/boundary cases passed** after the final explicit-identity compatibility adjustment. These overlap the broader selection; do not add the counts together.
- **95 frontend tests passed across 16 files**, including complete-title submissions, dashboard calendar parameters, PatientDetails integration and existing session regressions.
- Configured Ruff, frontend ESLint, production/PWA/marketing build and PR-diff design guardrails passed.

The real PostgreSQL case preserves long titles with a common prefix, Arabic titles and a 255-character title, checks identifier bounds/distinctness, then repeats the visit to verify stable keys and incremented occurrences. It also preserves an explicit template-defined identifier. The delivery-integrity file's nine live PostgreSQL cases executed rather than being counted as skipped successes. All PostgreSQL data was synthetic in a disposable review cluster.

Calendar tests exercise both service and authenticated HTTP paths for Cairo in winter/summer, Riyadh, and New York's spring/autumn timezone transitions. They check the exact start, last microsecond and exclusive next-midnight boundaries. Additional tests retain exact-instant filtering, reject ambiguous/inverted ranges and retain legacy code-only historical input.

Commands:

```bash
TEST_DATABASE_URL='<disposable preflight-initialized PostgreSQL URL>' PYTHONPATH=. .venv/bin/pytest \
  backend/tests/test_care_workflow_boundaries.py \
  backend/tests/services/test_care_session_workflow_unification_v2.py \
  backend/tests/services/test_care_session_workflow_unification.py \
  backend/tests/services/test_care_session_service.py \
  backend/tests/services/test_care_session_resume_and_rct_scenario.py \
  backend/tests/services/test_care_session_appointment_integration.py \
  backend/tests/test_care_session_delivery_integrity.py backend/tests/test_clinical_catalog.py \
  backend/tests/test_tenant_archive.py backend/tests/test_rbac.py backend/tests/test_tenant_time.py \
  -o addopts='' -q --tb=short --show-capture=no --disable-warnings
.venv/bin/ruff check --config ruff.toml backend
# From frontend/:
npm test -- src/features/care-sessions/ src/features/templates/ src/features/appointments/FollowUpDashboard.test.jsx \
  src/tests/CareSessionDraftAutosave.test.jsx src/tests/CareSessionRctWorkflow.test.jsx \
  src/tests/CareSessionAppointmentIntegration.test.jsx src/tests/CareSessionDisabledNotice.test.jsx \
  src/tests/CareSessionResumeEngine.test.jsx src/tests/ContinueTreatmentMultiProcedure.test.jsx \
  src/tests/TreatmentHistoryCareSessions.test.jsx src/tests/ProcedureStatusControl.test.jsx \
  src/tests/NextVisitQueue.test.jsx src/tests/FollowUpManagement.test.jsx
npm run lint
npm run build
node scripts/check-design-system-guardrails.mjs --diff-base=origin/staging
```

Executed logs are under `/tmp/dentix-care-boundary-fix/` (`red.log`, `pg-red.log`, `backend-final.log`, `compat-final.log`, `frontend-final.log`, `lint.log`, `build.log`, `design.log`). These are targeted gates; full-plan validation and manual staging acceptance remain separate.

## Staging check, about five minutes

1. In a synthetic clinic with native clinical writes enabled, record a historical visit with two long activity titles sharing the same prefix and an Arabic title. Verify full titles in history and separate progress entries. Record the same activities in another historical visit and check occurrence continuity.
2. In a Cairo test clinic, create follow-up requests at 00:30 on November 30 and 00:30 on December 1. Filter November 30 through November 30. Only the first request should appear. Check one-sided date filters and pagination.
3. Through the test API, verify an explicit datetime range still uses exact instants; mixing datetime and calendar-date fields returns 422.
