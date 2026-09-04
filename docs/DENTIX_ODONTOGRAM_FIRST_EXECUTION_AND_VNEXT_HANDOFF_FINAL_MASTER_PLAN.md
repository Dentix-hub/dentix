<!-- STATUS: HISTORICAL / NON-AUTHORITATIVE -->
# DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN

> **Classification**: `HISTORICAL-ARCHIVE`
> **Status**: HISTORICAL / NON-AUTHORITATIVE ARCHIVE
> **Notice**:
> - This document is retained strictly as a historical requirement source record.
> - Its product, clinical, and anatomical requirements are preserved through the active product specification (`docs/product/ODONTOGRAM_VNEXT_PRODUCT_SPEC.md`) and traceability matrix (`docs/product/ODONTOGRAM_TRACEABILITY_MATRIX.md`).
> - Its agent assignments, Codex/Gemini sequencing, branches, waves, micro-ticket mechanics, testing lifecycle, PR lifecycle, and release mechanics are obsolete.
> - It cannot override `PROJECT_STANDARDS.md`.
> - It cannot override `docs/engineering/DEVELOPMENT_WORKFLOW.md`.
> - It cannot override `AGENTS.md`.
> - No current task should execute directly from its historical workflow instructions.
> - Current development lifecycle is governed exclusively by `docs/engineering/DEVELOPMENT_WORKFLOW.md`.

---

# 0. Historical Purpose & Context (Archival Record)

*Historical Note: The section below reflects legacy execution planning between Codex and Gemini. For current development execution, refer exclusively to `docs/engineering/DEVELOPMENT_WORKFLOW.md` and `PROJECT_STANDARDS.md`.*

The historical intended delivery model was:

- **Step 1:** Codex executes **only the chart/odontogram foundation**
- **Step 2:** Gemini executes the **remaining VNext clinical workflow**
- **Step 3:** Codex performs a **forensic review and verification pass** on each Gemini delivery block

This plan was written in **very small, explicit, bounded micro-tasks** for legacy tracking.

---

# 1. Final Product Direction

## 1.1 Locked chart direction

The approved functional direction for the odontogram slice is:

**Dentix Native Renderer + Root Extension + Data-Driven Rules**

This means:

- keep the current Dentix chart visual style;
- keep the current overall layout;
- do **not** redesign the chart from scratch;
- add **roots only** as the first anatomy extension;
- keep the renderer separated from the clinical domain logic;
- keep the first UI simple;
- prepare the renderer for future root/canal-aware workflows.

## 1.2 What stays visually the same

- the current chart shell;
- the current tooth layout;
- the current stylistic line language;
- the current minimalist look.

## 1.3 What gets added in the first chart slice

- root outlines;
- anatomy registry;
- surface geometry;
- renderer contract;
- visual rule registry;
- demo states for findings and procedures;
- side-by-side multi-instance rendering;
- mobile and RTL-safe behavior.

---

# 2. Mandatory Execution Model

## 2.1 Role split

### Codex — Phase A only
Codex is authorized to implement **only** the odontogram/chart foundation defined in **Part I** of this document.

Codex must **not** implement the later clinical core, migration, finance, appointment, lab, or inventory phases in this run.

### Gemini — Remaining VNext
Gemini is authorized to implement **Part II** of this document **after Codex finishes Part I** and a handoff package exists.

### Codex — Reviewer
After each Gemini block, Codex must review:
- changed files;
- tests;
- behavior;
- acceptance criteria;
- regressions;
- phase completeness.

## 2.2 Hard-stop rules

### Codex hard stop
After completing Part I, Codex must:
1. stop implementation;
2. leave the chart slice runnable;
3. produce the handoff package;
4. state clearly: `WAITING FOR GEMINI VNEXT EXECUTION`.

### Gemini hard stop
Gemini must not skip phases, merge phases invisibly, or mark tasks done without evidence.

### Reviewer hard stop
Codex must not approve a Gemini phase if:
- any micro-task was skipped;
- any required test is missing;
- acceptance criteria are only asserted verbally;
- regressions are unresolved.

---

# 3. Branch and Delivery Strategy

## 3.1 Required branches

- `feature/odontogram-foundation-codex`
- `feature/clinical-vnext-gemini`
- `review/clinical-vnext-codex-audit` (optional review branch if needed)

## 3.2 Commit discipline

Use small commits only.

Recommended pattern:
- one anatomy concern per commit;
- one renderer concern per commit;
- one DTO/rule concern per commit;
- one UI concern per commit;
- one test concern per commit.

Examples:
- `feat(chart): add anatomy registry scaffold`
- `feat(chart): add permanent tooth root definitions`
- `feat(chart): add root layer renderer`
- `feat(chart): add visual rule registry`
- `test(chart): add multi-instance renderer tests`

---

# 4. Global Non-Negotiable Rules

1. Do not destroy old data.
2. Do not redesign the chart from zero.
3. Do not let renderer state become the clinical source of truth.
4. Do not let a package-owned DTO shape become the Dentix canonical schema.
5. Do not introduce giant modal-first UX.
6. Do not add unnecessary dependencies when Dentix already has usable ones.
7. Keep the first UI simple, but keep the underlying architecture extensible.
8. All later clinical complexity must remain in the domain model, not in the renderer.

---

# 5. Required Deliverables Overview

## Part I — Codex Deliverables
Codex must deliver:
- chart architecture decision note;
- anatomy registry;
- renderer contract;
- root-enhanced odontogram;
- visual rule registry;
- chart demo fixtures;
- multi-instance history compare view;
- mobile/RTL support;
- tests;
- screenshots / evidence;
- handoff package for Gemini.

## Part II — Gemini Deliverables
Gemini must deliver:
- additive clinical core;
- clinical catalog and taxonomy;
- deterministic migration engine;
- projection layer;
- command/API layer;
- chart integration to real data;
- zero-friction charting;
- treatment plans;
- sessions/resume engine;
- appointment integration;
- lab integration;
- inventory integration;
- finance integration;
- files/images context;
- rollout and controlled cutover.

## Part III — Codex Review Deliverables
Codex must deliver:
- phase review report;
- missing-task report;
- regression report;
- approval / rejected / blocked verdict.

---

# PART I — CODEX EXECUTES THE ODONTOGRAM FIRST

# 6. Part I Scope Boundary

## 6.1 In scope
Codex may implement:
- frontend chart architecture;
- anatomy definitions;
- tooth and root rendering;
- surface interaction geometry;
- demo projection DTOs;
- renderer adapter contract;
- lightweight chart workspace shell;
- test fixtures and demo scenarios.

## 6.2 Out of scope
Codex must **not** implement in this phase:
- production clinical schema;
- migrations;
- financial cutover;
- treatment plan backend;
- appointment bridge;
- lab bridge;
- inventory bridge;
- production API contracts;
- legacy migration.

Mock data is allowed for the chart foundation.

---

# 7. Part I Phase A0 — Baseline Revalidation and Freeze

## A0-M01 — Revalidate current `main`
- fetch latest `main`;
- compare relevant chart/frontend files against the plan assumptions.

**Acceptance:** drift report written.

## A0-M02 — Create execution docs folder
Create:
- `docs/odontogram-foundation/`

Add:
- `README.md`
- `TASK_TRACKER.md`
- `DECISIONS.md`
- `HANDOFF_TO_GEMINI.md`

**Acceptance:** all files exist.

## A0-M03 — Record baseline metadata
Record:
- repo name;
- execution branch;
- source `main` commit SHA;
- execution date;
- implementer = Codex.

**Acceptance:** metadata committed.

## A0-M04 — Create explicit scope lock note
Write a note stating:
- this phase is chart-only;
- no schema changes are authorized;
- mock/demo data is allowed;
- renderer is not source of truth.

**Acceptance:** note committed.

---

# 8. Part I Phase A1 — Final Chart Architecture Lock

## A1-M01 — Write chart direction ADR
Create:
- `docs/odontogram-foundation/ADR-001-CHART-DIRECTION.md`

State:
- keep current Dentix chart style;
- add roots;
- use Dentix native renderer direction;
- renderer separated from domain logic.

**Acceptance:** ADR committed.

## A1-M02 — Define chart architectural layers
Document these layers:
- Anatomy Registry
- Projection DTO
- Visual Rule Registry
- Renderer
- UI Interaction Layer

**Acceptance:** documented in ADR or companion file.

## A1-M03 — Define renderer non-responsibilities
Explicitly document that renderer does **not** own:
- persistence;
- pricing;
- workflows;
- finance;
- history storage.

**Acceptance:** documented.

## A1-M04 — Define future readiness targets
Document that architecture must be ready for:
- root targeting;
- canal targeting;
- layered existing/planned/active/completed visuals;
- multi-instance rendering.

**Acceptance:** documented.

---

# 9. Part I Phase A2 — Frontend Chart Module Scaffold

## A2-M01 — Create feature directory
Create:
- `frontend/src/features/clinical-chart/`

**Acceptance:** folder exists.

## A2-M02 — Create subfolders
Create:
- `components/`
- `domain/`
- `rendering/`
- `fixtures/`
- `hooks/`
- `tests/`

**Acceptance:** folders exist.

## A2-M03 — Create entry workspace component
Create:
- `ClinicalChartWorkspace.jsx` or repo-equivalent.

**Acceptance:** renders without crashing.

## A2-M04 — Create temporary demo route
Add isolated demo route for chart development.

Suggested:
- `/clinical-chart/demo`

**Acceptance:** route opens successfully.

---

# 10. Part I Phase A3 — Anatomy Registry Foundation

## A3-M01 — Create anatomy registry file
Create:
- `domain/dentalAnatomyRegistry.js`

**Acceptance:** file exists and exports scaffold.

## A3-M02 — Define anatomy model shape
Each anatomy record must support:
- tooth key;
- tooth type;
- crown outline reference;
- surface map;
- root count;
- root outline references;
- canal anchor placeholders;
- label anchor;
- overlay anchors.

**Acceptance:** typed or clearly structured model exists.

## A3-M03 — Define permanent dentition keys
Add permanent tooth registry coverage.

**Acceptance:** all permanent positions represented.

## A3-M04 — Define primary dentition keys
Add primary tooth registry coverage.

**Acceptance:** all primary positions represented.

## A3-M05 — Define mixed-dentition compatibility note
Document how permanent + primary can coexist in one view.

**Acceptance:** note committed.

---

# 11. Part I Phase A4 — Crown Outline Integration

## A4-M01 — Inventory current crown outlines
Audit the current programmatic tooth shapes already موجودة in the code.

**Acceptance:** list of existing shape assets/components documented.

## A4-M02 — Normalize crown shape access
Create a clean lookup so crown shapes are accessed by tooth/anatomy key rather than ad hoc imports.

**Acceptance:** lookup works.

## A4-M03 — Preserve current visual style
Ensure crown outlines remain visually unchanged from the current Dentix style.

**Acceptance:** side-by-side screenshot confirms parity.

---

# 12. Part I Phase A5 — Root Anatomy Definition

## A5-M01 — Create root outline model
Define a root outline structure compatible with the crown registry.

**Acceptance:** structure exists.

## A5-M02 — Add single-root anterior definitions
Define roots for:
- incisors;
- canines.

**Acceptance:** rendered correctly in demo.

## A5-M03 — Add premolar root definitions
Define premolar roots by tooth type.

**Acceptance:** rendered correctly in demo.

## A5-M04 — Add molar root definitions
Define molar roots by tooth type.

**Acceptance:** rendered correctly in demo.

## A5-M05 — Add primary tooth root definitions
Define roots for primary teeth in simplified form.

**Acceptance:** rendered correctly in demo.

## A5-M06 — Keep root style visually aligned
Match:
- stroke style;
- visual simplicity;
- outline language;
- proportion rules.

**Acceptance:** screenshots reviewed.

---

# 13. Part I Phase A6 — Surface Geometry Foundation

## A6-M01 — Create surface code constants
Add surface constants.

Permanent target set:
- M
- D
- O/I
- B
- L/P

**Acceptance:** constants exported.

## A6-M02 — Define per-tooth clickable surface geometry
Create geometric definitions for surface selection per tooth type.

**Acceptance:** geometry exists for all main tooth families.

## A6-M03 — Support anterior surface model
Anterior teeth must support incisal-compatible geometry.

**Acceptance:** demo works.

## A6-M04 — Support posterior surface model
Posterior teeth must support occlusal-compatible geometry.

**Acceptance:** demo works.

## A6-M05 — Add hover/focus/selected states
Add non-destructive interaction styles.

**Acceptance:** interaction visible.

---

# 14. Part I Phase A7 — Renderer Contract

## A7-M01 — Create renderer adapter interface
Create:
- `rendering/ClinicalChartRendererAdapter.js` or repo-equivalent.

**Acceptance:** interface exists.

## A7-M02 — Define input DTO contract
Renderer input must accept:
- anatomy definition;
- visual state DTO;
- notation mode;
- read-only/edit mode;
- interaction callbacks.

**Acceptance:** contract documented and used.

## A7-M03 — Define output interaction intents
Renderer emits neutral intents such as:
- tooth selected;
- surface selected;
- root selected;
- multi-select changed.

**Acceptance:** callbacks fire.

## A7-M04 — Prevent persistence leakage
Renderer must not directly call backend APIs or domain services.

**Acceptance:** no persistence calls inside renderer.

---

# 15. Part I Phase A8 — Projection DTO for Demo Use

## A8-M01 — Create demo DTO schema
Create a simple visual DTO for the chart demo.

**Acceptance:** schema file exists.

## A8-M02 — Define tooth visual state shape
Each tooth may include:
- lifecycle;
- findings;
- procedures;
- selection;
- disabled state;
- annotations.

**Acceptance:** schema documented.

## A8-M03 — Define target subshape
Targets may include:
- whole tooth;
- surface;
- root;
- canal placeholder.

**Acceptance:** schema documented.

## A8-M04 — Add sample DTO fixtures
Create fixtures for key use cases.

**Acceptance:** fixtures load.

---

# 16. Part I Phase A9 — Visual Rule Registry

## A9-M01 — Create visual rule registry file
Create:
- `domain/visualRuleRegistry.js`

**Acceptance:** file exists.

## A9-M02 — Add lifecycle rules
Support:
- PRESENT
- MISSING
- EXTRACTED
- IMPACTED
- UNERUPTED

**Acceptance:** demo shows states.

## A9-M03 — Add finding rules
Support at minimum:
- CARIES
- FRACTURE
- PAIN marker or generic symptom marker

**Acceptance:** demo shows findings.

## A9-M04 — Add procedure rules
Support at minimum:
- REST_COMPOSITE
- ENDO_RCT
- PROS_CROWN
- PROS_BRIDGE
- IMPLANT_FIXTURE
- IMPLANT_CROWN
- SURG_EXTRACTION planned/completed semantics

**Acceptance:** demo shows procedures.

## A9-M05 — Add layer mapping
Separate layers:
- base anatomy;
- lifecycle;
- findings;
- existing/completed work;
- planned/active work;
- selection/focus.

**Acceptance:** layer order stable.

---

# 17. Part I Phase A10 — Root Layer Rendering

## A10-M01 — Add root layer renderer
Render roots as a separate layer under the crown.

**Acceptance:** visible roots render correctly.

## A10-M02 — Handle single-root teeth
Verify incisors/canines.

**Acceptance:** demo verified.

## A10-M03 — Handle premolars
Verify premolar root behavior.

**Acceptance:** demo verified.

## A10-M04 — Handle molars
Verify multi-root rendering.

**Acceptance:** demo verified.

## A10-M05 — Handle primary teeth
Verify simplified primary roots.

**Acceptance:** demo verified.

## A10-M06 — Prevent root overlap artifacts
Fix spacing/alignment issues.

**Acceptance:** no obvious overlap defects.

---

# 18. Part I Phase A11 — Notation and Labels

## A11-M01 — Support current notation display mode
Keep current display behavior compatible with existing chart expectations.

**Acceptance:** current mode renders.

## A11-M02 — Add notation abstraction
Create notation config so future FDI/Palmer/Universal display switching is possible.

**Acceptance:** abstraction exists.

## A11-M03 — Verify label placement after roots
Make sure tooth labels remain visually clean after adding roots.

**Acceptance:** labels remain readable.

---

# 19. Part I Phase A12 — Demo Clinical Scenarios

## A12-M01 — Create adult dentition fixture
**Acceptance:** fixture renders.

## A12-M02 — Create primary dentition fixture
**Acceptance:** fixture renders.

## A12-M03 — Create mixed dentition fixture
**Acceptance:** fixture renders.

## A12-M04 — Create caries-on-surface fixture
Example:
- tooth 46;
- distal caries.

**Acceptance:** renders.

## A12-M05 — Create MOD restoration fixture
Example:
- tooth 46;
- MOD composite.

**Acceptance:** renders.

## A12-M06 — Create RCT fixture
**Acceptance:** renders.

## A12-M07 — Create crown fixture
**Acceptance:** renders.

## A12-M08 — Create missing tooth fixture
**Acceptance:** renders.

## A12-M09 — Create implant fixture
**Acceptance:** renders.

## A12-M10 — Create bridge fixture
Example:
- 14 abutment;
- 15 pontic;
- 16 abutment.

**Acceptance:** renders.

## A12-M11 — Create simultaneous existing + planned fixture
**Acceptance:** layered rendering verified.

---

# 20. Part I Phase A13 — Multi-Instance and History Compare

## A13-M01 — Create dual-chart page
Suggested:
- current state;
- historical state.

**Acceptance:** page renders two charts.

## A13-M02 — Ensure state isolation
Selection in one chart must not affect the other.

**Acceptance:** verified.

## A13-M03 — Ensure independent layer filtering
Each chart instance can differ.

**Acceptance:** verified.

## A13-M04 — Ensure read-only multi-instance support
Both charts can remain read-only.

**Acceptance:** verified.

---

# 21. Part I Phase A14 — Basic UI Layer

## A14-M01 — Create chart shell header
**Acceptance:** visible.

## A14-M02 — Create simple legend
**Acceptance:** visible.

## A14-M03 — Create simple inspector panel
Minimal information only.

**Acceptance:** visible.

## A14-M04 — Create simple selection summary
Show selected tooth/surface.

**Acceptance:** visible.

## A14-M05 — Keep UI intentionally simple
Do not introduce giant modal flows in this phase.

**Acceptance:** no giant modal added.

---

# 22. Part I Phase A15 — Mobile, RTL, and Accessibility

## A15-M01 — Verify chart on desktop
**Acceptance:** usable.

## A15-M02 — Verify chart on tablet width
**Acceptance:** usable.

## A15-M03 — Verify chart on mobile width
**Acceptance:** usable.

## A15-M04 — Add quadrant-friendly mobile behavior
Even if basic.

**Acceptance:** mobile usable without broken layout.

## A15-M05 — Verify Arabic RTL layout
**Acceptance:** usable.

## A15-M06 — Verify English LTR layout
**Acceptance:** usable.

## A15-M07 — Add keyboard focus states
**Acceptance:** visible.

## A15-M08 — Add accessible labels where practical
**Acceptance:** basic accessibility improved.

---

# 23. Part I Phase A16 — Testing

## A16-M01 — Add anatomy registry coverage test
**Acceptance:** passes.

## A16-M02 — Add renderer smoke test
**Acceptance:** passes.

## A16-M03 — Add multi-instance isolation test
**Acceptance:** passes.

## A16-M04 — Add root rendering snapshot or visual regression test
**Acceptance:** passes.

## A16-M05 — Add mixed dentition render test
**Acceptance:** passes.

## A16-M06 — Add RTL render test
**Acceptance:** passes.

## A16-M07 — Add mobile render test if tooling allows
**Acceptance:** passes or documented blocked reason.

---

# 24. Part I Phase A17 — Evidence and Handoff Package

## A17-M01 — Capture desktop screenshots
**Acceptance:** saved.

## A17-M02 — Capture mobile screenshots
**Acceptance:** saved.

## A17-M03 — Capture RTL screenshots
**Acceptance:** saved.

## A17-M04 — Capture history-compare screenshots
**Acceptance:** saved.

## A17-M05 — Write Codex completion report
Create:
- `docs/odontogram-foundation/CODEX_COMPLETION_REPORT.md`

Include:
- changed files;
- tests run;
- known limitations;
- future extension points;
- blocked items if any.

**Acceptance:** report committed.

## A17-M06 — Write handoff package for Gemini
Create:
- `docs/odontogram-foundation/HANDOFF_TO_GEMINI.md`

Must include:
- what is done;
- what is intentionally not done;
- integration contracts;
- files to reuse;
- next recommended implementation order.

**Acceptance:** handoff committed.

## A17-M07 — Hard stop
Codex must stop and state:

`WAITING FOR GEMINI VNEXT EXECUTION`

**Acceptance:** statement included in report/handoff.

---

# 25. Part I Exit Gate

Codex Part I is complete only if:

- the chart still looks like Dentix;
- roots were added successfully;
- no full redesign happened;
- anatomy registry exists;
- visual rule registry exists;
- renderer contract exists;
- multi-instance compare works;
- mobile/RTL evidence exists;
- tests exist and pass;
- handoff package exists;
- Codex stopped after the chart slice.

---

# PART II — GEMINI IMPLEMENTS THE REMAINING VNEXT

# 26. Gemini Scope Start Condition

Gemini may begin only after:
- Part I is complete;
- the handoff package exists;
- the chart branch is readable and usable;
- the renderer contract is stable enough for integration.

---

# 27. Part II Phase G0 — Revalidation Before Full VNext

## G0-M01 — Pull latest `main`
## G0-M02 — Pull Codex chart branch
## G0-M03 — Compare chart branch against handoff docs
## G0-M04 — Write Gemini kickoff note
## G0-M05 — Confirm no contract drift before backend work starts

**Acceptance:** kickoff note committed.

---

# 28. Part II Phase G1 — Additive Clinical Core Schema

## G1-M01 — Create `clinical_work_items`
## G1-M02 — Add work item constraints and indexes
## G1-M03 — Create `clinical_work_item_targets`
## G1-M04 — Add target validation rules
## G1-M05 — Create `clinical_treatment_plans`
## G1-M06 — Create `clinical_treatment_plan_phases`
## G1-M07 — Create `clinical_treatment_plan_items`
## G1-M08 — Create `clinical_events`
## G1-M09 — Create `clinical_event_targets`
## G1-M10 — Create `care_sessions`
## G1-M11 — Create `care_session_steps`
## G1-M12 — Create `care_observations`
## G1-M13 — Create `workflow_templates`
## G1-M14 — Create `next_visit_requests`
## G1-M15 — Create `clinical_attachment_links`
## G1-M16 — Add RLS policies to every new tenant table
## G1-M17 — Add migration
## G1-M18 — Add schema tests

**Acceptance:** migration applies cleanly and tests pass.

---

# 29. Part II Phase G2 — Canonical Catalog, Taxonomy, and Workflow Templates

## G2-M01 — Define canonical procedure codes
## G2-M02 — Define canonical finding codes
## G2-M03 — Define tooth lifecycle codes
## G2-M04 — Define treatment lifecycle codes
## G2-M05 — Create procedure category model
## G2-M06 — Create procedure subcategory model
## G2-M07 — Map core procedures to categories
## G2-M08 — Map findings to supported target types
## G2-M09 — Create RCT template v1
## G2-M10 — Create crown template v1
## G2-M11 — Create bridge template v1
## G2-M12 — Create composite template v1
## G2-M13 — Create extraction template v1
## G2-M14 — Create denture template v1
## G2-M15 — Add template versioning rules
## G2-M16 — Add catalog tests

**Acceptance:** catalog and templates exist, validated, and tested.

---

# 30. Part II Phase G3 — Deterministic Legacy Mapping Engine

## G3-M01 — Create migration package scaffold
## G3-M02 — Implement treatment procedure mapping
## G3-M03 — Implement treatment status mapping
## G3-M04 — Implement tooth notation mapping
## G3-M05 — Implement treatment-to-work-item mapping
## G3-M06 — Implement treatment-to-event mapping
## G3-M07 — Implement tooth-status mapping
## G3-M08 — Implement legacy treatment-session mapping
## G3-M09 — Preserve old free-text sessions
## G3-M10 — Implement exact lab-link mapping
## G3-M11 — Mark ambiguous duplicates only
## G3-M12 — Add idempotency tests
## G3-M13 — Add tenant isolation tests

**Acceptance:** deterministic mapper works and source rows remain untouched.

---

# 31. Part II Phase G4 — Controlled Backfill

## G4-M01 — Add dry-run mode
## G4-M02 — Add tenant-scoped execution
## G4-M03 — Add batch processing
## G4-M04 — Add resume checkpointing
## G4-M05 — Backfill treatments
## G4-M06 — Backfill tooth-status events
## G4-M07 — Backfill legacy care sessions
## G4-M08 — Backfill exact lab relationships
## G4-M09 — Backfill deterministic attachment links only
## G4-M10 — Verify record counts
## G4-M11 — Verify old data unchanged
## G4-M12 — Verify inventory unchanged
## G4-M13 — Verify payments unchanged
## G4-M14 — Generate backfill report

**Acceptance:** parity and invariance checks pass.

---

# 32. Part II Phase G5 — Projection Layer and Real Chart Data

## G5-M01 — Create clinical projection service
## G5-M02 — Add `as_of` support
## G5-M03 — Add tooth summary projection
## G5-M04 — Add work-item summary projection
## G5-M05 — Add patient clinical workspace aggregate
## G5-M06 — Add legacy read fallback
## G5-M07 — Add feature flag
## G5-M08 — Add shadow-read comparison
## G5-M09 — Add projection caching
## G5-M10 — Add performance benchmark

**Acceptance:** chart can render from real projected data.

---

# 33. Part II Phase G6 — Chart Integration to the Codex Renderer

## G6-M01 — Replace demo DTOs with projection-backed DTOs
## G6-M02 — Keep renderer contract stable or document changes precisely
## G6-M03 — Connect chart workspace to real patient data
## G6-M04 — Preserve multi-instance capability
## G6-M05 — Preserve mobile and RTL behavior
## G6-M06 — Add projection-to-renderer integration tests

**Acceptance:** real data renders through the Codex chart foundation.

---

# 34. Part II Phase G7 — Command/API Layer

## G7-M01 — Create command service
## G7-M02 — Add work item create API
## G7-M03 — Add work item update API
## G7-M04 — Add finding create API
## G7-M05 — Add bulk finding API
## G7-M06 — Add procedure create API
## G7-M07 — Add bulk procedure API
## G7-M08 — Add event correction API
## G7-M09 — Add workspace read API
## G7-M10 — Add tooth detail API
## G7-M11 — Add history API
## G7-M12 — Add permission enforcement
## G7-M13 — Add tenant security tests
## G7-M14 — Add API contract tests
## G7-M15 — Add idempotency keys
## G7-M16 — Add optimistic concurrency handling

**Acceptance:** APIs are safe, tested, and bounded.

---

# 35. Part II Phase G8 — Zero-Friction Charting UX

## G8-M01 — Add tooth selection state
## G8-M02 — Add quick action launcher
## G8-M03 — Add tooth-first flow
## G8-M04 — Add procedure-first flow
## G8-M05 — Add sticky tool mode
## G8-M06 — Add multi-select
## G8-M07 — Add direct surface interaction
## G8-M08 — Add favorites
## G8-M09 — Add recents
## G8-M10 — Add search
## G8-M11 — Add smart defaults
## G8-M12 — Add undo stack
## G8-M13 — Add consequence-aware remove
## G8-M14 — Measure click budget
## G8-M15 — De-emphasize old giant modal

**Acceptance:** common tasks hit the click-budget targets.

---

# 36. Part II Phase G9 — First-Class Treatment Plans

## G9-M01 — Create treatment plan service
## G9-M02 — Add plan create API
## G9-M03 — Add phase CRUD/reorder
## G9-M04 — Add work item membership API
## G9-M05 — Support shared work items across plans
## G9-M06 — Add plan lifecycle states
## G9-M07 — Add accept-plan flow
## G9-M08 — Preserve alternatives
## G9-M09 — Add plan overlay to chart
## G9-M10 — Add estimate projection
## G9-M11 — Add plan comparison UX
## G9-M12 — Add legacy safety rules
## G9-M13 — Add concurrency tests
## G9-M14 — Add E2E scenario

**Acceptance:** treatment plans work without duplicating care episodes.

---

# 37. Part II Phase G10 — Sessions and Resume Engine

## G10-M01 — Create care session service
## G10-M02 — Add start-session command
## G10-M03 — Add finish-session command
## G10-M04 — Add step add/update API
## G10-M05 — Add partial-step support
## G10-M06 — Add repeatable-step support
## G10-M07 — Add observation API
## G10-M08 — Build minimal RCT structured UI
## G10-M09 — Add canal-target UI
## G10-M10 — Add working-length structured entry
## G10-M11 — Add compact finish-session sheet
## G10-M12 — Build resume engine
## G10-M13 — Add continue-treatment card
## G10-M14 — Add clinical summary generation
## G10-M15 — Preserve free notes
## G10-M16 — Add template deviation support
## G10-M17 — Add finalization audit trail
## G10-M18 — Add concurrent session protection
## G10-M19 — Migrate new writes away from free-text-only session model
## G10-M20 — Add RCT scenario integration test

**Acceptance:** doctor can resume treatment without reading old notes manually.

---

# 38. Part II Phase G11 — Appointment Integration

## G11-M01 — Link session to appointment
## G11-M02 — Add next-visit request creation
## G11-M03 — Add auto-suggestion from workflow template
## G11-M04 — Add reception queue
## G11-M05 — Convert request to appointment
## G11-M06 — Populate appointment reason
## G11-M07 — Suggest duration
## G11-M08 — Prevent auto-booking without user action
## G11-M09 — Handle appointment cancellation safely
## G11-M10 — Handle appointment completion safely
## G11-M11 — Add integration tests
## G11-M12 — Add idempotency/race tests

**Acceptance:** reception can see what the patient needs next.

---

# 39. Part II Phase G12 — Lab Integration

## G12-M01 — Add real FK from lab order to work item
## G12-M02 — Add exact legacy migration support
## G12-M03 — Stop using note-string linkage for new data
## G12-M04 — Create lab requirement definition
## G12-M05 — Add lab-ready trigger
## G12-M06 — Add one-tap lab handoff sheet
## G12-M07 — Allow missing optional lab data
## G12-M08 — Create lab order without creating duplicate treatment
## G12-M09 — Decouple lab price from synthetic treatment creation
## G12-M10 — Add lab status mapping
## G12-M11 — Reflect lab state in work item
## G12-M12 — Prevent auto-complete when lab is ready
## G12-M13 — Add shade/material sync rules
## G12-M14 — Support bridge semantics
## G12-M15 — Add duplicate-billing regression test
## G12-M16 — Add handoff idempotency

**Acceptance:** lab workflows do not duplicate patient charges.

---

# 40. Part II Phase G13 — Inventory Integration

## G13-M01 — Distinguish material session from care session
## G13-M02 — Add `care_session_id` to new usage model
## G13-M03 — Preserve old usage data
## G13-M04 — Create material suggestion service
## G13-M05 — Prevent stock deduction at plan creation
## G13-M06 — Deduct at actual use point
## G13-M07 — Support different materials per session
## G13-M08 — Preserve divisible-material logic
## G13-M09 — Aggregate work-item material cost
## G13-M10 — Add migration invariance test
## G13-M11 — Add endo material scenario test

**Acceptance:** inventory follows care sessions without rewriting history.

---

# 41. Part II Phase G14 — Finance Integration and Parity

## G14-M01 — Define billing policy model
## G14-M02 — Keep old finance source authoritative during shadow mode
## G14-M03 — Add work-item billing projection
## G14-M04 — Design `clinical_charges`
## G14-M05 — Preserve payments unchanged
## G14-M06 — Create shadow calculator
## G14-M07 — Run per-patient parity
## G14-M08 — Run per-tenant parity
## G14-M09 — Detect legacy lab double-charge cases
## G14-M10 — Add deterministic remediation workflow
## G14-M11 — Add doctor-share compatibility tests
## G14-M12 — Cut finance reads only behind flag
## G14-M13 — Keep payments stable
## G14-M14 — Add financial regression suite

**Acceptance:** no cutover before exact parity.

---

# 42. Part II Phase G15 — Files and Clinical Context

## G15-M01 — Keep attachment storage unchanged
## G15-M02 — Add context links only
## G15-M03 — Link images to tooth
## G15-M04 — Link images to work item
## G15-M05 — Link images to care session
## G15-M06 — Add purpose codes
## G15-M07 — Show relevant images in tooth inspector
## G15-M08 — Show relevant images in session view
## G15-M09 — Add deterministic legacy link migration only

**Acceptance:** no duplicate uploads or unsafe file moves.

---

# 43. Part II Phase G16 — Rollout and Controlled Cutover

## G16-M01 — Enable internal tenant only
## G16-M02 — Roll out read-only VNext
## G16-M03 — Enable internal writes
## G16-M04 — Monitor errors
## G16-M05 — Monitor parity
## G16-M06 — Pilot clinic
## G16-M07 — Small rollout percentage
## G16-M08 — Add tenant rollback toggle
## G16-M09 — Expand rollout gradually
## G16-M10 — Keep legacy compatibility during rollout
## G16-M11 — Observe stability window
## G16-M12 — Stop legacy writes only after evidence
## G16-M13 — Retire dead code only after stability

**Acceptance:** controlled rollout succeeds without destructive cutover risk.

---

# PART III — CODEX REVIEWS GEMINI

# 44. Review Protocol

Codex must review Gemini output **phase by phase**, not only at the end.

---

# 45. Review Micro-Tasks Per Gemini Phase

## R-M01 — Read Gemini completion report
## R-M02 — Compare delivered files against planned micro-tasks
## R-M03 — Mark missing tasks explicitly
## R-M04 — Run/inspect tests
## R-M05 — Inspect migration safety if applicable
## R-M06 — Inspect tenant isolation if applicable
## R-M07 — Inspect idempotency protections if applicable
## R-M08 — Inspect UI behavior if applicable
## R-M09 — Inspect performance implications if applicable
## R-M10 — Write review verdict:
- `APPROVED`
- `APPROVED WITH FOLLOW-UPS`
- `BLOCKED`
- `REJECTED`

**Acceptance:** review report committed.

---

# 46. Mandatory Evidence Rule

No phase is complete without evidence appropriate to that phase.

Examples:
- changed file list;
- tests;
- screenshots;
- migration output;
- parity output;
- benchmark output;
- API examples;
- explicit acceptance checklist.

---

# 47. Final Definition of Done

The whole initiative is done only when:

1. the Dentix chart keeps its identity;
2. roots are added successfully;
3. the chart is integrated with a real clinical core;
4. treatment plans exist as first-class objects;
5. multi-session care and resume workflows work;
6. appointments, lab, inventory, finance, and files are integrated;
7. old data is preserved;
8. financial parity is proven;
9. mobile and RTL usability are proven;
10. rollout is controlled and reversible;
11. Codex has reviewed the Gemini implementation and explicitly signed off.

---

# 48. Exact Execution Order Summary

## Step A — Codex
Execute **Part I only**.

## Step B — Hard Stop
Produce handoff package and stop.

## Step C — Gemini
Execute **Part II** phase by phase.

## Step D — Codex Review
Review each Gemini delivery phase.

---

# 49. Final Operator Instruction

## Instruction for Codex
Execute this plan strictly, but only **Part I**.  
Implement the Dentix odontogram foundation with root extension, anatomy registry, renderer contract, and visual rule registry.  
Do not start the broader VNext implementation.  
When Part I is complete, produce the handoff package and stop.

## Instruction for Gemini
After Part I is complete, execute **Part II** strictly by micro-task and phase gate.  
Reuse the Codex chart foundation.  
Do not redesign the chart.  
Integrate the remaining VNext architecture phase by phase.

## Instruction for Codex Reviewer
After each Gemini delivery block, perform a forensic review against this plan and mark every missing, partial, or regressed item explicitly.

---

# 50. Final Authority

This file is the final controlling execution plan for:
- chart-first execution by Codex,
- remaining VNext execution by Gemini,
- review by Codex.

If any shortcut, older chat note, or implementation decision conflicts with this file, the implementer must stop and request clarification instead of silently choosing a different path.