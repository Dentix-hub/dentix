<!-- CLASSIFICATION: ACTIVE -->
# Session recording: native-write availability

Status: PARTIAL for the reported staging incident. UI correction and local verification are complete; the affected clinic's runtime configuration has not been inspected or changed. There is no claim of a successful save on the deployed clinic.

## Confirmed cause

The screenshot's exact message, `Clinical native writes are disabled`, is returned by `CareSessionService.ensure_native_writes_enabled()` before session creation when the effective `clinical_vnext_native_writes` decision is false. It does not report invalid canal lengths, taper, or missing notes. The effective decision includes the clinic override and global rollout policy.

`PatientDetails` already discovers that decision from `/settings/features`, but did not pass it to `TreatmentHistory`. History exposed recording to doctors based on permission alone. A failing UI regression reproduced that enabled button with native writes explicitly disabled. A second red regression reproduced the raw error and missing recovery path after a server-side rejection.

Investigation used the installed Superpowers `systematic-debugging` skill. The installed AI Hero catalog does not contain an independent debugging skill. Evidence was gathered before implementation; the server's rollout enforcement remains intact.

## Change

- Pass the effective tenant availability into history. Native session retrieval and clinical follow-up/correction actions honor availability; recording stays disabled until enabled. Existing treatment rows and supplied visit history remain readable.
- Explain unavailability in Arabic/English and offer a read-only availability refresh through the existing tenant-feature query.
- If the server disables native writes while the form is open, retain its entered documentation, show localized activation guidance, and require a successful availability recheck before resubmission. Closing the form is not advertised as durable draft persistence.
- No server authorization, rollout configuration, schemas, migrations, clinical records, or global clinic policy changed.

## Executed verification

Commands ran from the repository root unless the frontend directory is specified. All final commands below exited 0.

```text
PYTHONPATH=. .venv/bin/pytest backend/tests/test_care_session_feature_discovery.py -o addopts='' -q --tb=short --show-capture=no
2 passed. The authenticated session POST returns 404 and creates no row when disabled; the identical payload returns 201 after the synthetic tenant's flag is enabled. Existing multi-canal history/continuation/amendment preservation also passes.

cd frontend
npm test -- src/tests/TreatmentHistoryCareSessions.test.jsx src/features/care-sessions/HistoricalCareSessionModal.test.jsx src/features/care-sessions/GenericVisitWorkspace.test.jsx src/features/care-sessions/CareSessionAddendum.test.jsx src/features/care-sessions/PatientDetailsCareSessionIntegration.test.jsx src/i18n.resources.test.js
42 passed across 6 files; no skipped tests. Includes enabled/disabled real patient-page entry points, reception role restrictions, retained visit corrections, pending measurement capture, and recovery after a late server rejection.

npm run lint
npm run build
node scripts/check-design-system-guardrails.mjs --diff-base=origin/staging

cd ..
.venv/bin/ruff check --config ruff.toml backend/tests/test_care_session_feature_discovery.py
git diff --check
```

Initial integration-test execution exposed JSDOM's absent `scrollIntoView`; the test supplies that browser-method stub. No production behavior or assertion was weakened. Backend execution reported existing Pydantic deprecations and a tracer shutdown logging warning, with exit 0.

## Runtime completion and staging acceptance

The affected clinic's identity and authenticated administrative runtime access are missing. A targeted clinic lookup was requested; no production database connection or administrative session was available. Do not infer the clinic from a screenshot or enable every clinic globally.

1. Identify the affected clinic. An authorized super-admin can inspect `GET /api/v1/admin/features/tenant/{tenant_id}/clinical_vnext_native_writes` or `GET /api/v1/admin/clinical-rollout/{tenant_id}/status`.
2. If the clinic is intended to record native sessions, use the existing super-admin Feature Manager's clinic override for `clinical_vnext_native_writes`, or its authenticated `/api/v1/admin/features/override` endpoint. Full rollout-mode changes have wider effects and require a separate deliberate choice. No new permission or bypass is introduced here.
3. In that clinic's doctor session, confirm `/api/v1/settings/features` includes the native key; use Check again. Record one synthetic visit and verify its measurements/notes appear once in history.
4. In a deliberately disabled test clinic, confirm recording cannot open and legacy history remains visible. For a form opened before a flag change, confirm rejection retains entered notes and rechecking does not submit a write automatically.
5. Staging manual acceptance and the affected clinic's successful save remain outstanding. Do not mark the incident DONE based only on a disabled button or local tests.
