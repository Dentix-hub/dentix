# ODG-A16 Odontogram Part I Regression Gate Evidence

Status: **PASS**

## Scope

- Final Part I automated and visual regression consolidation gate across A10–A15.
- Complete contract validation: Anatomy Registry exhaustive coverage, Generic Renderer Smoke Gate, Multi-Instance Isolation, Root Geometry Snapshots, Mixed Dentition Render, RTL/LTR Layout, and Mobile Quadrant Navigation.
- Full frontend regression gate (canonical test runner, canonical lint, production build, Playwright browser suite).
- Production-code changes: **NO (ZERO)**.

---

## Acceptance Matrix

| Milestone | Description | Coverage Type | Disposition | Evidence / Test |
| --- | --- | --- | --- | --- |
| **A16-M01** | Anatomy registry exhaustive contract | **New** | **PASS** | `a16RegressionGate.test.jsx` (54 tests: 2 collection-level uniqueness/count tests, 52 FDI schema validation tests, and root geometry matching) |
| **A16-M02** | Renderer smoke test | **New** | **PASS** | `a16RegressionGate.test.jsx` (12 tests: 1 fixture count test, 11 scenario fixtures rendered and unmounted cleanly) |
| **A16-M03** | Multi-instance isolation | **Existing** | **PASS** | `ClinicalChartWorkspace.test.jsx` (7 tests: focus selection, root filter, clinical layer, inspector isolation) |
| **A16-M04** | Root geometry regression snapshots | **New** | **PASS** | `a16RegressionGate.test.jsx` + snapshot file (7 tests: representative teeth 11, 14, 16, 36, 51, 55, 85) |
| **A16-M05** | Mixed dentition render test | **Existing** | **PASS** | `a12ScenarioFixtures.test.jsx` (24-tooth mixed FDI order, permanent 26 3-root, primary 63 1-root) |
| **A16-M06** | RTL render test | **Existing** | **PASS** | `ClinicalChartWorkspace.test.jsx` (default Arabic RTL `dir="rtl"`, `lang="ar"`, English LTR toggle) |
| **A16-M07** | Mobile render test | **Existing** | **PASS** | `ClinicalChartWorkspace.test.jsx` (4 quadrant buttons, scroll-into-view, focus rings) + `e2e/odontogram-part1.spec.ts` (390x844 mobile viewport) |

---

## Test Verification

### 1. Targeted A16 Test Gate

Command:
```powershell
node_modules\.bin\vitest.cmd run --reporter=verbose src/features/clinical-chart/tests/a16RegressionGate.test.jsx
```

Exact Test Arithmetic:
- **A16-M01 (Anatomy Registry):** 54 tests
  - 1: 32 permanent and 20 primary count without overlap
  - 1: unique surface geometry refs and unique root outline refs
  - 52: complete anatomy schema validation per FDI tooth (11..48, 51..85) + root geometry matching
- **A16-M02 (Renderer Smoke Gate):** 12 tests
  - 1: 11 scenario fixtures available
  - 11: generic render without throw and clean unmount per fixture
- **A16-M04 (Root Geometry Snapshots):** 7 tests
  - 7: stable geometry contract snapshots (teeth 11, 14, 16, 36, 51, 55, 85)
- **Total targeted tests:** **73 passed** (54 + 12 + 7 = 73)
- **Snapshots:** 7 written / matched
- **Duration:** 2.23s
- **Exit code:** 0

### 2. Clinical Chart Subsystem Suite

Baseline before A16:
- **Test Files:** 13 passed (13)
- **Tests:** 119 passed (119)

Result after A16:
```powershell
node_modules\.bin\vitest.cmd run src/features/clinical-chart/tests/
```
- **Test Files:** 14 passed (14)
- **Tests:** 192 passed (192)
- **Failures:** 0
- **Duration:** 25.41s
- **Exit code:** 0

### 3. Full Frontend Test Suite (Canonical `npm test`)

Command:
```powershell
npm.cmd test
```

Result:
- **Test Files:** 110 passed (110)
- **Tests:** 586 passed (586)
- **Failures:** 0
- **Duration:** 205.69s
- **Exit code:** 0
- **FinancePage Timeout Status:** Not reproduced; passed cleanly (`✓ src/pages/admin/FinancePage.test.jsx (3 tests) 1081ms`).

### 4. Full Frontend Lint (Canonical `npm run lint`)

Command:
```powershell
npm.cmd run lint
```

Result:
- `eslint . --ext js,jsx --report-unused-disable-directives --max-warnings 0`
- **Errors:** 0
- **Warnings:** 0
- **Exit code:** 0

### 5. Full Frontend Production Build

Command:
```powershell
node_modules\.bin\vite.cmd build
```

Result:
- **Status:** Succeeded (`✓ built in 12.57s`, `PWA precache 117 entries generated`)
- **Exit code:** 0

### 6. Playwright Browser Matrix

Command:
```powershell
$env:ODONTOGRAM_URL="http://127.0.0.1:5173/clinical-chart/demo"
node_modules\.bin\playwright.cmd test e2e/odontogram-part1.spec.ts --no-deps
```

Result:
- **Tests:** 3 passed (3)
  - `desktop Arabic RTL comparison is usable (1440x1000)`: PASS
  - `tablet English LTR comparison is usable (768x1024)`: PASS
  - `mobile Arabic layout exposes quadrant navigation and keyboard focus (390x844)`: PASS
- **Visual evidence captured:**
  - `docs/odontogram-foundation/evidence/A15-desktop-ar-rtl.png`
  - `docs/odontogram-foundation/evidence/A15-tablet-en-ltr.png`
  - `docs/odontogram-foundation/evidence/A15-mobile-ar-rtl.png`
- **Document overflow:** 0px (verified across all three viewports)

---

## Changed Files Summary

1. `frontend/src/features/clinical-chart/tests/a16RegressionGate.test.jsx` (New test file)
2. `frontend/src/features/clinical-chart/tests/__snapshots__/a16RegressionGate.test.jsx.snap` (New snapshot file)
3. `docs/odontogram-foundation/TASK_TRACKER.md` (Updated A16 milestones to PASS)
4. `docs/odontogram-foundation/evidence/ODG-A16-REGRESSION-GATE-EVIDENCE.md` (This evidence artifact)

Production code modified: **ZERO**
