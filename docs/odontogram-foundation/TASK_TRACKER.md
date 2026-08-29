# Odontogram Foundation Task Tracker

Status values: `PENDING`, `IN PROGRESS`, `PASS`, `BLOCKED`, `ACCEPTED DEVIATION`.

| Micro-task | Status | Evidence / note |
| --- | --- | --- |
| A0-M01 Revalidate current main | PASS | `BASELINE_DRIFT_REPORT.md`; fetched `origin/main@89d67010` |
| A0-M02 Create execution docs folder | PASS | Required four files plus drift report created |
| A0-M03 Record baseline metadata | PASS | `README.md`; committed in `c0e27897` |
| A0-M04 Create explicit scope lock note | PASS | `README.md`; committed in `c0e27897` |
| A1-M01 Write chart direction ADR | PASS | `ADR-001-CHART-DIRECTION.md` |
| A1-M02 Define chart architectural layers | PASS | ADR “Architectural layers” and data-flow sections |
| A1-M03 Define renderer non-responsibilities | PASS | ADR “Renderer non-responsibilities” section |
| A1-M04 Define future readiness targets | PASS | ADR “Future-readiness targets” section |
| A2-M01 Create feature directory | PASS | `frontend/src/features/clinical-chart/` |
| A2-M02 Create subfolders | PASS | `components`, `domain`, `rendering`, `fixtures`, `hooks`, `tests` |
| A2-M03 Create entry workspace component | PASS | Component test: 1/1 passed; frontend lint passed |
| A2-M04 Create temporary demo route | PASS | DEV-only `/clinical-chart/demo`; browser DOM verified with zero console errors |
| A3-M01 Create anatomy registry file | PASS | `domain/dentalAnatomyRegistry.js` exports immutable registry and lookup |
| A3-M02 Define anatomy model shape | PASS | JSDoc contract covers every required field; 10/10 focused tests passed |
| A3-M03 Define permanent dentition keys | PASS | All 32 permanent FDI positions represented and tested |
| A3-M04 Define primary dentition keys | PASS | All 20 primary FDI positions represented and tested |
| A3-M05 Define mixed-dentition compatibility note | PASS | `MIXED_DENTITION_COMPATIBILITY.md` |
| A4-M01 Inventory current crown outlines | PASS | `CROWN_OUTLINE_INVENTORY.md` |
| A4-M02 Normalize crown shape access | PASS | All 52 anatomy keys resolve; 20/20 focused chart tests passed |
| A4-M03 Preserve current visual style | PASS | Exact source-path equality test plus `evidence/A4-crown-parity.png`; zero browser errors |
| A5-M01 Create root outline model | PENDING | — |
| A5-M02 Add single-root anterior definitions | PENDING | — |
| A5-M03 Add premolar root definitions | PENDING | — |
| A5-M04 Add molar root definitions | PENDING | — |
| A5-M05 Add primary tooth root definitions | PENDING | — |
| A5-M06 Keep root style visually aligned | PENDING | — |
| A6-M01 Create surface code constants | PENDING | — |
| A6-M02 Define per-tooth clickable surface geometry | PENDING | — |
| A6-M03 Support anterior surface model | PENDING | — |
| A6-M04 Support posterior surface model | PENDING | — |
| A6-M05 Add hover/focus/selected states | PENDING | — |
| A7-M01 Create renderer adapter interface | PENDING | — |
| A7-M02 Define input DTO contract | PENDING | — |
| A7-M03 Define output interaction intents | PENDING | — |
| A7-M04 Prevent persistence leakage | PENDING | — |
| A8-M01 Create demo DTO schema | PENDING | — |
| A8-M02 Define tooth visual state shape | PENDING | — |
| A8-M03 Define target subshape | PENDING | — |
| A8-M04 Add sample DTO fixtures | PENDING | — |
| A9-M01 Create visual rule registry file | PENDING | — |
| A9-M02 Add lifecycle rules | PENDING | — |
| A9-M03 Add finding rules | PENDING | — |
| A9-M04 Add procedure rules | PENDING | — |
| A9-M05 Add layer mapping | PENDING | — |
| A10-M01 Add root layer renderer | PENDING | — |
| A10-M02 Handle single-root teeth | PENDING | — |
| A10-M03 Handle premolars | PENDING | — |
| A10-M04 Handle molars | PENDING | — |
| A10-M05 Handle primary teeth | PENDING | — |
| A10-M06 Prevent root overlap artifacts | PENDING | — |
| A11-M01 Support current notation display mode | PENDING | — |
| A11-M02 Add notation abstraction | PENDING | — |
| A11-M03 Verify label placement after roots | PENDING | — |
| A12-M01 Create adult dentition fixture | PENDING | — |
| A12-M02 Create primary dentition fixture | PENDING | — |
| A12-M03 Create mixed dentition fixture | PENDING | — |
| A12-M04 Create caries-on-surface fixture | PENDING | — |
| A12-M05 Create MOD restoration fixture | PENDING | — |
| A12-M06 Create RCT fixture | PENDING | — |
| A12-M07 Create crown fixture | PENDING | — |
| A12-M08 Create missing tooth fixture | PENDING | — |
| A12-M09 Create implant fixture | PENDING | — |
| A12-M10 Create bridge fixture | PENDING | — |
| A12-M11 Create simultaneous existing + planned fixture | PENDING | — |
| A13-M01 Create dual-chart page | PENDING | — |
| A13-M02 Ensure state isolation | PENDING | — |
| A13-M03 Ensure independent layer filtering | PENDING | — |
| A13-M04 Ensure read-only multi-instance support | PENDING | — |
| A14-M01 Create chart shell header | PENDING | — |
| A14-M02 Create simple legend | PENDING | — |
| A14-M03 Create simple inspector panel | PENDING | — |
| A14-M04 Create simple selection summary | PENDING | — |
| A14-M05 Keep UI intentionally simple | PENDING | — |
| A15-M01 Verify chart on desktop | PENDING | — |
| A15-M02 Verify chart on tablet width | PENDING | — |
| A15-M03 Verify chart on mobile width | PENDING | — |
| A15-M04 Add quadrant-friendly mobile behavior | PENDING | — |
| A15-M05 Verify Arabic RTL layout | PENDING | — |
| A15-M06 Verify English LTR layout | PENDING | — |
| A15-M07 Add keyboard focus states | PENDING | — |
| A15-M08 Add accessible labels where practical | PENDING | — |
| A16-M01 Add anatomy registry coverage test | PENDING | — |
| A16-M02 Add renderer smoke test | PENDING | — |
| A16-M03 Add multi-instance isolation test | PENDING | — |
| A16-M04 Add root visual regression evidence | PENDING | — |
| A16-M05 Add mixed dentition render test | PENDING | — |
| A16-M06 Add RTL render test | PENDING | — |
| A16-M07 Add mobile render test if tooling allows | PENDING | — |
| A17-M01 Capture desktop screenshots | PENDING | — |
| A17-M02 Capture mobile screenshots | PENDING | — |
| A17-M03 Capture RTL screenshots | PENDING | — |
| A17-M04 Capture history-compare screenshots | PENDING | — |
| A17-M05 Write Codex completion report | PENDING | — |
| A17-M06 Write handoff package for Gemini | PENDING | — |
| A17-M07 Hard stop | PENDING | — |
