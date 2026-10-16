<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Odontogram & Clinical VNext Implementation Status

**Authority:** `docs/engineering/DEVELOPMENT_WORKFLOW.md`  
**Classification:** `ACTIVE`  
**Last Updated:** 2026-10-16 (Post Slice 3)  
**Status Reference Invariant:** This document is the single authoritative implementation status reference for all Odontogram Foundation (A0–A17) and Clinical VNext (G0–G16) phases across DENTIX, updated incrementally per slice.

---

## 1. Status Summary

- **Total Phases Tracked:** 35 (A0–A17, G0–G16)
- **DONE:** 26 phases (A0–A17, G0–G6)
- **PARTIAL:** 4 phases (G7, G8, G9, G16)
- **SCHEMA_ONLY:** 3 phases (G10, G11, G15)
- **NOT_STARTED:** 2 phases (G12, G13, G14)

---

## 2. Phase-by-Phase Implementation Status Ledger

| Phase | Phase Title | Status | Evidence (File[:line], Tests, PR) |
|---|---|:---:|---|
| **A0** | Baseline Revalidation and Freeze | **DONE** | `docs/odontogram-foundation/evidence/`, `docs/engineering/DEVELOPMENT_WORKFLOW.md`, PR #222 |
| **A1** | Final Chart Architecture Lock | **DONE** | `PROJECT_STANDARDS.md:Section 5`, `docs/engineering/CLINICAL_CHART_DISPOSITION.md`, PR #222 |
| **A2** | Frontend Chart Module Scaffold | **DONE** | `frontend/src/features/clinical-chart/` module tree, `tests/smoke.test.jsx`, PR #222 |
| **A3** | Anatomy Registry Foundation | **DONE** | `frontend/src/features/clinical-chart/domain/dentalAnatomyRegistry.js:1-120`, `dentalAnatomyRegistry.test.js`, PR #222 |
| **A4** | Crown Outline Integration | **DONE** | `frontend/src/features/clinical-chart/rendering/crownGeometry.js:1-90`, `crownGeometry.test.js`, PR #222 |
| **A5** | Root Anatomy Definition | **DONE** | `frontend/src/features/clinical-chart/rendering/rootGeometry.js:1-110`, `rootGeometry.test.js`, PR #222 |
| **A6** | Surface Geometry Foundation | **DONE** | `frontend/src/features/clinical-chart/rendering/surfaceGeometry.js:1-85`, `surfaceGeometry.test.js`, PR #222 |
| **A7** | Renderer Contract | **DONE** | `frontend/src/features/clinical-chart/rendering/ClinicalChartRendererAdapter.js:1-241`, `ClinicalChartRendererAdapter.test.jsx`, PR #222 |
| **A8** | Projection DTO for Demo Use | **DONE** | `frontend/src/features/clinical-chart/domain/clinicalChartProjection.js:1-115`, `clinicalChartProjection.test.js`, PR #222 |
| **A9** | Visual Rule Registry | **DONE** | `frontend/src/features/clinical-chart/domain/visualRuleRegistry.js:1-150`, `visualRuleRegistry.test.js`, PR #222 |
| **A10** | Root Layer Rendering | **DONE** | `frontend/src/features/dental/DentalChartSVG.jsx:398-460`, `features/clinical-chart/tests/rootLayerRendering.test.jsx`, PR #222 |
| **A11** | Notation and Labels | **DONE** | `frontend/src/features/clinical-chart/domain/chartNotation.js:1-90`, `chartNotation.test.js`, PR #222 |
| **A12** | Demo Clinical Scenarios | **DONE** | `frontend/src/features/clinical-chart/fixtures/a12ScenarioFixtures.js:1-200`, `workspaceSnapshotAdapter.test.js`, PR #222 |
| **A13** | Multi-Instance and History Compare | **DONE** | `frontend/src/features/clinical-chart/components/ClinicalChartComparisonCard.jsx:1-80`, `a16RegressionGate.test.jsx`, PR #222 |
| **A14** | Basic UI Layer | **DONE** | `frontend/src/features/clinical-chart/components/ClinicalChartWorkspace.jsx:1-100`, `ClinicalChartInspector.jsx`, PR #222 |
| **A15** | Mobile, RTL, and Accessibility | **DONE** | `frontend/src/features/clinical-chart/components/ClinicalChartWorkspace.jsx:45-90`, `DentalChartSVG.jsx:210-250`, PR #222 |
| **A16** | Testing | **DONE** | `frontend/src/features/clinical-chart/tests/a16RegressionGate.test.jsx`, `backend/tests/test_odontogram_traceability.py`, PR #222 |
| **A17** | Evidence and Handoff Package | **DONE** | `docs/odontogram-foundation/evidence/`, `docs/engineering/DEVELOPMENT_WORKFLOW.md`, PR #222 |
| **G0** | Revalidation Before Full VNext | **DONE** | `docs/product/ODONTOGRAM_VNEXT_PRODUCT_SPEC.md:1-50`, PR #222 |
| **G1** | Additive Clinical Core Schema | **DONE** | `backend/models/clinical_core.py:97-590`, migration `f4a5b6c7d8e9`, `test_clinical_core_schema.py`, PR #222 |
| **G2** | Canonical Catalog, Taxonomy, & Templates | **DONE** | `backend/clinical/catalog.py:1-120`, `templates.py:1-150`, `test_clinical_catalog.py`, PR #222 |
| **G3** | Deterministic Legacy Mapping Engine | **DONE** | `backend/clinical/legacy_mapping.py:1-140`, `treatment_service.py:189-224`, `test_clinical_legacy_mapping.py`, PR #222 & PR #226 |
| **G4** | Controlled Backfill | **DONE** | tool built and tested; not yet run on real data (`scripts/backfill_clinical_work_items.py:1-352`, `test_clinical_backfill.py` (35 tests, 100% coverage), PR #227 (commit `2c9b6180`)) |
| **G5** | Projection Layer & Real Chart Data | **DONE** | `backend/services/clinical_workspace_service.py:1-1018`, `test_clinical_workspace_service.py`, `backend/routers/clinical_workspace.py`, PR #222 |
| **G6** | Chart Integration to Codex Renderer | **DONE** | `frontend/src/features/clinical-chart/adapters/workspaceSnapshotAdapter.js:1-328`, `PatientDetails.jsx:558` (main chart) & `PatientDetails.jsx:659` (modal chart), `PatientDetails.chartRoots.test.jsx`, PR #222 & PR #228 (commit `7dceae07`) |
| **G7** | Command / API Layer | **PARTIAL** | `backend/services/treatment_service.py:260-470` (`_sync_clinical_work_item`, update & delete sync via PR #226), `POST /treatments/multi-procedure`, `test_treatment_service.py:900-1015`; dedicated standalone WorkItem CRUD router not yet exposed. |
| **G8** | Zero-Friction Charting UX | **PARTIAL** | `frontend/src/features/dental/DentalChartSVG.jsx:320-380` (surface selector), `TreatmentModal.jsx:210-310`, `PatientDetails.jsx:659` (modal chart via PR #228); quick action launcher / sticky tool mode not started. |
| **G9** | First-Class Treatment Plans | **PARTIAL** | Minimal treatment plans create & list (Slice G9a): `backend/models/clinical_core.py:189-280`, `backend/services/treatment_plan_service.py`, `backend/routers/treatment_plans.py`, `frontend/src/features/clinical-plans/TreatmentPlansCard.jsx`, `backend/tests/services/test_treatment_plan_service.py`, `frontend/src/tests/TreatmentPlansCard.test.jsx`, PR #230. Phase items and lifecycle not yet implemented. |

| **G10** | Sessions and Resume Engine | **SCHEMA_ONLY** | `backend/models/clinical_core.py:383-500` (`CareSession`, `CareSessionStep`, `CareObservation`), migration `f4a5b6c7d8e9`; service, router, and UI not yet implemented. |
| **G11** | Appointment Integration | **SCHEMA_ONLY** | `backend/models/clinical_core.py:542-575` (`NextVisitRequest`), migration `f4a5b6c7d8e9`; appointment integration service, reception queue, and suggestion UI not yet implemented. |
| **G12** | Lab Integration | **NOT_STARTED** | `backend/models/clinical.py:326` (`LabOrder` has no `work_item_id` foreign key); direct work item link and decoupling not implemented. |
| **G13** | Inventory Integration | **NOT_STARTED** | `backend/models/inventory.py:289` (`TreatmentMaterialUsage` references `material_sessions.id`, not `care_sessions.id`). |
| **G14** | Finance Integration and Parity | **NOT_STARTED** | `clinical_charges` table does not exist in schema, models, or migrations (`git grep clinical_charges` returns 0). |
| **G15** | Files and Clinical Context | **SCHEMA_ONLY** | `backend/models/clinical_core.py:582-615` (`ClinicalAttachmentLink`), migration `f4a5b6c7d8e9`; link API and attachment context UI not yet implemented. |
| **G16** | Rollout and Controlled Cutover | **PARTIAL** | `backend/config.py:120` (`clinical_vnext_rollout_mode`), `backend/services/clinical_workspace_service.py:997-1018` (supports `LEGACY_ONLY`, `SHADOW`, `VNEXT_PRIMARY`), `PatientDetails.jsx:446-456`; default is `LEGACY_ONLY`. |

---

## 3. Implementation State Legend

- **`DONE`**: Model, service, router/API, frontend component (where applicable), and automated tests are fully implemented and verified on `staging`.
- **`PARTIAL`**: Core backend projection or UI interaction is active, but sub-features (e.g. standalone command APIs or quick-action launchers) remain pending.
- **`SCHEMA_ONLY`**: Database tables, constraints, Alembic migrations, and RLS policies exist in `backend/models/clinical_core.py`, but no domain service, router endpoints, or UI workflows have been built.
- **`NOT_STARTED`**: Neither active schema nor runtime implementation exists in the codebase.
