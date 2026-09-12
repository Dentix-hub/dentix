# DENTIX Clinical VNext — G0 Revalidation Kickoff Note

> **Classification:** KICKOFF & CONTRACT REVALIDATION
> **GitHub Issue:** #178
> **Model:** Gemini 3.8 Flash (High)
> **Date:** 2026-09-06
> **Branch:** `feature/clinical-vnext-gemini`
> **Starting HEAD SHA:** `9214d9ad4399627f0faf199632c5dde482c4fd03`
> **Protected Staging SHA:** `9214d9ad4399627f0faf199632c5dde482c4fd03`
> **Origin Main SHA:** `86fbf612c0290f2534eb6e191af78ce2eaa7df26`
> **Part I Merge PR:** #177 (`Dentix-hub/feat/odontogram-part1-final-gate` -> `staging`)
> **Part I Merge Commit SHA:** `9214d9ad4399627f0faf199632c5dde482c4fd03`
> **Part I Closed Tracking Issue:** #133 (`CLOSED/agent:verified`)

---

## 1. Executive Summary & Provenance Reconciliation

This document formalizes the **Phase G0 Revalidation Kickoff** for DENTIX Clinical VNext (GitHub Issue #178) within the dedicated delegated worktree `feature/clinical-vnext-gemini`.

### Provenance & Reconciled Baseline Facts
- **Merged Integration Baseline:** Odontogram Foundation Part I was formally completed, verified across 230 focused tests, and merged into canonical `staging` via Pull Request **#177** (Merge commit `9214d9ad4399627f0faf199632c5dde482c4fd03`), fully closing Issue #133 as `agent:verified`.
- **Historical Metadata Context:** Historical snapshot documents—notably `docs/odontogram-foundation/HANDOFF_TO_GEMINI.md`—contain pre-merge baseline references (`614338f479e89ede7786bc85bd74eb0e25c32ed2`) and pending-integration wording written prior to the merge of PR #177. Per project safety discipline, historical Part I documentation is not retroactively rewritten; instead, this note records the reconciled ground truth at current HEAD.
- **Branch Lineage:** Current branch `feature/clinical-vnext-gemini` originates directly from the protected staging head `9214d9ad4399627f0faf199632c5dde482c4fd03`, inheriting all canonical Part I odontogram foundations intact.

---

## 2. Development Workflow Authority vs. Historical G0 Mechanics

In legacy planning documents (`docs/DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md` and `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md`), Phase G0 contemplated complex multi-agent pull, branch cross-merging, wave tracking, and micro-ticket state machines (G0-M01 through G0-M05).

Pursuant to **`docs/engineering/DEVELOPMENT_WORKFLOW.md` (Section 7: Authority & Legacy Plans)** and **`AGENTS.md`**:
1. **Superseding Authority:** `DEVELOPMENT_WORKFLOW.md` is the sole development lifecycle authority. Historical execution mechanics (obsolete role matrices, micro-ticket waves, or complex orchestration state machines) are explicitly superseded.
2. **Current Lifecycle Discipline:** DENTIX operates under a single, deterministic lifecycle:
   - **One active feature** per working session.
   - **One dedicated temporary branch** branched directly from and targeting `staging`.
   - **No manual cross-branch pulling or rebasing:** The delegated branch is already rooted on the exact merged staging SHA `9214d9ad4399627f0faf199632c5dde482c4fd03`.
   - **Validate once, promote the validated revision:** Local verification confirms compatibility before opening a single PR into `staging`.
   - **Requirement Provenance Preservation:** While execution mechanics are streamlined, product requirements, acceptance criteria, clinical invariants, and architectural guardrails from the product specifications remain 100% authoritative.

---

## 3. Contract Comparison: Handoff vs. Actual Code at HEAD

The canonical Part I frontend and renderer contracts specified in `docs/odontogram-foundation/HANDOFF_TO_GEMINI.md` were evaluated against the executable codebase at HEAD (`9214d9ad4399627f0faf199632c5dde482c4fd03`).

### Inspected Canonical Paths
1. `frontend/src/features/dental/DentalChartSVG.jsx`
2. `frontend/src/features/clinical-chart/domain/dentalAnatomyRegistry.js`
3. `frontend/src/features/clinical-chart/domain/clinicalChartProjection.js`
4. `frontend/src/features/clinical-chart/domain/chartNotation.js`
5. `frontend/src/features/clinical-chart/domain/visualRuleRegistry.js`
6. `frontend/src/features/clinical-chart/domain/clinicalVisualCodes.js`
7. `frontend/src/features/clinical-chart/domain/toothDisplayMetrics.js`
8. `frontend/src/features/clinical-chart/rendering/ClinicalChartRendererAdapter.js`
9. `frontend/src/features/clinical-chart/rendering/ClinicalToothVisualLayers.jsx`
10. `frontend/src/features/clinical-chart/rendering/crownGeometry.js`
11. `frontend/src/features/clinical-chart/rendering/rootGeometry.js`
12. `frontend/src/features/clinical-chart/rendering/surfaceGeometry.js`
13. `frontend/src/features/clinical-chart/rendering/visualInstructionSelectors.js`
14. `frontend/src/features/clinical-chart/fixtures/a12ScenarioFixtures.js`

### Contract Boundary Verification Matrix

| Contract Boundary | Handoff Specification | Code Implementation at Current HEAD | Status |
|---|---|---|:---:|
| **Source-of-Truth Separation** | Pure projection/renderer; never clinical source of truth; zero imports of API clients, repositories, services, or DB. | Verified: `ClinicalChartRendererAdapter.js` (lines 59-62) and `clinicalChartProjection.js` (lines 286-288) contain zero data-persistence or API dependencies. | **MATCH** |
| **schemaVersion 1 Boundary** | `ClinicalChartProjection` DTO carries `schemaVersion: 1`. Used solely as adapter projection contract for rendering. | Verified: `CLINICAL_CHART_PROJECTION_VERSION = 1` defined in `clinicalChartProjection.js` (line 13) and enforced by validator. | **MATCH** |
| **Intent Constants (`CHART_INTENT_TYPES`)** | Forward-slash constants: `chart/tooth-selected`, `chart/surface-selected`, `chart/root-selected`, `chart/multi-select-changed`. | Verified: `CHART_INTENT_TYPES` in `ClinicalChartRendererAdapter.js` (lines 20-25) matches exact string literals without colon notation. | **MATCH** |
| **Target-Kind Union (`PROJECTION_TARGET_KINDS`)** | Full 4-element union: `tooth \| surface \| root \| canal`. Consistently supported across findings, procedures, and selections. | Verified: `PROJECTION_TARGET_KINDS` in `clinicalChartProjection.js` (lines 20-25) defines `TOOTH`, `SURFACE`, `ROOT`, `CANAL`. Handled in `createProjectionTarget`. | **MATCH** |
| **FDI Identity / Notation Rule** | Canonical identity is strictly FDI (`11`–`48`, `51`–`85`). Palmer and Universal notations are presentation-only derived labels. | Verified: `chartNotation.js` (lines 53-71) preserves immutable FDI key; `resolveToothNotation` produces presentation strings without altering identity. | **MATCH** |
| **Surface Geometry & Semantics** | 5 clipped polygon targets: `M`, `D`, `O`/`I`, `B`, `L`/`P`. Maxillary inner is `P`; Mandibular inner is `L`. Anterior center is `I`; Posterior center is `O`. | Verified: `surfaceGeometry.js` (lines 3-11, 54-70) and `dentalAnatomyRegistry.js` (lines 80-90) enforce arch and tooth-type specific codes and geometries. | **MATCH** |
| **Root Identities** | Single (`single`), premolar bifurcated (`buccal`, `palatal` for 14/24), maxillary molar trifurcated (`mesiobuccal`, `distobuccal`, `palatal`), mandibular molar bifurcated (`mesial`, `distal`). | Verified: `getRootIds` in `dentalAnatomyRegistry.js` (lines 39-55) maps exact anatomically compliant root ID arrays. | **MATCH** |
| **Canonical Visual Codes** | Lifecycle: `PRESENT`, `MISSING`, `EXTRACTED`, `IMPACTED`, `UNERUPTED`. Findings: `CARIES`, `FRACTURE`, `PAIN`. Procedures: `REST_COMPOSITE`, `ENDO_RCT`, `PROS_CROWN`, `PROS_BRIDGE`, `IMPLANT_FIXTURE`, `IMPLANT_CROWN`, `SURG_EXTRACTION`. | Verified: `clinicalVisualCodes.js` (lines 1-23) defines exact frozen enums; imported and enforced by `visualRuleRegistry.js`. | **MATCH** |
| **Visual Lifecycle Phases** | Four lifecycle phases: `existing`, `planned`, `active`, `completed`. Governs z-index sequence and visual styling. | Verified: `PROJECTION_VISUAL_PHASES` in `clinicalChartProjection.js` (lines 27-32) and `VISUAL_LAYER_SEQUENCE` in `visualRuleRegistry.js` (lines 22-29). | **MATCH** |
| **React Query Integration Boundary** | Future server state owned by `@tanstack/react-query`; renderer adapter remains pure and stateless. | Verified: `PROJECT_STANDARDS.md` Section 4 and `ClinicalChartRendererAdapter.js` preserve pure input/output functional design. | **MATCH** |
| **Protected Geometry Files** | Zero modifications allowed to: `DentalChartSVG.jsx`, `crownGeometry.js`, `rootGeometry.js`, `surfaceGeometry.js`. | Verified: All 4 geometry files are untouched, clean, and verified against full snapshot test suite. | **MATCH** |

---

## 4. Execution & Verification Evidence

All required gate verification commands were executed on the worktree environment and recorded with exact outcomes:

### Verification Gate 1: Odontogram Traceability Matrix
- **Command:** `python -m pytest backend/tests/test_odontogram_traceability.py -q`
- **Exit Status:** `0` (Success)
- **Output:**
  ```text
  13 passed, 15 warnings in 12.10s
  backend/tests/test_odontogram_traceability.py coverage: 99%
  ```
- **Validation Scope:** Validates all 327 micro-task requirements from the historical master plan across all categories (Product Requirements: 259, Architecture Constraints: 21, Historical Mechanics: 11, Evidence Deliverables: 36), ensuring zero unmapped or discarded items.

### Verification Gate 2: Odontogram Subsystem & SVG Component Suite
- **Command:** `npm.cmd test -- --run src/features/clinical-chart/tests src/features/dental/DentalChartSVG.test.jsx` (from `frontend/`)
- **Exit Status:** `0` (Success)
- **Output:**
  ```text
  Test Files  15 passed (15)
       Tests  230 passed (230)
    Start at  16:33:18
    Duration  25.07s
  ```
- **Validation Scope:** Confirms full pass across 15 test suites covering anatomy registries, root geometries, surface hit targets, visual rule registries, comparison workspaces, and SVG canvas rendering.

### Verification Gate 3: Git Tree Integrity Check
- **Command:** `git diff --check`
- **Exit Status:** `0` (Success)
- **Output:** Clean (no whitespace, merge conflicts, or format violations).
- **Working Tree Status:** Clean working tree prior to creating this document; only `docs/clinical-vnext/G0_KICKOFF.md` created.

---

## 5. Contract Verdict & G1 Authorization

### Contract Verdict
**MATCH — 100% Alignment across all 11 architectural and clinical boundaries.**
There is **zero contract drift** between the Part I foundation handoff and the codebase at current HEAD.

### Backend Blockage Assessment
Contract drift **does NOT block backend work**. The renderer and projection contracts are stable, fully tested, and ready to be targeted by downstream clinical projection services.

### Next Bounded Phase: G1 Additive Clinical Core Schema
- **Designation:** Phase G1 — Additive Clinical Core Schema.
- **Bounded Scope:** Implement additive PostgreSQL tables, foreign key constraints, indexes, tenant isolation (RLS / `tenant_scope.py`), and Alembic migrations for core clinical models (`clinical_work_items`, `clinical_work_item_targets`, `clinical_treatment_plans`, `clinical_treatment_plan_phases`, `clinical_treatment_plan_items`, `clinical_events`, `clinical_event_targets`, `care_sessions`, `care_session_steps`, `care_observations`, `workflow_templates`, `next_visit_requests`, `clinical_attachment_links`).
- **Phase Boundary:** Pursuant to G0 discipline, G1 is strictly scoped and defined here without designing or implementing schemas, models, or migrations within this task.
