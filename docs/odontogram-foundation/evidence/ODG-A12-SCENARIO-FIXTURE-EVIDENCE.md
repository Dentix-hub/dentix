# ODG-A12 / Issue #128 — Scenario Fixture Matrix Evidence

## Execution record

- Ticket: ODG-A12 / Issue #128
- Mode: HIGH_RISK after the explicitly approved mixed-dentition renderer-contract expansion
- Risk: `clinical-semantics`
- Execution: `SERIAL_ONLY`
- Protected baseline: `origin/staging@013090f53ca2d38c2d876d26baa1c3554ff69547`
- Scope remained frontend-only. No backend, API, schema, persistence, tenant, RBAC, finance, or geometry source was changed.
- The chart remains a projection/controller. Canonical tooth identity remains FDI.

## Acceptance disposition

- A12-M01 — PASS: 32-tooth permanent fixture renders.
- A12-M02 — PASS: 20-tooth primary fixture renders.
- A12-M03 — PASS: explicit 24-tooth mixed fixture renders permanent and primary anatomy in the governed FDI order.
- A12-M04 — PASS: distal caries renders on tooth 46 crown surface D only.
- A12-M05 — PASS: completed composite renders on tooth 46 M, O, and D surfaces.
- A12-M06 — PASS: completed RCT renders against tooth 46 mesial and distal roots.
- A12-M07 — PASS: completed prosthetic crown renders on tooth 36.
- A12-M08 — PASS: missing lifecycle renders on tooth 38.
- A12-M09 — PASS: tooth 23 implant fixture and crown render while natural roots are hidden.
- A12-M10 — PASS: 14-15-16 bridge units render with tooth 15 as the missing pontic.
- A12-M11 — PASS: completed composite and planned crown layers render simultaneously on tooth 46.

## Focused T1

Final command:

```text
npm.cmd test -- src/features/clinical-chart/tests/ClinicalChartRendererAdapter.test.jsx src/features/clinical-chart/tests/a12ScenarioFixtures.test.jsx
```

Final result: PASS — 2 files, 26 tests, 6.99 seconds.

Expanded clinical-chart command:

```text
npm.cmd test -- src/features/clinical-chart/tests
```

Result: PASS — 13 files, 114 tests, 26.64 seconds.

The mixed contract checks exact rendered order, canonical FDI selection intents for permanent tooth 21 and primary tooth 61, invalid-order rejection, and representative permanent/primary root anatomy.

## Visual evidence

- [Dentition matrix](./A12-dentition-matrix.png)
  - SHA-256: `940CE2879EA56DA69241BF797D4B0D6E7710E3E345570A1933EFC8F7E2396BE1`
- [Findings and treatment matrix](./A12-clinical-scenarios-1.png)
  - SHA-256: `7585AEFD1362E56FD4C91F37CE75E1D40B260C676FCDB8C5D91E2AB424043982`
- [Lifecycle, prosthetic, and layered matrix](./A12-clinical-scenarios-2.png)
  - SHA-256: `7AD8CBF6A296237E540C097651BD8F4EE9622F2135D31E007764FCD920BE41D2`

Playwright measurements from the local Vite rendering:

| Metric | Result |
|---|---:|
| Adult crowns | 32 |
| Primary crowns | 20 |
| Mixed crowns | 24 |
| Mixed dentition marker | `mixed` |
| 14-15-16 bridge units | 3 |
| Existing and planned layer groups | present |
| Document horizontal overflow | false |
| Browser console/page errors | 0 |

The repository's installed Playwright runtime captured the images. The in-app browser inspection path was unavailable because the Windows ACL bootstrap failed before connection; the saved screenshots and DOM measurements remain the review evidence.

## Independent HIGH_RISK review

Initial verdict: REWORK — one MEDIUM finding.

- Mixed tests originally compared key sets and did not prove exact layout order, permanent/primary event identity, or representative anatomy selection.

Remediation:

- Exact crown-key order now equals the explicit mixed `toothOrder`.
- Edit-mode clicks on permanent 21 and primary 61 assert exact canonical FDI intents.
- Permanent maxillary molar 26 asserts three base root paths; primary canine 63 asserts one.

Final independent verdict: CLEAN / HIGH_RISK PASS. Unresolved findings: zero.

## T2 frontend gate

- `npm.cmd run test` — PASS: 109 files, 508 tests, 278.88 seconds.
- `npm.cmd run lint` — PASS: zero lint errors or warnings.
- `npm.cmd run build` — PASS: 3,947 client modules and 2 service-worker modules transformed.

Baseline/new-failure classification:

- The first full-suite run had one `FinancePage.test.jsx` 5-second timeout under suite load (507 passes).
- The unchanged Finance test passed focused 3/3 in 1.60 seconds.
- The final full-suite run passed 508/508.
- Classification: transient test-load timeout, not an ODG-A12 regression.

Non-failing baseline output: jsdom cross-document navigation notices, stale `caniuse-lite`, and the Vite `inlineDynamicImports` deprecation warning.

## T3 boundary

T3 is required on the individual protected PR. It remains pending until the PR is opened and asynchronous required checks complete. Issue #129 remains blocked until #128 merges.
