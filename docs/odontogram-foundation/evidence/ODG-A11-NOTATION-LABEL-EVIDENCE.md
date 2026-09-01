# ODG-A11 / Issue #127 — Notation and Label Semantics Evidence

## Execution record

- Wave: ODG-L2
- Mode: HIGH_RISK
- Risk: `clinical-semantics`
- Execution: `SERIAL_ONLY`
- Protected baseline: `origin/staging@b8dd209bf19c7d74c89655052dfee5b6e5e141b1`
- Production rollout remains Palmer-only; no notation selector or workflow was added.
- The chart remains a projection/controller. Canonical tooth identity remains FDI and is never derived from a display label.

## Acceptance disposition

- A11-M01 — PASS: the exact legacy Palmer labels are verified for all adult Universal sources 1–32 and primary sources A–T after conversion to their 52 canonical FDI identities.
- A11-M02 — PASS: a frozen presentation registry supports Palmer, FDI, and Universal formatting while deriving every display from canonical FDI identity. Unsupported, inherited, null, and non-string modes are rejected.
- A11-M03 — PASS: notation labels render as an explicit sibling after the root/crown viewport, remain nowrap, and have no measured clipping, anatomy overlap, adjacent-label overlap, or identity mismatch.
- Root/crown geometry and renderer boundaries — PASS: `crownGeometry.js` and `rootGeometry.js` remain identical to the protected baseline.

## Focused T1

Command:

```text
npm.cmd run test -- src/features/clinical-chart/tests/chartNotation.test.js src/features/clinical-chart/tests/ClinicalChartRendererAdapter.test.jsx src/features/clinical-chart/tests/ClinicalChartWorkspace.test.jsx src/features/clinical-chart/tests/rootLayerRendering.test.jsx src/features/dental/DentalChartSVG.test.jsx
```

Authoritative result: PASS — 5 files, 54 tests, 9.97 seconds.

Failure and rework classification:

- First invocation did not start tests because the isolated worktree lacked `node_modules`. Lockfile-pinned dependencies were restored with `npm.cmd ci --prefer-offline --no-audit`; no manifest or lockfile changed.
- Initial implementation passed 53 focused tests.
- Independent review found one HIGH and two MEDIUM clinical-semantics findings. The first remediation run exposed an adult/primary source-type conversion defect: 9 failures, 45 passes. The map was corrected surgically.
- Final focused rerun passed 54/54.

## Visual evidence

- [Final Palmer desktop chart](./A11-notation-labels-desktop.png)
- SHA-256: `0DCF88859F530140F9125F99A9EB043B7053DD40F7D30C062C9DC760B5FA39A3`

Final Playwright measurements:

| Metric | Result |
|---|---:|
| Notation mode | `palmer` |
| FDI 11 label | `UR1` |
| Labels / roots / crowns | 32 / 32 / 32 |
| Label overlap pairs | 0 |
| Label/anatomy overlaps | 0 |
| Clipped labels | 0 |
| Label-to-anatomy identity mismatches | 0 |
| Document overflow | false |

The screenshot was visually inspected. The in-app browser runtime could not start because of a Windows sandbox bootstrap failure, so the repository's installed Playwright runtime captured and measured the same local Vite page.

## T2 frontend gate

- `npm.cmd run test` — PASS: 108 files, 493 tests, 182.65 seconds.
- `npm.cmd run lint` — PASS: zero lint errors or warnings.
- `npm.cmd run build` — PASS: 3,947 modules transformed; application build 2.23 seconds and service-worker build 0.911 seconds.
- Baseline-only non-failing output: jsdom cross-document navigation notices, stale `caniuse-lite`, and Vite `inlineDynamicImports` deprecation warning.

## Independent semantics review

Initial verdict: REWORK.

- HIGH: caller-supplied Universal source could contradict canonical FDI identity.
- MEDIUM: inherited object keys could pass notation-mode lookup.
- MEDIUM: initial all-52 Palmer compatibility test shared its formatter with production and was tautological.

All three findings were remediated and covered by focused tests. Final independent verdict: CLEAN / HIGH_RISK PASS. Unresolved findings: zero.

## T3 boundary

T3 is required on the individual protected PR. It remains pending until the PR is opened and asynchronous required checks complete.
