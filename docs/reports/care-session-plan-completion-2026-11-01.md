# Care-session workflow: scope closure

This review covers the multi-visit procedure workflow and the five remaining requirements listed in the earlier delivery review. It continues the existing branch and reconciles the merged PR #339 staging history.

## Requirement accounting

| Requirement | Delivered behavior and entry point | Verification |
| --- | --- | --- |
| Multiple visits and inline procedure status | Continue Treatment / Resume All initializes procedure-specific steps. Visit completion and procedure completion remain separate. Status changes use optimistic versions, correction/override reasons and financial warnings. | Prior unification, resume/RCT, status-control and PatientDetails integration suites. |
| Generic visit workspace | Chart → Visit Workspace supports multiple procedures, separate notes/custom fields, steps/repeats/skips, prior context and RCT controls. Materials, protected images and laboratory handoff are reachable for the selected procedure. | GenericVisitWorkspace, CareSessionResources and PatientDetailsCareSessionIntegration; material/lab/attachment service tests. |
| Clinic template/custom-field editor | Settings → Workflow Templates provides ordered stages, typed fields, preview and immutable versions. New identifiers do not reuse removed stage/field identities, and reordering preserves the cached original definition. | WorkflowTemplateEditor and backend template/catalogue/integrity suites. |
| Populated specialty snapshots | Six canonical specialty families initialize snapshots. Template revisions/deactivation do not reinterpret definitions or values in recorded visits. | v2 and delivery-integrity snapshot/deactivation tests. |
| Historical entry and corrections | History → Record Past Visit supports actual date/provider, long/Arabic titles, and procedure-specific steps/measurements. Observation amendments preserve original values. Completed visit narratives accept dated, reasoned addenda with the original record retained. | Historical modal, amendment, boundary, completion and PostgreSQL archive tests. |
| Follow-up dashboard | Appointments → Follow-Ups offers visible-patient counts, search/filters, clinic-calendar ranges, pagination, scheduling and clinical follow-up actions. Requests retain procedure associations and optional explicit target dates. | Dashboard, appointment, visibility/RBAC and calendar/HTTP suites. |
| Recovery and clinical safety | Rollout gating and server permissions remain enforced. Both dashboard and reception queue respect doctor visibility. Failed flushes/measurement saves retain documentation; offline flushes reject completion. History displays saved custom values, original notes and corrections. | Authenticated endpoint, recovery/integration, locale-integrity and real PostgreSQL tenant/reference tests. |

All listed requirements have implementations; none is reclassified as deferred. Staging acceptance and protected CI remain separate delivery gates.

## Closure corrections

- Restored actual material consumption, protected image linking/viewing and existing lab handoff in the workspace. Stock caches refresh after confirmed usage; suggestions never consume stock.
- Replaced historical entry's implicit first-procedure assignment with explicit selection and prevented removal of a procedure while its documentation remains attached.
- Repaired the historical form/API contract: `provider_user_id` is accepted, validated as an active clinician in the clinic and stored separately from `recorded_by_user_id`. An authenticated HTTP test submits the form's complete steps/measurements/provider payload; foreign, inactive and non-clinician targets are rejected.
- Added visit-note addenda using existing `amends_session_id`/audit fields. They appear under the original visit, with actor/time/reason, and are excluded from the history visit count. PostgreSQL archive round trips remap both row and event references.
- Bound observation amendments to their route's visit, validated corrected FDI teeth, and distinguished clearing a target from leaving it unchanged. Original clinical values remain intact.
- Fixed finish-sheet closure on failed saves, retained rejected measurement notes, rejected offline finish flushes and isolated measurement forms across procedures.
- Displayed prior procedure notes/next actions, non-RCT observations and saved specifications in workspace/history. Follow-up requests retain associated procedures and support an optional target date without booking an appointment.
- Matched dashboard actions to permissions, hid unauthenticated clinical actions, and closed the older reception queue's restricted-doctor visibility gap. Cancelled requests do not inflate overdue counts.
- Completed Arabic/English resources and corrected template identifier reuse and cached-definition mutation.

No schema or previously committed migration is changed by these closure corrections. Existing additive migration and boundary fixes remain in the cumulative branch.

## Verification

Status: **DONE for implementation, local review and verification**. Protected CI and owner staging acceptance remain pending.

| Executed gate | Result |
| --- | --- |
| Final frozen-code full backend suite | **1,758 passed, one existing skip, zero failures/errors**; JUnit confirms 1,759 collected cases. Real PostgreSQL enabled. |
| Coverage-gated full closure run | **1,756 passed, one existing skip; 79.53% coverage**, exceeding the configured 52%. This precedes the final two provider-contract tests, which are included in the final full run above. |
| Final frozen-code full frontend suite | **1,116 passed across 172 files**, zero failures/skips. |
| Completion/provider/real-PostgreSQL archive selection | **11 passed**, overlapping the full backend run. |
| Configured backend Ruff, frontend ESLint, production/PWA/marketing build | **PASS**, real exit codes 0. |
| PR-diff design guardrails and whitespace checks | **PASS**, zero new guarded violations. |

The last two full suites ran after the implementation was frozen. Selected-test counts overlap; they are not added to full-suite totals. The environment reconciliation and an earlier coverage run are separately described below.

Reproduction commands (substitute a disposable, preflight-initialized PostgreSQL URL):

```bash
uv sync --frozen
TEST_DATABASE_URL='<disposable PostgreSQL URL>' PYTHONPATH=. .venv/bin/pytest backend/tests/ \
  --no-cov -o addopts='' -q --tb=short --maxfail=0 --show-capture=no -rs
.venv/bin/ruff check --config ruff.toml backend
# From frontend/:
npm test -- --reporter=dot
npm run lint
npm run build
node scripts/check-design-system-guardrails.mjs --diff-base=origin/staging
```

Executed logs/JUnit/coverage are under `/tmp/dentix-care-final-completion/`: `backend-head.log`, `backend-head.xml`, `backend-full-final.log`, `coverage-final.xml`, `frontend-head.log`, `provider-http.log`, `lint-verified.log`, `build-verified.log`, and `design-verified.log`.

The first full backend run exposed environment drift: installed urllib3 2.7.0 and PyJWT 2.13.0 differed from the existing lock's 2.8.0 and 2.15.1. `uv sync --frozen` reconciled the environment without changing the lock or assertions. The subsequent coverage gate passed **1,756 tests, one existing skip, 79.53% coverage** against the configured 52% threshold. The final-head run additionally includes the two provider-contract regressions; counts overlap and must not be added together.

The existing skip is `test_auth_flow.py`'s refresh check: `request.client.host` is unavailable with that TestClient fixture; real PostgreSQL session/refresh coverage remains in the project. No PostgreSQL cases are represented as skipped successes. Early frontend runs, including the run that loaded the pre-fix stock-cache module, are not counted as passed full runs.

## Staging acceptance, approximately 12–15 minutes

Use synthetic patients and stock in a disposable test clinic with native clinical writes enabled.

1. Open active RCT and restorative procedures, resume both, and switch between them. Enter notes/specifications and save a canal measurement. Confirm inputs do not cross procedures. Record a known available material, link a synthetic radiograph and open the lab handoff for the selected procedure.
2. Finish with a follow-up reason/date. Start another visit and verify prior notes, next action and measurements. Change overall procedure status inline; incomplete work still requires justification and invoiced work retains its financial-review warning.
3. Revise a template and inspect its preview. Verify the completed visit retains its original fields/values. Disable the template and confirm it is not resurrected for a new visit.
4. Record a past multi-procedure visit with an Arabic/long title and a step/measurement assigned to the second procedure. Correct a measurement and add a visit-note correction with reasons. Verify original and replacement documentation/actor/time remain visible.
5. Filter Follow-Ups by doctor, procedure and clinic date; test pagination with seeded data. As reception, verify scheduling while clinical management is hidden/denied. As a restricted doctor, verify dashboard and queue both omit hidden patients.
6. Type notes, allow autosave and reopen. Offline finalization must retain the sheet/notes; reconnect and finish. Inspect Arabic at a narrow viewport. Disable the rollout flag and verify the new server routes deny access.

Do not restore a real clinic for this smoke test. Automated archive round trips use disposable PostgreSQL only. No merge, promotion or deployment is included.
