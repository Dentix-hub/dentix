# Dentix Unified Clinical Workflow VNext
## Master Implementation Plan — Micro-Task Edition

**Status:** FINAL PRE-IMPLEMENTATION MASTER PLAN — third-forensic-verified, OSS-aware, and human-gated before odontogram architecture lock  
**Target repository:** `Dentix-hub/dentix`  
**Baseline branch:** `main`  
**Baseline commit verified during planning and re-verified before implementation:** `46584940df522e681e52fac1ec4bc3b7b206793b`  
**Third verification date:** 2026-08-26  
**Third verification scope:** current `main`, data/migration invariants, treatment-plan gap, session semantics, lab/finance/inventory coupling, concurrency/idempotency, open-source/build-vs-buy review, and mandatory human approval of the odontogram architecture before full implementation.  
**Primary goal:** Replace the isolated, modal-heavy dental chart/treatment workflow with a unified clinical core that connects charting, multi-session care, treatment plans, appointments, laboratory work, inventory, finance, files/images, and longitudinal history without destroying or rewriting existing customer data.

---

# 0. Executive Intent

This project is **not** a cosmetic odontogram redesign.

The target is a new **Dentix Clinical Core** built around these principles:

1. **Enter once — flow everywhere.**
2. **Simple first — powerful when needed.**
3. **Clinical complexity belongs in the domain model, not in front of the doctor.**
4. **The common task must never pay the complexity cost of the uncommon task.**
5. **Clinical work is longitudinal. A procedure may span multiple visits, sessions, steps, appointments, lab stages, materials, and financial events.**
6. **Historical customer data must be preserved and migrated additively.**
7. **Never infer a clinical fact during migration when certainty is insufficient.**
8. **No destructive cutover until old/new financial and clinical projections are verified.**
9. **All SaaS tenant boundaries must remain enforced.**
10. **The chart is a projection/controller over the clinical core, not the source of truth.**
11. **Reuse before rebuild:** before custom-building a capability, evaluate existing Dentix dependencies and trustworthy open-source projects; adopt only when licensing, maintenance, security, UX, data-control, and exit-strategy gates pass.
12. **Third-party code may accelerate presentation and interaction, but it must never become the authoritative clinical data model.**

---

# 1. Current-System Facts That Drive This Plan

The implementation must assume the following verified characteristics of the current codebase:

- Active chart UI is centered around `DentalChartSVG.jsx` and whole-tooth statuses.
- `Treatment` currently mixes clinical, billing, status, endodontic, and note concerns.
- `Treatment.sessions` still exists as text while `TreatmentSession` also exists separately.
- `TreatmentSession` is currently too shallow for a real multi-session care engine.
- Current `MultiSessionPanel` primarily stores free-text session notes.
- `LabOrder` currently duplicates patient/work/tooth/material/shade/cost information.
- Lab billing synchronization currently creates/updates a linked `Treatment` and identifies that pair through `notes = Link:LabOrder:<id>`.
- Current billing totals and outstanding balances still depend directly on `Treatment.cost - Treatment.discount` and `Payment.amount`.
- Current inventory already has useful domain objects for materials, batches, stock movements, material sessions, and treatment material usage.
- Existing `TreatmentMaterialUsage.session_id` points to a **MaterialSession**, not to a clinical treatment visit.
- Existing attachments are patient-level records and are not natively linked to tooth/work-item/session/purpose.
- A transactional outbox/domain-event infrastructure already exists and should be reused for integration events, while remaining separate from permanent patient clinical events.
- The frontend already ships mature reusable primitives including Radix Dialog/Select/Dropdown/Tooltip, Headless UI, TanStack Query/Table/Virtual, Zustand, dnd-kit, react-hotkeys-hook, FullCalendar, Playwright, and Vitest. New overlapping dependencies should not be added without a documented reason.
- The current repository has no native first-class Treatment Plan aggregate/table discovered during the re-audit; therefore VNext must explicitly model treatment plans rather than merely storing an undefined `treatment_plan_id` on a work item.
- Existing timestamp handling follows Dentix's established UTC-naive persistence convention for instant-like clinical/financial timestamps; VNext must follow the same convention until a separately approved timezone-storage migration changes the platform-wide rule.

These facts mean the redesign must be **additive, compatibility-first, and phased**.

---

# 1A. AI Developer Execution Contract — Mandatory

This section controls how an AI developer or human developer must execute this plan.

## 1A.1 Initial execution scope

On the first execution run, the developer MUST perform only:

1. Phase 0 — Forensic Production Data Baseline and production-shaped rehearsal preparation;
2. Phase 0A — Reuse / Open-Source / Odontogram Technical Spikes;
3. the Odontogram Decision Report and demo deliverables defined in Phase 0A.

The developer MUST NOT start Phase 1 or any later implementation phase until the mandatory Human Odontogram Decision Gate has been passed.

## 1A.2 No autonomous architecture lock

The developer may:

- investigate;
- prototype;
- benchmark;
- score;
- identify risks;
- recommend one odontogram strategy.

The developer MUST NOT autonomously choose the final odontogram strategy and continue.

The final choice belongs to the project owner.

## 1A.3 Required approval token

Full implementation may resume only after an explicit owner instruction matching one of:

- `APPROVE ODONTOGRAM STRATEGY: A`
- `APPROVE ODONTOGRAM STRATEGY: B`
- `APPROVE ODONTOGRAM STRATEGY: C`

No inferred approval, silence, Git commit, successful build, or recommendation counts as approval.

## 1A.4 Hard-stop behavior

When the Phase 0A deliverables are complete, the developer MUST:

1. stop implementation work;
2. leave all prototypes runnable;
3. provide the exact local/staging routes for A/B/C;
4. provide the comparison report;
5. provide its recommendation and reasons;
6. state clearly: `WAITING FOR ODONTOGRAM STRATEGY APPROVAL`;
7. perform no Phase 1 schema migration or VNext production implementation.

## 1A.5 Evidence-per-micro-task rule

A micro-task is not complete without evidence appropriate to the task, such as:

- changed file list;
- test output;
- screenshots for UI work;
- benchmark output;
- migration dry-run output;
- row-count/parity report;
- license/source reference for adopted OSS;
- explicit pass/fail against acceptance criteria.

## 1A.6 No-skip rule

The developer MUST NOT:

- merge multiple micro-tasks into an undocumented “done” claim;
- silently omit a task;
- continue through a failed phase exit gate;
- replace a required test with a verbal assertion;
- create destructive migrations to simplify implementation;
- use AI inference to manufacture historical clinical facts.

If a task is blocked, mark it `BLOCKED`, record the reason and required decision, and stop at the relevant gate.

---

# 2. Target Domain Architecture

## 2.1 Core Entities

### A. Clinical Work Item
Represents one longitudinal episode of care.

Examples:
- RCT — tooth 46
- Crown — tooth 46
- Bridge — 14–16
- Implant restoration — tooth 36
- Complete denture — upper arch

### B. Clinical Event
Permanent longitudinal patient record describing what clinically happened.

Examples:
- Caries detected on 46-D
- Working length recorded for MB canal
- RCT completed
- Crown seated

### C. Care Session
One real clinical visit instance within a work item.

### D. Clinical Step
Structured progress unit inside a session/work item.

Examples:
- Access
- Canal location
- Working length
- Cleaning and shaping
- Impression
- Try-in
- Cementation

### E. Clinical Observation
Structured measurement or fact attached to a step/event.

Examples:
- MB working length = 20.5 mm
- Shade = A2
- Implant torque = value/unit

### F. Workflow Template
Configurable procedure pathway that suggests the normal sequence without forcing it.

### G. Next Visit Request
Structured “needs booking” item generated from care progression, later converted into a real appointment.

---

# 3. Non-Negotiable UX Rules

## 3.1 Zero-Friction Charting

Target interaction budgets:

| User action | Maximum target |
|---|---:|
| Mark tooth missing | 2 interactions |
| Add whole-tooth procedure | 2–3 |
| Add caries + surface | 3 |
| Add surface restoration | 3 |
| Continue active treatment | 1–2 |
| Mark a clinical step complete | 1 |
| Finish session | 1–2 |
| Open tooth history | <=2 |
| Start lab handoff from an existing case | <=2 |
| Search rare procedure | search + one result selection |
| Undo simple entry | 1 |

## 3.2 Progressive Disclosure

Never show fields unless relevant.

Examples:
- `Missing` must not show surfaces/material/session details.
- `Composite` may request surface selection.
- `RCT` may expose endodontic details only when requested.
- `Crown` should not require lab fields at treatment-plan creation time.

## 3.3 No Mandatory Giant Modal

The default flow must move from:

`tooth -> giant treatment modal -> many unrelated fields -> save`

to:

`tooth -> quick action -> optional targeted details -> done`

Deep details must live behind contextual drawers/sheets/inspectors.

## 3.4 Undo-First, Confirm-When-Consequences-Matter

- Simple finding removal: perform + Undo.
- Destructive action with downstream lab/finance/appointments: explicit consequence-aware confirmation.

---

# 4. Delivery and Execution Rules

## 4.1 Required Branch Strategy

Create a dedicated long-lived implementation branch, for example:

`feature/unified-clinical-workflow-vnext`

Do not develop directly on `main`.

## 4.2 Required Execution Discipline

Every micro-task below must be treated as an explicit checkbox.

An agent/developer must not mark a phase complete unless:

1. every micro-task is either completed or explicitly deferred with reason;
2. every required test passes;
3. every migration verification query passes;
4. no unreviewed destructive migration exists;
5. new tables are tenant-isolated;
6. old customer data remains intact;
7. financial parity gates pass where applicable;
8. rollback path remains valid;
9. any new dependency passed the reuse/OSS/license/security gate and is wrapped appropriately;
10. clinically critical third-party behavior has Dentix-owned regression tests.

## 4.3 Forbidden Actions Until Final Contract Phase

Do **not**:

- drop `treatments`;
- drop `tooth_status`;
- drop `treatment_sessions`;
- delete old payments;
- rewrite historical payment amounts;
- regenerate stock movements during backfill;
- auto-delete suspected duplicate lab billing records;
- overwrite legacy session notes with guessed structured steps;
- use AI to create definitive clinical facts during migration;
- globally enable VNext for all tenants before phased rollout.

---


## 4.4 Mandatory Reuse-First / Open-Source Evaluation Rule

This rule applies to **this plan and all future Dentix implementation plans**.

Before a phase proposes custom implementation of a non-Dentix-specific capability, the implementer must perform this sequence:

1. **Reuse existing Dentix code/dependency first.** Search current shared components, services, utilities, dependencies, and prior V3 experiments.
2. **Search trustworthy open source second.** Prefer actively maintained projects with clear release history, automated tests, documentation, and a commercial-friendly license.
3. **Build custom only when the evaluated options fail a documented requirement.** The plan must state why.

### OSS acceptance gate

A new dependency/project cannot be adopted until all of the following are recorded in `docs/clinical-vnext/OSS_EVALUATION.md` (or the equivalent file for future plans):

- exact project/package and version evaluated;
- upstream repository and official documentation;
- license and commercial/proprietary SaaS compatibility;
- latest release/activity signal and maintenance health;
- known security concerns / dependency surface;
- React/Python/runtime compatibility with Dentix;
- bundle/runtime/performance impact where relevant;
- accessibility, mobile/touch, RTL/LTR behavior where relevant;
- whether it performs any network call, telemetry, analytics, or external data transfer;
- ability to keep patient/clinical data entirely under Dentix control;
- ability to wrap it behind a Dentix adapter so it can be replaced;
- proof-of-concept results against Dentix acceptance tests;
- final decision: `ADOPT`, `ADOPT_PARTIALLY`, `REFERENCE_ONLY`, or `REJECT`;
- fallback/exit strategy.

### License policy

Default preference:

- **Preferred:** MIT, BSD-2/3-Clause, Apache-2.0 (after notice requirements are captured).
- **Requires explicit legal/architecture review:** LGPL, MPL, unusual/custom licenses.
- **Do not embed/copy into Dentix by default:** GPL, AGPL, SSPL, source-available/proprietary code, unknown/no-license repositories.

A GPL/AGPL project may still be used as a **behavioral benchmark/reference** when legally permitted, but its source/assets must not be copied into Dentix unless a separate license decision explicitly approves it.

### Architecture rule for third-party clinical UI

Even when an odontogram/workflow library is adopted:

`Dentix Clinical Projection -> Dentix Adapter -> Third-Party Renderer`

and never:

`Third-Party Internal State -> Dentix Database Source of Truth`

No package-specific state shape may be persisted as the canonical clinical schema.

### Dependency minimization rule

Do not add a new library when an existing installed dependency already satisfies the requirement. Examples in the current frontend:

- modal/dialog/select/tooltip primitives: prefer current shared UI + existing Radix/Headless UI;
- remote server state: TanStack Query already exists;
- app/local state: Zustand already exists;
- virtualization: TanStack Virtual/react-window already exist;
- keyboard shortcuts: react-hotkeys-hook already exists;
- reorder/drag interactions: dnd-kit already exists;
- calendar: FullCalendar already exists;
- frontend tests: Vitest/Testing Library/Playwright already exist.

### Critical-dependency pinning

For any new clinically critical dependency:

- adopt through a time-boxed spike first;
- pin the initially approved version exactly in the implementation PR;
- commit the lockfile update;
- record upstream license/notice;
- add automated regression coverage around the Dentix adapter;
- update intentionally after review rather than silently relying on a floating major/minor change.


# 5. PHASE 0 — Forensic Production Data Baseline

**Objective:** Build a read-only factual inventory of current production-shaped data before schema changes.

**No writes to customer clinical or financial data in this phase.**

## P0-M01 — Freeze a Baseline Commit

- Record current `main` SHA.
- Store it in migration documentation.
- Record schema migration head.
- Record currently deployed backend/frontend versions where available.

**Acceptance:** baseline metadata committed under `docs/clinical-vnext/`.

## P0-M02 — Create Clinical VNext Documentation Directory

Create:

`docs/clinical-vnext/`

Add:
- `README.md`
- `BASELINE.md`
- `MIGRATION_RULES.md`
- `ROLLBACK.md`
- `DATA_PARITY.md`

## P0-M03 — Inventory Relevant Tables

Count per tenant:

- patients
- tooth_status
- treatments
- treatment_sessions
- appointments
- lab_orders
- payments
- lab_payments
- attachments
- treatment_material_usages
- stock_movements
- material_sessions

Persist **counts only** in generated diagnostic output.

## P0-M04 — Detect Null/Invalid Tenant Ownership

Create read-only audit queries for all affected domain tables.

Report:
- null tenant IDs;
- non-existent tenant references;
- cross-tenant FK inconsistencies.

**Gate:** no migration script may run until each anomaly class has a handling rule.

## P0-M05 — Audit Tooth Number Quality

Classify existing treatment/tooth-status values:

- valid FDI;
- valid Universal/Palmer-like string requiring mapping;
- invalid;
- null;
- multi-tooth string;
- ambiguous.

Do not mutate yet.

## P0-M06 — Audit Procedure String Cardinality

Extract distinct current `Treatment.procedure` strings per tenant.

Classify into:
- known canonical procedure;
- known synonym;
- lab-generated synthetic procedure;
- manual/custom procedure;
- unknown.

## P0-M07 — Audit Treatment Status Values

Enumerate all existing status strings.

Map only deterministic known values into:
- PLANNED
- ACTIVE
- COMPLETED
- CANCELLED
- UNKNOWN_LEGACY

## P0-M08 — Audit Tooth Status Values

Enumerate all `ToothStatus.condition` values.

Create deterministic mapping table.

Unknown values must remain `LEGACY_UNKNOWN`, not guessed.

## P0-M09 — Audit Legacy Session Data

For `Treatment.sessions` and `TreatmentSession.notes`:

- count non-empty values;
- count treatments having both old text and child session rows;
- detect duplicates if obvious;
- record date coverage.

No NLP/AI transformation.

## P0-M10 — Audit Lab-Generated Treatment Links

Detect exact links using:

`notes LIKE 'Link:LabOrder:%'`

Verify:
- referenced LabOrder exists;
- same tenant;
- patient matches;
- tooth compatibility;
- price compatibility.

## P0-M11 — Detect Potential Duplicate Lab Billing

Create a **review-only** report for likely cases where:

- a clinical crown/bridge/etc treatment exists; and
- a synthetic lab-linked treatment also exists for same patient/tooth/date window.

Classify confidence:
- deterministic duplicate;
- probable duplicate;
- ambiguous;
- not duplicate.

Do not auto-fix.

## P0-M12 — Snapshot Finance Parity Baseline

For every tenant and every active patient capture:

- treatment gross total;
- discounts;
- net charge total;
- payment total;
- outstanding balance.

Store as migration verification fixtures or export artifact.

## P0-M13 — Snapshot Inventory Baseline

Capture:
- stock quantity by stock item;
- movement count;
- material usage count;
- open material sessions.

This becomes the “must remain unchanged during backfill” baseline.

## P0-M14 — Snapshot Attachment Baseline

Capture counts and IDs by patient.

## P0-M15 — Write Phase 0 Report

Required sections:
- data anomalies;
- mapping coverage;
- migration-safe classes;
- manual-review classes;
- blocking issues.

## P0-M16 — Rehearse on a Production-Shaped Restore

Before any production backfill, restore a recent production backup/snapshot into an isolated non-production environment with equivalent PostgreSQL extensions/RLS behavior. Run the schema migration, dry-run mapper, and parity checks there first.

Do not export unnecessary patient PII into developer artifacts; generated audit artifacts should prefer IDs, counts, hashes, classifications, and redacted samples.

## P0-M17 — Re-verify Main Immediately Before Coding

If `main` has advanced beyond the baseline SHA, compare the relevant clinical/lab/finance/inventory/appointment files and update this plan's assumptions before Phase 1 begins. Do not implement against a stale baseline silently.

### Phase 0 Exit Gate

Do not proceed unless:

- all relevant rows are classified;
- financial baseline exists;
- inventory baseline exists;
- duplicate lab billing classes are documented;
- no unknown tenant-isolation issue remains unclassified;
- production-shaped restore rehearsal is successful;
- baseline SHA is still valid or documented deltas have been reconciled.

---


# 5A. PHASE 0A — Reuse / Open-Source Technical Spikes

**Objective:** decide what Dentix should reuse, wrap, partially adopt, or build before implementation work starts. This phase is mandatory but non-production and may run in parallel with the read-only data baseline.

## P0A-M01 — Create OSS Evaluation Register

Create:

`docs/clinical-vnext/OSS_EVALUATION.md`

Use the acceptance gate from Section 4.4.

## P0A-M02 — Inventory Existing Dentix Dependencies

Record whether each VNext need can already be served by installed libraries/shared components.

**Acceptance:** no duplicate UI/state/testing library is proposed without justification.

## P0A-M03 — Spike `react-advanced-odontogram`

Evaluate the current MIT-licensed `react-advanced-odontogram` package in an isolated branch/demo only.

Verify specifically:

- React 18 + current Vite compatibility;
- controlled/read-only projection from Dentix data;
- permanent, primary, and mixed dentition;
- FDI/Universal/Palmer display;
- B/M/O/D/L surface interaction;
- bridge, pontic, implant, crown, filling, endodontic visual layers;
- Arabic/RTL and English/LTR;
- touch/mobile behavior;
- keyboard accessibility;
- CSS/Tailwind collision risk;
- bundle impact;
- no telemetry/network transmission of patient data;
- ability to suppress/ignore package-owned clinical persistence/export semantics;
- whether the package's module-level/single-instance behavior prevents future side-by-side history/compare views;
- ability to wrap it behind a Dentix renderer adapter.

**Decision rule:** do not adopt the package wholesale just because it has more features. Its internal state model must not replace VNext's Clinical Core.

## P0A-M04 — Spike Lightweight `react-odontogram` as Fallback

Evaluate only as a simpler SVG/tooth-selection candidate or asset/reference source.

Because it is still a `0.x` package and provides less clinical depth, it is not the default choice without superior adapter/performance results.

## P0A-M05 — Compare Against Existing Dentix V3 Assets

Compare both OSS candidates with:

`frontend/src/features/dental/v3/`

Score:

- visual anatomy quality;
- surface geometry;
- layer extensibility;
- mobile performance;
- accessibility;
- bridge/implant semantics;
- maintainability;
- amount of custom adaptation required.

## P0A-M05A — Build Three Comparable Odontogram Prototypes

Build **three runnable, user-testable prototypes** using the same Dentix shell, same patient fixture, same clinical scenarios, and comparable visual/interaction fidelity.

The goal is a fair architectural comparison, not three production implementations.

Required routes (or equivalent clearly documented isolated routes):

- `/clinical-vnext/spike/odontogram/a`
- `/clinical-vnext/spike/odontogram/b`
- `/clinical-vnext/spike/odontogram/c`

### Prototype A — `WRAPPED_PACKAGE`

Use the best qualified external OSS odontogram renderer from P0A-M03/P0A-M04 behind a Dentix adapter.

Rules:

- Dentix owns the clinical state;
- no package persistence API becomes authoritative;
- package-specific DTOs stop at the adapter boundary;
- all patient data used in the spike must be synthetic/test data.

### Prototype B — `PARTIAL_VENDOR / HYBRID`

Use only legally reusable MIT-licensed rendering assets/primitives/geometry where they materially help, while Dentix owns:

- state;
- selection;
- layers;
- clinical semantics;
- multi-instance behavior;
- interaction orchestration.

Retain required third-party notices and source attribution records.

### Prototype C — `DENTIX_NATIVE`

Build/refine the renderer from Dentix-owned V3 SVG assets and Dentix-controlled rendering/state code.

Do not intentionally make C visually weaker than A/B merely because it is custom.

### Fair-comparison rule

All three prototypes MUST:

- use the same surrounding Dentix UI;
- use the same dimensions and responsive breakpoints;
- use the same test data;
- expose the same core interactions;
- reach enough visual polish to let the owner judge the actual product direction;
- avoid production database writes.

A prototype that is only a wireframe while another is polished does not satisfy this task.

## P0A-M05B — Required Clinical Scenario Fixture

Every A/B/C prototype MUST demonstrate the same minimum scenario set:

1. adult permanent dentition;
2. primary dentition;
3. mixed dentition;
4. Arabic RTL;
5. English LTR;
6. mobile/touch layout;
7. keyboard navigation where applicable;
8. tooth single-select;
9. multi-select;
10. direct surface selection;
11. 46-D caries;
12. 46-DO caries;
13. 46-MOD composite restoration;
14. RCT state;
15. crown;
16. missing tooth;
17. impacted/unerupted state;
18. implant fixture + implant crown representation;
19. bridge 14–16 with:
    - 14 ABUTMENT;
    - 15 PONTIC;
    - 16 ABUTMENT;
20. simultaneous EXISTING + PLANNED layers;
21. completed/planned visual distinction;
22. basic quick-action flow;
23. history/time-state rendering.

## P0A-M05C — Mandatory Multi-Instance / History Compare Test

Each prototype MUST render two independently controlled odontograms on the same page:

```text
Historical state                Current state
┌────────────────────┐          ┌────────────────────┐
│ Odontogram A       │          │ Odontogram B       │
│ as-of 2025         │          │ Today              │
└────────────────────┘          └────────────────────┘
```

Verify:

- selection in one does not mutate the other;
- filters/layers can differ independently;
- no singleton/module-state leakage occurs;
- both can be read-only;
- both remain responsive on realistic desktop/tablet sizes.

A candidate that cannot support this without unsafe hacks receives a major negative score.

## P0A-M05D — Measure and Score the Three Prototypes

Create one scorecard covering:

- clinical expressiveness;
- surface accuracy;
- bridge semantics;
- implant semantics;
- mixed dentition;
- multi-layer rendering;
- multi-instance support;
- mobile/touch UX;
- RTL;
- accessibility;
- controlled-state compatibility;
- performance/render cost;
- bundle impact;
- CSS collision risk;
- adapter complexity;
- amount of custom code still required;
- testability;
- maintenance burden;
- dependency health;
- security posture;
- license obligations;
- vendor-lock-in risk;
- ease of future replacement;
- ability to support the Zero-Friction click budget.

Do not hide failed criteria.

## P0A-M06 — Produce Odontogram Decision Report — Recommendation Only

Create:

`docs/clinical-vnext/ODONTOGRAM_SPIKE_DECISION_REPORT.md`

The report MUST include:

- screenshots of A/B/C on desktop;
- screenshots of A/B/C on mobile;
- screenshots of Arabic RTL;
- screenshots of the history-compare test;
- exact package/project versions evaluated;
- license classification;
- prototype routes;
- measured performance data;
- bundle delta where measurable;
- accessibility findings;
- failed scenarios;
- required hacks/workarounds;
- maintenance and upgrade risks;
- estimated implementation effort after selection;
- score matrix;
- recommended strategy;
- explicit reasons for rejecting or ranking the alternatives.

The developer MUST recommend one strategy but MUST NOT approve it.

## P0A-M06A — MANDATORY HUMAN ODONTOGRAM DECISION GATE — HARD STOP

After P0A-M06:

**STOP ALL FULL IMPLEMENTATION WORK.**

Do not:

- start Phase 1;
- create VNext production migrations;
- implement the production Clinical Core;
- delete spike alternatives;
- merge a chosen renderer as the production strategy;
- infer owner approval.

Keep all three prototypes runnable for owner evaluation.

Display a completion message containing:

`WAITING FOR ODONTOGRAM STRATEGY APPROVAL`

Resume only after receiving exactly one explicit owner decision:

- `APPROVE ODONTOGRAM STRATEGY: A`
- `APPROVE ODONTOGRAM STRATEGY: B`
- `APPROVE ODONTOGRAM STRATEGY: C`

## P0A-M06B — Record the Human-Approved Architecture Decision

After explicit approval, create:

`docs/clinical-vnext/ADR-001-ODONTOGRAM-STRATEGY.md`

Record:

- approved A/B/C strategy;
- date;
- evaluated versions;
- why it was chosen;
- known limitations;
- adapter boundary;
- fallback/exit strategy;
- whether any third-party assets are vendored;
- required license notices;
- conditions that would justify revisiting the decision.

Only after this ADR exists may Phase 1 begin.

## P0A-M07 — Evaluate XState v5 for Frontend Interaction State

XState is MIT-licensed and suitable for explicit state-machine UI orchestration. Evaluate it only for **transient frontend interaction modes** such as sticky charting tools or a complicated session-finish wizard.

Do **not** make XState the clinical source of truth.

Adopt only if a prototype demonstrates materially clearer/safer logic than the existing Zustand + explicit reducers/commands.

## P0A-M08 — Evaluate Backend FSM Library Only If Needed

`pytransitions/transitions` is a mature MIT-licensed Python FSM option, but it must **not** be added automatically.

First implement/benchmark the intended data-driven transition validator inside Dentix services. Adopt an external FSM only if it demonstrably reduces complexity without compromising SQL transaction boundaries, tenant checks, dynamic workflow templates, auditability, or testability.

Default decision at plan time: `REFERENCE_ONLY / DEFER`.

## P0A-M09 — Explicitly Classify Open Dental

Open Dental remains a valuable workflow benchmark, but current Open Dental versions are proprietary and historical published source is GPL-2.0.

Classification for Dentix:

`REFERENCE_ONLY`

Do not copy current or historical Open Dental code/assets into Dentix as part of this plan.

## P0A-M10 — Reject Premature Standards/Interop Dependencies

Do not add FHIR/SNOMED/ICDAS libraries merely because an odontogram package supports them. Interoperability is a separate product requirement. Keep VNext internal canonical codes mappable so standards support can be added later.

## P0A-M11 — Create Third-Party Adapter Boundary

If an odontogram library is adopted, define an internal interface such as:

`ClinicalChartRendererAdapter`

Required contract:

- receives Dentix projection DTO;
- emits Dentix-neutral selection intents;
- contains no API calls to clinical persistence;
- contains no pricing/lab/finance logic;
- can be replaced without database migration.

## P0A-M12 — OSS Phase Exit Report

Record the final matrix and approved dependencies before Phase 7 implementation.

### Phase 0A Exit Gate

Phase 0A is considered technically complete only when:

- every plausible reuse candidate has a documented evaluation;
- license is known for every adopted/copied dependency or asset;
- no GPL/AGPL/unknown-license code is embedded by accident;
- all three A/B/C odontogram prototypes are runnable;
- all three use the same clinical fixture and comparable visual/interaction fidelity;
- the mandatory multi-instance/history-compare test has been executed;
- desktop/mobile/RTL evidence exists;
- `ODONTOGRAM_SPIKE_DECISION_REPORT.md` exists;
- the developer has made a recommendation but has not self-approved it;
- the project owner has issued an explicit A/B/C approval token;
- `ADR-001-ODONTOGRAM-STRATEGY.md` records that human-approved decision;
- clinical source-of-truth remains Dentix-owned.

**Phase 1 is BLOCKED until every item above is satisfied.**

---

# 6. PHASE 1 — Additive Clinical Core Schema

**Objective:** Add VNext tables without changing current application behavior.

## P1-M01 — Create `clinical_work_items`

Required columns:

- `id`
- `tenant_id`
- `patient_id`
- `procedure_code`
- `display_name`
- `lifecycle_status`
- `primary_provider_id` nullable (planned/unassigned work may exist)
- `workflow_template_id` nullable
- `workflow_template_version` nullable
- `workflow_definition_snapshot` JSONB nullable
- `started_at` nullable
- `completed_at` nullable
- `source`
- `legacy_source_type` nullable
- `legacy_source_id` nullable
- `created_at`
- `updated_at`
- `version_id` for optimistic concurrency
- cancellation/void semantics as defined; do not hard-delete clinically meaningful history

## P1-M02 — Add Work Item Constraints

- tenant FK/index;
- patient index;
- provider index;
- status index;
- unique idempotency key for legacy mapping:
  `(tenant_id, legacy_source_type, legacy_source_id)` where source fields are not null.

## P1-M03 — Create `clinical_work_item_targets`

Columns:
- work_item_id
- tenant_id
- target_type
- tooth_number nullable
- surface nullable
- role nullable
- arch/quadrant metadata if required

Target types:
- TOOTH
- SURFACE
- ROOT
- CANAL
- QUADRANT
- ARCH
- MOUTH

## P1-M04 — Add Target Validation

Implement application validation for canonical **storage**: FDI/ISO-3950 tooth identity internally, with Palmer/Universal treated as display/input conversion only. Validate canonical surface codes:

- M
- D
- O
- I
- B
- L

## P1-M04A — Create First-Class `clinical_treatment_plans`

Required fields:
- `id`
- `tenant_id`
- `patient_id`
- `name`
- `status` (`DRAFT`, `PROPOSED`, `ACCEPTED`, `DECLINED`, `ARCHIVED`)
- `is_primary`
- `created_by`
- `created_at`
- `accepted_at` nullable
- `version_id`

Do not rely on an undefined/legacy `treatment_plan_id`.

## P1-M04B — Create `clinical_treatment_plan_phases`

Required fields:
- `id`
- `tenant_id`
- `plan_id`
- `name`
- `sequence_order`
- `status`

## P1-M04C — Create `clinical_treatment_plan_items` Membership Table

Required fields:
- `tenant_id`
- `plan_id`
- `work_item_id`
- `phase_id` nullable
- `sequence_order`
- `plan_item_status`
- `estimate_override` nullable
- `notes` nullable

A Work Item may appear in more than one alternative plan. Keep plan membership outside `clinical_work_items` so a shared proposed procedure does not require duplicate clinical episodes merely because it appears in Plan A and Plan B.

## P1-M04D — Add Cross-Tenant Ownership Guards

For every relation where simple integer FKs cannot guarantee same-tenant/same-patient ownership, enforce service-level ownership checks and test them. Examples:
- attachment -> clinical link;
- plan -> work item;
- work item -> patient/provider;
- care session -> appointment/work item;
- event -> session/work item.

## P1-M05 — Create `clinical_events`

Required:
- tenant_id
- patient_id
- work_item_id nullable
- care_session_id nullable
- event_type
- clinical_code
- lifecycle_status nullable
- provider_id nullable
- occurred_at
- source
- notes nullable
- metadata JSON/JSONB
- supersedes_event_id nullable
- created_at
- created_by

## P1-M06 — Create `clinical_event_targets`

Same target model concept as work item targets.

## P1-M07 — Create `care_sessions`

Required:
- tenant_id
- patient_id
- work_item_id
- appointment_id nullable
- provider_id
- session_number
- status
- started_at
- finished_at nullable
- clinical_summary nullable
- additional_notes nullable
- legacy_source_type nullable
- legacy_source_id nullable
- created_at

Statuses:
- DRAFT
- ACTIVE
- FINISHED
- VOIDED
- LEGACY

## P1-M08 — Create `care_session_steps`

Required:
- tenant_id
- care_session_id
- work_item_id
- workflow_step_code
- step_instance_key
- status
- sequence_order nullable
- structured_data JSONB
- started_at nullable
- completed_at nullable
- created_at

Step statuses:
- NOT_STARTED
- PARTIAL
- COMPLETED
- DEFERRED
- SKIPPED

## P1-M09 — Create `care_observations`

Required:
- tenant_id
- patient_id
- work_item_id nullable
- care_session_id nullable
- care_session_step_id nullable
- observation_code
- target_type
- target_key nullable
- value_text nullable
- value_numeric nullable
- unit nullable
- metadata JSONB
- observed_at
- provider_id

## P1-M10 — Create `workflow_templates`

Workflow template versions are immutable after publication. A work item must pin the template version and retain a definition snapshot so editing a clinic template never retroactively changes an active patient episode.

Support:
- global defaults;
- tenant overrides;
- doctor-specific override later.

Columns:
- procedure_code
- name
- specialty
- version
- is_active
- tenant_id nullable
- definition JSONB

## P1-M11 — Create `next_visit_requests`

Fields:
- tenant_id
- patient_id
- work_item_id
- origin_care_session_id
- provider_id nullable
- reason_code
- display_reason
- duration_minutes
- earliest_date nullable
- recommended_interval_days nullable
- status READY_TO_BOOK / BOOKED / CANCELLED
- appointment_id nullable

## P1-M12 — Create `clinical_attachment_links`

Fields:
- tenant_id
- attachment_id
- patient_id
- work_item_id nullable
- care_session_id nullable
- clinical_event_id nullable
- tooth_number nullable
- purpose nullable

## P1-M13 — Add RLS Policies to Every New Tenant Table

No table may ship without tenant isolation.

Special case: global workflow templates with `tenant_id IS NULL` require an explicit read policy for authenticated tenants and a restricted write path for system/super-admin maintenance. Do not accidentally make global rows writable by clinic users.

## P1-M13A — Preserve Dentix Timestamp Convention

Use the established Dentix UTC-naive persistence convention for instant-like timestamps in this project so VNext does not reintroduce timezone/reporting drift. Convert at API/UI boundaries using existing tenant-time utilities. A future timezone-storage redesign must be a separate approved migration.

## P1-M14 — Add Model Exports

Update model package registration safely.

## P1-M15 — Create Alembic Migration

Rules:
- create referenced tables/FKs in dependency-safe order (notably `workflow_templates`/work items -> care sessions -> clinical events, or add deferred FKs after both tables exist);
- additive only;
- no old column drop;
- no data rewrite except required defaults;
- reversible down migration where safe.

## P1-M16 — Schema Tests

Test:
- table creation;
- FK integrity;
- tenant isolation;
- idempotency unique constraint;
- valid nullable behavior;
- optimistic-concurrency/version behavior;
- plan membership uniqueness and cross-tenant rejection;
- immutable template version/snapshot behavior;
- migration creation order succeeds on PostgreSQL.

### Phase 1 Exit Gate

- Migration applies cleanly to empty DB.
- Migration applies cleanly to production-like copied schema.
- Old application test suite still passes.
- No old table changed destructively.

---

# 7. PHASE 2 — Canonical Clinical Catalog and Workflow Templates

## P2-M01 — Define Canonical Procedure Codes

Create stable internal codes independent from display names.

Examples:
- REST_COMPOSITE
- ENDO_RCT
- PROS_CROWN
- PROS_BRIDGE
- SURG_EXTRACTION
- IMPLANT_FIXTURE
- IMPLANT_CROWN

## P2-M02 — Define Canonical Finding Codes

Examples:
- CARIES
- FRACTURE
- ABSCESS
- MOBILITY
- PAIN
- PERIAPICAL_LESION

## P2-M03 — Define Tooth Lifecycle Codes

- PRESENT
- MISSING
- EXTRACTED
- UNERUPTED
- PARTIALLY_ERUPTED
- IMPACTED
- RETAINED_ROOT
- CONGENITALLY_ABSENT

## P2-M04 — Define Treatment Lifecycle

Domain states:
- PROPOSED
- ACCEPTED
- READY
- ACTIVE
- PAUSED
- WAITING
- AWAITING_LAB
- READY_FOR_NEXT_VISIT
- READY_TO_COMPLETE
- COMPLETED
- DECLINED
- CANCELLED
- REFERRED

UI must expose only simplified labels.

## P2-M05 — Define Visual State Model

Separate:
- finding;
- existing work;
- planned work;
- active work;
- completed work;
- historical/corrected work.

## P2-M06 — Build RCT Template v1

Suggested steps:
- diagnosis/confirm indication
- access
- canal location
- working length
- cleaning/shaping
- irrigation
- intracanal medication
- temporary restoration
- obturation
- core/definitive restoration

Classify each step:
- milestone;
- repeatable;
- canal-targeted;
- optional.

## P2-M07 — Build Crown Template v1

- preparation
- impression/scan
- temporary
- lab handoff readiness
- try-in
- adjustment
- cementation

## P2-M08 — Build Bridge Template v1

Include abutment/pontic semantics.

## P2-M09 — Build Implant Restorative Template v1

Separate fixture/abutment/crown components.

## P2-M10 — Build Complete Denture Template v1

- primary impression
- final impression
- jaw relation
- try-in
- delivery
- adjustment

## P2-M11 — Build Partial Denture Template v1

## P2-M12 — Build Composite Template v1

Single-session optimized workflow.

## P2-M13 — Build Extraction Template v1

Single-session + optional follow-up.

## P2-M14 — Add Template Versioning

Published template versions are immutable. New work items select the current applicable version; existing work items continue using their pinned snapshot unless an explicit, audited "adopt newer template" action is performed.

Never mutate historical template meaning in place.

## P2-M15 — Add Catalog Tests

Test stable codes and schema validation.

### Phase 2 Exit Gate

- all initial canonical codes documented;
- at least RCT, Crown, Bridge, Composite, Extraction, Implant Crown, Denture templates exist;
- no UI dependency yet.

---

# 8. PHASE 3 — Legacy Mapping Engine

**Objective:** Convert old records deterministically into VNext projections without deleting originals.

## P3-M01 — Create Migration Mapping Package

Suggested location:

`backend/services/clinical_migration/`

Files:
- `mapper.py`
- `procedure_map.py`
- `status_map.py`
- `tooth_map.py`
- `session_map.py`
- `lab_map.py`
- `verification.py`

## P3-M02 — Implement Treatment Procedure Mapping

Map only known strings.

Unknown strings:
- create `CUSTOM_LEGACY_PROCEDURE` code;
- preserve exact original display name in metadata.

## P3-M03 — Implement Status Mapping

Deterministic only.

## P3-M04 — Implement Tooth Number Mapping

Preserve original string/value in metadata.

Ambiguous values remain unresolved.

## P3-M05 — Map `Treatment` to Work Item

For each active treatment:
- create one work item if idempotency key absent;
- copy patient/provider/date/status;
- store legacy source fields.

## P3-M06 — Map Treatment to Clinical Event

Depending on status:
- planned -> planned procedure event;
- done -> completed procedure event;
- unknown -> legacy procedure event.

## P3-M07 — Map `ToothStatus`

Create baseline/current legacy event.

Do not fabricate timestamps if not available.

Use metadata:
- `historical_precision = UNKNOWN` where required.

## P3-M08 — Map `TreatmentSession` to Legacy Care Session

- preserve exact notes;
- preserve session date;
- set status LEGACY;
- no structured steps guessed.

## P3-M09 — Preserve `Treatment.sessions` Free Text

If non-empty and not represented by child sessions:
- store as legacy narrative event or legacy session note container.

Never drop.

## P3-M10 — Deterministic Canal Length Parsing Only

If strongly parseable structured format exists, map to observations.

Otherwise preserve original text.

## P3-M11 — Map Lab Linked Synthetic Treatment

When exact `Link:LabOrder:<id>` exists:
- create link relationship in migration metadata;
- do not delete treatment;
- do not create duplicate work item if it represents same source pair under deterministic rule.

## P3-M12 — Mark Ambiguous Lab Duplicates

Store migration review classification, not automatic correction.

## P3-M13 — Idempotency Tests

Run mapper twice.

Expected:
- second run inserts zero duplicates.

## P3-M14 — Tenant Isolation Tests

Cross-tenant legacy IDs must never cross-link.

### Phase 3 Exit Gate

- deterministic mapping coverage report produced;
- unknown/ambiguous rows preserved;
- mapper is idempotent;
- no source row modified.

---

# 9. PHASE 4 — Controlled Backfill

## P4-M01 — Add Dry-Run Mode

Outputs counts without DB inserts.

## P4-M02 — Add Tenant-Scoped Execution

Backfill exactly one tenant at a time.

## P4-M03 — Add Batch Processing

Bound memory and transaction size.

## P4-M04 — Add Resume Checkpointing

Backfill can safely restart after interruption.

## P4-M05 — Backfill Patients’ Legacy Treatments

## P4-M06 — Backfill Tooth Status Events

## P4-M07 — Backfill Legacy Care Sessions

## P4-M08 — Backfill Exact Lab Relationships

## P4-M09 — Backfill Attachment Association Placeholders Only Where Deterministic

Do not move files.

## P4-M10 — Verify Record Counts

Per tenant compare:
- classified legacy treatment count;
- generated work-item mappings;
- generated legacy session count.

## P4-M11 — Verify Source Preservation

Checksums/counts of old tables unchanged.

## P4-M12 — Verify Inventory Invariance

Stock quantity and movement counts must remain exactly unchanged.

## P4-M13 — Verify Payment Invariance

Payment IDs, amounts, patient IDs unchanged.

## P4-M14 — Generate Backfill Report

### Phase 4 Exit Gate

- no old data modification;
- stock unchanged;
- payments unchanged;
- all migrated rows trace back to source IDs;
- no duplicate mappings.

---

# 10. PHASE 5 — Compatibility and Projection Layer

## P5-M01 — Create Clinical Projection Service

Responsibilities:
- build current odontogram state from clinical events/work items;
- expose history-as-of queries;
- combine migrated legacy records and VNext-native records.

## P5-M02 — Implement `as_of` Projection

Support chart state at date/time.

## P5-M03 — Implement Tooth Summary Projection

Return:
- tooth lifecycle;
- active findings;
- existing work;
- planned work;
- active work;
- completed work;
- recent history.

## P5-M04 — Implement Work Item Summary Projection

## P5-M05 — Implement Patient Clinical Workspace Aggregate

Single optimized payload for the chart screen.

## P5-M06 — Add Legacy Read Fallback

If a patient is not backfilled/enabled:
- old read path remains valid.

## P5-M07 — Add Feature Flag

Suggested:
- `clinical_vnext_enabled`
- tenant scoped.

## P5-M08 — Add Internal Shadow Read Comparison

For migrated patients compare key current states between old/new projections where semantically comparable.

## P5-M09 — Add Projection Caching Strategy

Avoid N+1 per tooth.

## P5-M10 — Performance Benchmark

Set budget for chart aggregate API.

### Phase 5 Exit Gate

- VNext projection can render full-mouth state from old migrated data;
- no writes required;
- response uses bounded query count.

---

# 11. PHASE 6 — Clinical API and Command Layer

## P6-M01 — Create Clinical Command Service

Centralize writes.

Do not let frontend directly create disconnected rows.

## P6-M02 — Add Work Item Create API

Example:

`POST /api/v1/clinical/work-items`

## P6-M03 — Add Work Item Update/Transition API

Validate lifecycle transitions.

## P6-M04 — Add Finding Create API

Support whole-tooth and surface-targeted findings.

## P6-M05 — Add Bulk Finding API

One request for multi-tooth charting.

## P6-M06 — Add Procedure Create API

## P6-M07 — Add Bulk Procedure API

## P6-M08 — Add Clinical Event Correction API

Use supersede/correction semantics.

## P6-M09 — Add Clinical Workspace Read API

Example:

`GET /api/v1/patients/{id}/clinical-workspace`

## P6-M10 — Add Tooth Detail API

## P6-M11 — Add History API

Support `as_of` and timeline.

## P6-M12 — Add Permission Enforcement

Use existing clinical/treatment permissions appropriately.

## P6-M13 — Add Tenant Security Tests

## P6-M14 — Add API Contract Tests

## P6-M15 — Add Command Idempotency Keys

Create/finish/send commands that can be double-submitted from mobile/PWA/network retries must accept or derive an idempotency key and return the prior successful result instead of creating duplicate clinical work, sessions, lab jobs, or charges.

## P6-M16 — Add Optimistic Concurrency Handling

Require `version_id`/expected-version checks for high-risk edits to work items, plans, and active care sessions. Return conflict rather than silently overwriting another clinician's changes.

### Phase 6 Exit Gate

- command service is sole supported VNext writer;
- bulk operations supported;
- tenant isolation tested;
- old APIs still work.

---

# 12. PHASE 7 — VNext Odontogram Read-Only UI

## P7-M01 — Create Feature Directory

`frontend/src/features/clinical-chart/`

## P7-M02 — Create `ClinicalChartWorkspace`

## P7-M03 — Build Responsive Layout Shell

Desktop:
- chart center;
- contextual inspector on demand;
- compact toolbar.

Mobile:
- full-mouth overview;
- quadrant focus;
- bottom sheet.

## P7-M04 — Implement the Phase-0A Odontogram Decision Behind an Adapter

Use only the human-approved strategy recorded in `docs/clinical-vnext/ADR-001-ODONTOGRAM-STRATEGY.md` (`WRAPPED_PACKAGE`, `PARTIAL_VENDOR`, or `DENTIX_RENDERER`). If that ADR does not exist, Phase 7 is blocked.

If third-party code/assets are used, preserve license notices and keep all imports behind a Dentix adapter boundary. Existing V3 tooth SVG assets remain a valid internal fallback.

Do not wire the old V3 architecture directly.

## P7-M05 — Implement Layered Tooth Renderer

Layers:
- base anatomy;
- findings;
- existing/completed work;
- planned/active overlays;
- selection/focus.

## P7-M06 — Implement Surface Geometry

Clickable geometry prepared even if read-only phase does not write yet.

## P7-M07 — Implement Adult Dentition

## P7-M08 — Implement Primary Dentition

## P7-M09 — Implement Mixed Dentition Projection

No global boolean-only model.

## P7-M10 — Implement Notation Display

- FDI primary target;
- Palmer/Universal display conversion optional.

## P7-M11 — Implement Compact Legend

## P7-M12 — Implement Tooth Inspector Read Mode

Tabs only when needed:
- overview;
- findings;
- treatment;
- history;
- images.

## P7-M13 — Implement Timeline Read Mode

## P7-M14 — Implement As-Of History Slider

## P7-M15 — Implement Mobile Bottom Sheet

## P7-M16 — Accessibility Pass

Color + pattern + icon; keyboard focus; target sizes.

## P7-M17 — Screenshot/Visual Regression Tests

### Phase 7 Exit Gate

- current customer data renders in VNext chart;
- no writes required;
- mobile does not rely on 700px horizontal-scroll chart;
- baseline visual regression suite exists.

---

# 13. PHASE 8 — Zero-Friction Charting Writes

## P8-M01 — Implement Tooth Selection State

## P8-M02 — Implement Quick Action Launcher

Contextual actions only.

## P8-M03 — Implement Tooth-First Flow

`tooth -> action -> surface if needed -> done`

## P8-M04 — Implement Procedure-First Flow

`action -> select tooth/surfaces -> done`

## P8-M05 — Implement Sticky Tool Mode

Example: choose Caries once, chart multiple surfaces, finish.

## P8-M06 — Implement Multi-Select

- multiple teeth;
- quadrant;
- arch;
- clear selection.

## P8-M07 — Implement Surface Interaction

No dropdown needed for common cases.

## P8-M08 — Implement Favorites

## P8-M09 — Implement Recents

## P8-M10 — Implement Search

Rare procedures/findings searchable quickly.

## P8-M11 — Implement Smart Defaults

Context-only; never hide clinically important differences.

## P8-M12 — Implement Undo Stack

For reversible simple operations.

## P8-M13 — Implement Consequence-Aware Remove

If downstream entities exist, display consequences.

## P8-M14 — Measure Click Budget

Add UX test checklist for common scenarios.

## P8-M15 — Deprecate Automatic Giant Modal Opening

Do not delete old modal yet.

### Phase 8 Exit Gate

Common tasks meet click budget.

---


# 13A. PHASE 8A — First-Class Treatment Plans, Alternatives, and Phases

**Objective:** make Treatment Plans a real grouping/view over canonical Work Items without creating duplicate treatments or disconnected plan records.

## P8A-M01 — Create Treatment Plan Service

Tenant/patient-scoped CRUD/transitions for plan aggregates.

## P8A-M02 — Add Plan Create API

Create `Plan A`, `Plan B`, etc. without duplicating patient data.

## P8A-M03 — Add Phase CRUD/Reorder

Use existing dnd-kit only if drag/reorder materially improves UX; otherwise simple move controls are acceptable. Do not add a second drag/drop library.

## P8A-M04 — Add Work Item Membership API

Attach/detach/move a Work Item within a plan/phase without recreating the Work Item.

## P8A-M05 — Support Shared Work Items Across Alternative Plans

Example: the same RCT 46 may be common to Plan A and Plan B. Membership must not create two independent RCT clinical episodes.

## P8A-M06 — Add Plan Status Lifecycle

- DRAFT
- PROPOSED
- ACCEPTED
- DECLINED
- ARCHIVED

## P8A-M07 — Accept Plan Without Completing Treatment

Plan acceptance transitions eligible work items according to policy but does not mark care completed and does not create a payment.

## P8A-M08 — Preserve Alternative Plans

Accepting Plan A should archive/mark other alternatives appropriately according to user action; never silently delete them.

## P8A-M09 — Chart Plan Overlay

Allow filters such as:
- Current findings
- Existing work
- Plan A
- Plan B
- All active plans

## P8A-M10 — Plan Estimate Projection

Show estimated fees without recognizing them as actual revenue until billing policy says a charge is generated.

## P8A-M11 — Plan Comparison UX

Compare treatment composition and estimates without side effects.

## P8A-M12 — Legacy Rule

Do not invent historical Treatment Plans for old Treatments unless plan membership is deterministically known. Legacy treatments may appear as historical/unplanned completed work.

## P8A-M13 — Plan Concurrency Tests

Prevent two users from accepting/reordering the same plan with lost updates.

## P8A-M14 — Plan E2E Scenario

- create Plan A and Plan B;
- share one Work Item between both;
- accept Plan A;
- verify no duplicated work item, charge, or lab order;
- verify Plan B remains historical/alternative, not deleted.

### Phase 8A Exit Gate

- Treatment Plans exist as first-class aggregates;
- alternatives do not require duplicate clinical care episodes;
- plan estimates are not confused with recognized revenue;
- chart can overlay selected plans with low-friction UX.

---

# 14. PHASE 9 — Care Pathway, Sessions, and Resume Engine

This is a critical phase.

## P9-M01 — Create Care Session Service

## P9-M02 — Add `Start Session` Command

Start a new care session linked to work item and optional appointment.

## P9-M03 — Add `Finish Session` Command

Transactionally finalize structured steps and session metadata.

## P9-M04 — Add Step Add/Update API

## P9-M05 — Add Partial Step Support

Example:
- MB completed;
- ML completed;
- D partial.

## P9-M06 — Add Repeatable Step Support

Examples:
- irrigation;
- temporary restoration;
- medication.

## P9-M07 — Add Observation API

## P9-M08 — Implement RCT Structured UI

Start minimal:
- access;
- canals located;
- working length;
- cleaning/shaping;
- medication;
- obturation.

## P9-M09 — Implement Canal Target UI

## P9-M10 — Implement Working Length Structured Entry

## P9-M11 — Implement Session Finish Sheet

Must remain compact.

## P9-M12 — Build Resume Engine Service

Must answer deterministically:
- what is completed;
- what is partial;
- what remains;
- what is waiting;
- suggested next step.

## P9-M13 — Build `Continue Treatment` Card

Example:

`Continue RCT 46`

## P9-M14 — Generate Human-Readable Clinical Summary

Structured-first, narrative-second.

Do not require AI.

## P9-M15 — Preserve Free Notes

Additional notes always allowed.

## P9-M16 — Add Template Deviation Support

- add custom step;
- skip;
- defer;
- repeat.

## P9-M17 — Add Session Finalization and Audit Trail

Finishing a session locks the finalized clinical snapshot. Normal edits after finalization are forbidden. Corrections/addenda must be explicit, attributable, timestamped, and represented through superseding/correction clinical events rather than silent mutation.

## P9-M17A — Add Concurrent Session Protection

Prevent duplicate active sessions for the same appointment/work item when the workflow policy says only one may be active, and make repeated `Finish Session` requests idempotent.

## P9-M18 — Migrate New Session Writes Away From Legacy Free-Text-Only Model

Keep legacy read compatibility.

## P9-M19 — Session UX Click-Budget Tests

## P9-M20 — RCT Scenario Integration Test

Scenario:
- Session 1 access;
- Session 2 WL + partial shaping;
- Session 3 complete shaping + obturation;
- verify resume state each time.

### Phase 9 Exit Gate

- doctor can resume a multi-session case without reading old notes;
- no mandatory giant checklist;
- every session has structured progress + optional narrative.

---

# 15. PHASE 10 — Appointment Integration

## P10-M01 — Link Care Session to Appointment

## P10-M02 — Implement Next Visit Request Creation

## P10-M03 — Auto-Suggest Next Visit from Workflow Template

Suggestion only.

## P10-M04 — Reception Queue UI

Show patients needing booking.

## P10-M05 — Convert Request to Appointment

Do not duplicate request.

## P10-M06 — Populate Appointment Reason from Work Item

## P10-M07 — Suggest Duration

Template/doctor preference based.

## P10-M08 — Do Not Auto-Book Without User Action

## P10-M09 — Handle Appointment Cancellation

Do not cancel work item automatically.

## P10-M10 — Handle Appointment Completion

Update only visit/session status according to explicit clinical workflow.

## P10-M11 — Integration Tests

## P10-M12 — Next-Visit Idempotency and Race Tests

A network retry or two reception users must not convert one Next Visit Request into duplicate appointments.

### Phase 10 Exit Gate

Reception can see “what this patient needs next” without asking the doctor.

---

# 16. PHASE 11 — Smart Laboratory Integration

## P11-M01 — Add Real FK From Lab Order to Clinical Work Item

Add:
- `clinical_work_item_id` nullable;
- `origin_care_session_id` nullable.

## P11-M02 — Add Migration for Exact Legacy Lab Links

## P11-M03 — Stop Using `notes` as the Primary Relationship for New Data

Keep old note parsing only for compatibility.

## P11-M04 — Create Lab Requirement Definition

Not every planned crown should instantly create/send an order.

## P11-M05 — Add `LAB_READY` Workflow Trigger

Examples:
- preparation + scan done.

## P11-M06 — Add One-Tap Lab Handoff Sheet

Prefill:
- patient;
- teeth;
- work type;
- material if known;
- shade if known;
- provider.

## P11-M07 — Allow Missing Optional Lab Data

Mark as `needs shade`, etc.

## P11-M08 — Create Lab Order Without Creating New Clinical Treatment

Critical requirement.

## P11-M09 — Decouple Lab Patient Price From Synthetic Treatment Creation

Introduce compatibility billing projection while finance remains legacy-backed.

## P11-M10 — Implement Lab Status Mapping

- pending;
- in production;
- try-in;
- ready;
- received;
- completed/cancelled.

## P11-M11 — Reflect Lab State in Clinical Work Item

Example: `Waiting for lab`.

## P11-M12 — Do Not Auto-Complete Clinical Treatment When Lab Is Ready

## P11-M13 — Shade/Material Change Synchronization

If lab already sent, require explicit update action.

## P11-M14 — Bridge Multi-Tooth Semantics

Lab order must inherit correct abutment/pontic targets.

## P11-M15 — Lab Duplicate Billing Regression Test

## P11-M16 — Lab Handoff Idempotency

Assign an idempotent requirement/handoff key so retries cannot create duplicate lab orders. Allow an explicit remake/new-lab-cycle action to create a new order intentionally.

Ensure one crown does not become two patient charges.

### Phase 11 Exit Gate

- new lab-backed procedure is entered clinically once;
- lab order derives from it;
- no synthetic duplicate clinical treatment is created.

---

# 17. PHASE 12 — Inventory Integration at Session Level

## P12-M01 — Explicitly Distinguish `MaterialSession` From `CareSession`

Rename variables/UI labels where ambiguity exists.

## P12-M02 — Add `care_session_id` to Clinical Material Usage Model

Do not reuse legacy `session_id`.

## P12-M03 — Preserve Existing Treatment Material Usage

## P12-M04 — Create Session Material Suggestion Service

Based on:
- procedure;
- step;
- template;
- learned/default BOM.

## P12-M05 — Do Not Deduct Stock at Plan Creation

## P12-M06 — Deduct/Confirm at Actual Use Point

Usually session finish or explicit use action.

## P12-M07 — Support Different Materials Per Session

## P12-M08 — Keep Divisible Material Learning Compatible

## P12-M09 — Aggregate Work Item Material Cost

Sum all care-session usage.

## P12-M10 — Inventory Invariance Migration Test

Historical backfill cannot change physical stock.

## P12-M11 — Endo Material Scenario Test

Different materials in Sessions 1/2/3.

### Phase 12 Exit Gate

Inventory consumption follows actual care sessions without rewriting old movement history.

---

# 18. PHASE 13 — Finance Integration and Financial Parity

This phase must be treated as high risk.

## P13-M01 — Define Billing Policy Model

Possible policies:
- full at start;
- full at completion;
- split;
- per session;
- custom milestones.

## P13-M02 — Do Not Change Existing Customer Financial Source Yet

Legacy Treatment-backed totals remain authoritative during shadow mode.

## P13-M03 — Add Work Item Billing Projection

Map a work item to the existing billing semantics without duplicate treatment rows where possible.

## P13-M04 — Design `clinical_charges` Table

Only introduce after parity design is validated.

Required fields likely:
- tenant_id
- patient_id
- work_item_id
- amount
- discount
- status
- generated_at
- policy snapshot
- legacy_treatment_id nullable

## P13-M05 — Preserve Existing Payments Unchanged

Do not invent payment-to-charge allocations for legacy payments during this project unless an independently verified deterministic rule exists. Patient-level payment history remains authoritative.

## P13-M06 — Create Finance Shadow Calculator

Compute:
- old total;
- new projected total;
- difference.

## P13-M07 — Run Per-Patient Parity

Expected difference: `0.00` before any finance read cutover.

## P13-M08 — Run Per-Tenant Parity

## P13-M09 — Detect Legacy Lab Double-Charge Cases

Do not automatically delete.

## P13-M10 — Build Manual/Rule-Based Remediation Workflow for Deterministic Duplicates

Must include audit and rollback.

## P13-M11 — Add Doctor Share Compatibility Tests

If doctor share logic depends on Treatment rows, maintain parity.

## P13-M12 — Cut Finance Reads Only Behind Flag

## P13-M13 — Keep Payments Table Stable

## P13-M14 — Add Financial Regression Suite

### Phase 13 Exit Gate

No cutover unless:

- every active patient balance matches exactly;
- tenant totals match exactly;
- payment rows unchanged;
- lab duplication behavior is explicitly classified.

---

# 19. PHASE 14 — Files, Images, and Clinical Context

## P14-M01 — Keep Attachment Storage Unchanged

## P14-M02 — Add Context Links Only

## P14-M03 — Link Image to Tooth

## P14-M04 — Link Image to Work Item

## P14-M05 — Link Image to Care Session

## P14-M06 — Add Purpose Codes

Examples:
- PRE_OP_PA
- WORKING_LENGTH_PA
- MASTER_CONE
- POST_OP_PA
- SHADE_PHOTO
- SCAN
- LAB_RX

## P14-M07 — Show Relevant Images in Tooth Inspector

## P14-M08 — Show Relevant Images in Session View

## P14-M09 — Add Existing Attachment Migration Only When Deterministic

Otherwise patient-level only.

### Phase 14 Exit Gate

No file duplicated or moved unnecessarily.

---

# 20. PHASE 15 — Integration Events and Module Synchronization

## P15-M01 — Keep Clinical Events and Outbox Domain Events Separate

Permanent patient record != integration message.

## P15-M02 — Define Integration Event Catalog

Examples:
- `clinical.work_item.created`
- `clinical.session.started`
- `clinical.session.finished`
- `clinical.step.completed`
- `clinical.work_item.completed`
- `clinical.lab.ready`
- `clinical.next_visit.requested`

## P15-M03 — Emit Events Transactionally

Use existing outbox infrastructure.

## P15-M04 — Build Idempotent Event Handlers

Each side-effect handler must have a durable deduplication key/inbox or an equivalent database uniqueness guarantee. The existing outbox can redeliver after crashes; "the worker normally runs once" is not an idempotency strategy.

## P15-M05 — Appointment Handler

## P15-M06 — Lab Handler

## P15-M07 — Inventory Handler

## P15-M08 — Timeline/Analytics Handler

## P15-M09 — Notification Handler

## P15-M10 — Finance Handler Only for Non-Source-of-Truth Side Effects

Critical financial writes requiring atomicity remain synchronous/domain-service controlled.

## P15-M11 — Retry/Failure Tests

Reuse current outbox recovery design.

## P15-M12 — Duplicate Delivery Tests

Handlers must not duplicate side effects.

### Phase 15 Exit Gate

A clinical action updates related modules without requiring repeated user entry and without unsafe event duplication.

---

# 21. PHASE 16 — Mobile, RTL, Accessibility, and Performance Hardening

## P16-M01 — Mobile Full-Mouth Overview

## P16-M02 — Quadrant Focus Navigation

## P16-M03 — Bottom Sheet Interaction

## P16-M04 — Large Touch Targets

## P16-M05 — No Hover Dependency

## P16-M06 — RTL Layout Audit

Arabic must not be an afterthought.

## P16-M07 — English/LTR Audit

## P16-M08 — Keyboard Shortcuts on Desktop

Optional power-user layer.

Potential shortcuts:
- C caries
- F filling
- R RCT
- X extraction
- Esc cancel tool
- Ctrl/Cmd+Z undo

## P16-M09 — Screen Reader Labels

## P16-M10 — Color-Blind Safety

Never rely on color alone.

## P16-M11 — Render Performance

Memoize tooth renderers.

## P16-M12 — API Performance

Avoid one request/query per tooth.

## P16-M13 — Cache/Invalidation Rules

## P16-M14 — Patient Page Performance Regression Test

### Phase 16 Exit Gate

The VNext chart is genuinely usable on mobile/tablet and does not reintroduce known slow patient-page behavior.

---

# 22. PHASE 17 — Rollout, Shadow Mode, and Controlled Cutover

## P17-M01 — Internal Tenant Only

## P17-M02 — Read-Only VNext Rollout

## P17-M03 — Enable VNext Writes for Internal Tenant

## P17-M04 — Monitor Error Rates

## P17-M05 — Monitor Data-Parity Metrics

## P17-M06 — Pilot Clinic

## P17-M07 — Small Percentage Rollout

## P17-M08 — Tenant-Specific Rollback Toggle

## P17-M09 — Expand to 25%

## P17-M10 — Expand to 50%

## P17-M11 — Expand to 100%

Only after gates pass.

## P17-M12 — Keep Legacy Read Compatibility

### Phase 17 Exit Gate

VNext is default only after stable staged rollout.

---

# 23. PHASE 18 — Legacy Retirement and Contract Phase

Do not start immediately after launch.

## P18-M01 — Observe Stability Window

## P18-M02 — Stop New Legacy Session Writes

## P18-M03 — Stop New Legacy Tooth Status Writes

Only after VNext equivalents are proven.

## P18-M04 — Stop Synthetic Lab Treatment Creation

## P18-M05 — Stop Legacy Chart Writer

## P18-M06 — Mark Old APIs Deprecated

## P18-M07 — Remove Dead UI Code

Candidates eventually include old chart/modal-specific pathways no longer used.

## P18-M08 — Keep Historical Tables Read-Only Initially

## P18-M09 — Re-run Finance/Inventory/Patient Parity

## P18-M10 — Decide Whether Physical Table Removal Is Ever Necessary

Prefer historical preservation unless there is a strong operational reason.

---

# 24. Required Migration Mapping Rules

| Legacy source | VNext destination | Rule |
|---|---|---|
| Patient | same Patient | do not recreate |
| Treatment | Work Item + Event | additive mapping |
| ToothStatus | legacy baseline/current event | preserve uncertainty |
| TreatmentSession | Legacy Care Session | preserve free text |
| Treatment.sessions text | legacy narrative/session artifact | do not discard |
| canal_lengths | Observation only if deterministic | otherwise preserve text |
| LabOrder | link to Work Item when deterministic | keep original order |
| synthetic lab Treatment | compatibility/billing relationship | do not auto-delete |
| Payment | unchanged | never recreate |
| Appointment | unchanged; link only when deterministic/new | no guessed history |
| Attachment | unchanged; add links | do not re-upload |
| StockMovement | unchanged | never regenerate during backfill |
| TreatmentMaterialUsage | preserve; bridge gradually | do not confuse material session with care session |

---

# 25. Critical Data-Safety Rules

## 25.1 Clinical Certainty Rule

Never convert free text into definitive structured facts unless the mapping is deterministic.

Bad migration:

`"Access done, canals difficult" -> Access=COMPLETED, Shaping=PARTIAL`

unless explicitly encoded and verified.

Safe migration:

store original note under legacy session and mark structured progress unknown.

## 25.2 Financial Immutability Rule

Historical payments:
- no amount rewrite;
- no patient change;
- no deletion;
- no renumbering.

## 25.3 Inventory Invariance Rule

Backfill must not:
- deduct stock;
- open/close material sessions;
- create usage stock movements;
- reverse historical movement.

## 25.4 Tenant Rule

Every new relation must validate same-tenant ownership.

---

# 26. End-to-End Acceptance Scenarios

## Scenario A — New Surface Caries

1. Open patient.
2. Tap tooth 46.
3. Tap Caries.
4. Tap D surface.
5. Save automatically/quick confirm.

Verify:
- clinical event created;
- chart updates;
- no treatment charge created unless policy says so;
- undo available.

## Scenario B — Multi-Session RCT

Session 1:
- create RCT 46;
- access complete;
- canals located.

Session 2:
- resume card appears;
- WL recorded MB/ML/D;
- shaping MB/ML complete, D partial;
- finish session;
- next visit request generated.

Session 3:
- resume shows D shaping pending;
- complete shaping;
- obturation complete;
- mark RCT complete.

Verify:
- all three sessions preserved;
- structured observations exist;
- chart shows completed RCT;
- timeline correct;
- materials per session preserved;
- finance follows policy exactly once.

## Scenario C — Crown with Lab

1. Create Crown 46 planned.
2. Do preparation session.
3. Record scan.
4. System marks case lab-ready.
5. Doctor taps Send to Lab.
6. Lab order prefilled.
7. Lab marked ready.
8. Chart/work item shows waiting/ready state.
9. Clinical treatment remains incomplete.
10. Cementation session completes work item.

Verify:
- no duplicate patient charge;
- lab order linked by FK;
- shade/material sync rules work;
- finance correct.

## Scenario D — Legacy Patient

Patient has:
- 7 old Treatments;
- 3 ToothStatus records;
- 2 old TreatmentSessions;
- 1 LabOrder;
- 4 Payments.

After backfill:
- old rows unchanged;
- VNext chart renders legacy state;
- legacy notes visible;
- payment total identical;
- outstanding balance identical;
- stock unchanged.

## Scenario E — Mobile

Complete common workflow without horizontal scrolling or giant modal.

---

# 27. Automated Test Matrix

Required categories:

### Unit
- canonical mappings;
- lifecycle transitions;
- projection rules;
- resume engine;
- workflow template interpretation;
- lab status mapping;
- billing policy calculation.

### Integration
- work item + event creation;
- session + step transactions;
- next visit -> appointment;
- lab handoff;
- session inventory use;
- finance projection;
- attachment links;
- outbox event processing.

### Migration
- idempotency;
- tenant isolation;
- old row immutability;
- financial parity;
- stock invariance;
- unknown legacy value preservation.

### Frontend

- third-party renderer adapter contract tests (when applicable);
- no third-party renderer state is treated as persisted clinical truth;
- tooth selection;
- surface selection;
- sticky tool;
- multi-select;
- quick action;
- undo;
- resume card;
- finish session;
- mobile bottom sheet;
- RTL.

### End-to-End
At minimum the five scenarios above.

---

# 28. Observability Requirements

Add metrics/logs for:

- VNext API latency;
- projection latency;
- backfill counts;
- migration failures;
- parity mismatch count;
- duplicate side-effect prevention;
- outbox failures;
- session completion failure;
- lab-link failure;
- finance projection mismatch;
- tenant rollout state.

Never log sensitive clinical details unnecessarily.

---

# 29. Suggested Code Organization

## Backend

```text
backend/
  models/
    clinical_vnext.py

  schemas/
    clinical_vnext.py

  services/
    clinical/
      command_service.py
      projection_service.py
      work_item_service.py
      event_service.py
      session_service.py
      resume_service.py
      workflow_template_service.py
      appointment_bridge.py
      lab_bridge.py
      inventory_bridge.py
      finance_bridge.py
      attachment_bridge.py

    clinical_migration/
      mapper.py
      treatment_map.py
      status_map.py
      tooth_map.py
      session_map.py
      lab_map.py
      verification.py

  routers/
    clinical_vnext.py
```

Exact file structure may be adapted to repository conventions, but business logic must remain centralized and not spread across routers/components.

## Frontend

```text
frontend/src/features/clinical-chart/
  ClinicalChartWorkspace.jsx

  components/
    ChartToolbar/
    Odontogram/
    Tooth/
    ToothSurfaces/
    QuickActions/
    ToothInspector/
    MultiSelectToolbar/
    HistoryTimeline/
    ClinicalLegend/
    ResumeCard/
    CareSessionSheet/
    MobileChart/

  hooks/
    useClinicalWorkspace.js
    useChartSelection.js
    useClinicalCommands.js
    useCareSession.js
    useResumeState.js

  domain/
    clinicalCodes.js
    surfaces.js
    dentition.js
    visualRules.js
```

---

# 30. Phase-by-Phase Commit Discipline

Recommended commit pattern:

- one schema/migration concern per commit;
- one service capability per commit;
- one UI behavior per commit;
- tests in same commit when practical;
- no giant “implement clinical vnext” commit.

Example:

- `feat(clinical): add work item models`
- `feat(clinical): add care session schema`
- `feat(clinical): add deterministic legacy treatment mapper`
- `test(clinical): verify migration idempotency`
- `feat(chart): add layered tooth renderer`
- `feat(session): add rct resume state`

---

# 31. Mandatory Definition of Done for Every Micro-Task

A micro-task is not done because code compiles.

It is done only if:

- code exists;
- tests exist where relevant;
- tests pass;
- tenant ownership is validated;
- API errors are handled;
- no duplicate side effect can occur;
- migration behavior is idempotent if applicable;
- user-facing behavior respects click budget if applicable;
- RTL/mobile impact is considered if applicable;
- existing Dentix code/dependencies were reused where appropriate;
- any new dependency has an OSS/license/security evaluation and adapter/fallback strategy where applicable;
- third-party clinical behavior has Dentix-owned tests where clinically significant;
- docs/checklist updated.

---

# 32. Final Go-Live Checklist

Before release also verify:
- approved OSS/dependency register is current;
- third-party notices/licenses required for shipped code/assets are present;
- lockfiles match approved versions;
- no unexpected telemetry/network calls exist in adopted clinical UI packages;
- dependency/license/security scan has no unresolved release blocker.


Before VNext becomes default for all tenants:

- [ ] 100% patient IDs preserved
- [ ] 100% payment IDs/amounts preserved
- [ ] old treatment records preserved
- [ ] legacy session notes preserved
- [ ] lab orders preserved
- [ ] attachment records preserved
- [ ] stock quantities unchanged by backfill
- [ ] financial old/new patient balance difference = 0.00
- [ ] tenant aggregate financial difference = 0.00
- [ ] zero cross-tenant clinical links
- [ ] zero duplicate migration mappings
- [ ] common chart tasks meet click budget
- [ ] RCT 3-session scenario passes
- [ ] crown/lab scenario passes
- [ ] mobile scenario passes
- [ ] RTL scenario passes
- [ ] rollback flag tested
- [ ] old UI remains available during rollback window
- [ ] outbox duplicate-delivery tests pass
- [ ] observability dashboards/logs ready

---

# 33. Recommended Implementation Order Summary

Do not start with visual redesign.

The correct order is:

1. production data audit + production-shaped restore rehearsal;
2. reuse/open-source research and three comparable odontogram prototypes;
3. odontogram comparison report + **MANDATORY HUMAN A/B/C DECISION — HARD STOP**;
6. record approved renderer strategy in ADR-001;
7. additive Clinical Core + first-class Treatment Plan schema;
6. canonical clinical codes and immutable workflow templates;
7. deterministic legacy mapper;
8. controlled backfill and parity verification;
9. projection/read model;
10. command API with idempotency/concurrency controls;
11. read-only VNext chart behind renderer adapter;
12. zero-friction chart writes;
13. first-class treatment plans, alternatives, phases, and overlays;
14. structured care sessions + Resume Engine;
15. appointment/Next Visit integration;
16. laboratory integration without synthetic duplicate treatments;
17. session-level inventory integration;
18. finance shadow projection, exact parity, then controlled cutover;
19. files/images clinical context;
20. integration events with durable consumer idempotency;
21. mobile/RTL/accessibility/performance hardening;
22. staged tenant rollout;
23. legacy writer retirement only after stability/parity gates.

---


# 34A. Third Verification Findings Resolved Before Implementation

The pre-implementation re-audit found and corrected the following plan-level gaps:

1. **Treatment Plan aggregate was missing.** The earlier plan referenced `treatment_plan_id` without defining a real plan domain. VNext now uses first-class plans, phases, and membership records.
2. **Alternative plans could have duplicated treatments.** Membership is separated from Work Items so one canonical care episode can appear in more than one proposal.
3. **Workflow-template drift risk.** Active episodes now pin an immutable template version/snapshot; later clinic template edits do not rewrite patient history or resume logic.
4. **Migration FK ordering risk.** Care Sessions must exist before a Clinical Event FK references them, or the FK must be added later. PostgreSQL migration order is now an explicit test.
5. **Legacy provider nullability.** Old sessions/treatments may lack a provider, so the DB allows migration-safe nulls while new commands enforce provider requirements.
6. **Concurrent/double-submit risk.** Work Items, Plans, and Care Sessions require version/idempotency protection. Mobile/PWA retries must not duplicate sessions, lab orders, appointments, or charges.
7. **Finalized clinical record mutability.** Finished sessions are now locked; corrections become attributable addenda/superseding events instead of silent edits.
8. **Outbox redelivery risk.** Existing transactional outbox retry behavior requires durable consumer idempotency, now made explicit.
9. **Canonical tooth identity.** VNext stores FDI internally and converts Palmer/Universal at boundaries instead of persisting mixed notation.
10. **Global-template RLS exception.** `tenant_id NULL` global templates require an explicit safe read policy and restricted write policy.
11. **Cross-tenant FK ownership.** Simple integer FKs are not enough; service-level same-tenant/same-patient checks are mandatory for linked records.
12. **Existing dependency duplication risk.** The plan now requires using Dentix's already-installed Radix/TanStack/Zustand/dnd-kit/hotkey/testing stack before adding equivalents.
13. **Odontogram build-vs-buy had not been investigated.** An OSS spike phase was added, including `react-advanced-odontogram`, `react-odontogram`, XState, and explicit Open Dental license classification.
14. **Open Dental licensing changed.** Current versions are proprietary and historical public source is GPL-2.0, so it is classified as workflow reference only for Dentix.
15. **Clinical renderer vendor lock-in.** Any third-party odontogram must sit behind a Dentix adapter and must never own the canonical data shape.
16. **Legacy payment allocation risk.** Existing payments remain patient-level; VNext does not invent historical charge allocations.
17. **Timestamp consistency risk.** New instant-like timestamps follow current Dentix UTC-naive persistence conventions to avoid a hidden second timezone migration inside this project.
18. **Odontogram architecture approval ambiguity.** The previous plan allowed an AI developer to select A/B/C and continue. The final plan now requires three runnable comparable prototypes, a formal decision report, and an explicit human approval token before Phase 1 can start.

These corrections are mandatory parts of the implementation plan, not optional recommendations.

# 34. Final Product Principle

The implementation is successful only when a dentist experiences this:

```text
46 -> RCT

Next visit:
Continue RCT 46

Last time:
✓ Access
✓ Working length

Next:
Cleaning & shaping

[Continue]
```

while Dentix internally keeps the clinical history, appointment context, materials, finance, lab state, files, audit trail, and future actions synchronized without forcing the user to enter the same information twice.

That is the target product experience.
---

# 35. AI Developer Start Prompt — Use With This Plan

Use this exact operational intent when handing the plan to an AI developer:

> Execute `DENTIX_UNIFIED_CLINICAL_WORKFLOW_VNEXT_MASTER_IMPLEMENTATION_PLAN_FINAL.md` strictly by micro-task and phase gate.
>
> Start by re-validating the current `main` HEAD against the plan baseline and document any drift.
>
> On the first execution cycle, perform Phase 0 and Phase 0A only.
>
> For the odontogram decision, build all three runnable comparison prototypes A/B/C at comparable visual and interaction fidelity using the same synthetic Dentix clinical fixture. Do not merely provide screenshots or theoretical analysis; I must be able to open and interact with each prototype.
>
> Complete the desktop, mobile, RTL, surface, bridge, implant, mixed-dentition, multi-select, layered-state, and side-by-side history-compare tests defined in Phase 0A.
>
> Produce `ODONTOGRAM_SPIKE_DECISION_REPORT.md` with evidence, measurements, risks, score matrix, and your recommendation.
>
> Then HARD STOP. Do not start Phase 1 or any full VNext implementation.
>
> Wait for my explicit approval in one of these exact forms:
>
> `APPROVE ODONTOGRAM STRATEGY: A`
>
> `APPROVE ODONTOGRAM STRATEGY: B`
>
> `APPROVE ODONTOGRAM STRATEGY: C`
>
> After approval, record the decision in `ADR-001-ODONTOGRAM-STRATEGY.md`, then continue the master plan phase by phase.
>
> Never skip a micro-task. Never mark a task complete without evidence. Never make destructive changes to existing customer clinical/financial data to simplify the migration. Prefer existing Dentix capabilities, then trusted/stable OSS after license/security/maintenance evaluation, and custom-build only where justified.

---

# 36. Final Plan Authority

This file is the controlling implementation plan for Dentix Unified Clinical Workflow VNext.

If an older plan, prototype note, chat instruction, or implementation shortcut conflicts with this file, the developer must stop and request a decision rather than silently choosing the conflicting interpretation.

The mandatory human odontogram architecture gate is intentional and must not be optimized away.
