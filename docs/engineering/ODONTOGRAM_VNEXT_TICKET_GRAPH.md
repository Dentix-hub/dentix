<!-- STATUS: HISTORICAL / NON-AUTHORITATIVE -->
# STATUS: HISTORICAL / NON-AUTHORITATIVE
> **Archived Document** — This file records historical V2.1 ticket graph mechanics. Product requirements and clinical decisions are preserved for reference, but execution mechanics are strictly **NON-AUTHORITATIVE**. Active DENTIX development is governed by `docs/engineering/DEVELOPMENT_WORKFLOW.md`.

---

# Odontogram and Clinical VNext Ticket Graph (V2.1 Lean)

Status: `GRAPH_BOUND` — Ready for V2.1 Lean Wave Execution

## Source lock

- Source: `docs/DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md`
- Status: Final execution plan
- SHA-256: `27A300E5DA8BEF9CCC6FA7E68D78975C9A628B813C828B3C7547FAA8F2A9AFFF`
- Existing tracker: `docs/odontogram-foundation/TASK_TRACKER.md`
- Pilot authority: Codex Part I only

G0-G16 remain reserved for Gemini after A17 produces a valid handoff and Codex declares `WAITING FOR GEMINI VNEXT EXECUTION`.

## Preserved boundaries

- Keep the Dentix chart identity; do not redesign from zero.
- Renderer state is not the clinical source of truth.
- A package-owned DTO must not become the Dentix canonical clinical schema.
- Do not add dependencies when Dentix already has usable capabilities.
- Later clinical complexity belongs in the domain model, not the renderer.
- Part I adds no schema, migration, production API, finance, appointment, lab, inventory, treatment-plan backend, or legacy-migration work.
- Preserve old data; avoid giant modal-first flows.
- Do not begin Part II before the A17 hard gate.
- G11 must never auto-book an appointment without explicit user action.

## V2.1 Lean Wave Architecture

| Wave ID | Tickets / Nodes | Mode | Risk Family | Review Policy | PR Strategy | Verification Tier |
|---|---|---|---|---|---|---|
| **ODG-L1** | #126 (ODG-A10) | `STANDARD` | `risk:clinical-ui` | Wave boundary | Wave PR | T1 (targeted renderer tests) -> T2 (wave gate) |
| **ODG-L2** | #127 (ODG-A11) | `HIGH_RISK` | `risk:clinical-semantics` | Independent per-ticket | Individual PR | T1 -> T2 -> T3 full gate |
| **ODG-L3** | #128–#131 (ODG-A12..ODG-A15) | `STANDARD` | `risk:clinical-ui` | Wave boundary | Single Wave PR (serial inside wave) | T1 (per-ticket bounded commits) -> T2 (wave gate) |
| **ODG-L4** | #132 (ODG-A16) | `STANDARD` | `risk:clinical-ui` | Wave boundary | Wave PR | T2 Part I regression verification gate |
| **ODG-L5** | #133 (ODG-A17) | `HIGH_RISK` | `governance` | Independent gate | Individual PR | T3 Hard-stop checklist & handoff |

```text
Wave 0 (reconciled pre-graph): A0-A9 (PASS_PRE_GRAPH)
Wave 1 (ODG-L1): #126 (ODG-A10) [STANDARD, clinical-ui]
Wave 2 (ODG-L2): #127 (ODG-A11) [HIGH_RISK, clinical-semantics]
Wave 3 (ODG-L3): #128 -> #129 -> #130 -> #131 [STANDARD, clinical-ui, serial wave]
Wave 4 (ODG-L4): #132 (ODG-A16) [Part I Regression Gate]
Wave 5 (ODG-L5): #133 (ODG-A17) [Final Evidence & Handoff Hard-Stop] -> WAITING FOR GEMINI VNEXT EXECUTION
```

## Part I Ticket Graph

| Key | Issue | Objective | Requirements | Mode | Risk Family | Depends on | Verification |
|---|---|---|---|---|---|---|---|
| ODG-A10 | #126 | Root layer for every tooth family | A10-M01..M06 | `STANDARD` | `clinical-ui` | A0-A9 | T1 (vitest root rendering) + T2 wave gate |
| ODG-A11 | #127 | Notation and labels after roots | A11-M01..M03 | `HIGH_RISK` | `clinical-semantics` | A10 | T1 + T2 + T3 full verification |
| ODG-A12 | #128 | Complete demo fixture matrix | A12-M01..M11 | `STANDARD` | `clinical-ui` | A11 | T1 (fixture/render unit tests) |
| ODG-A13 | #129 | Isolated dual-chart compare | A13-M01..M04 | `STANDARD` | `clinical-ui` | A12 | T1 (state/layer isolation tests) |
| ODG-A14 | #130 | Simple shell and inspector UI | A14-M01..M05 | `STANDARD` | `clinical-ui` | A13 | T1 (component tests and browser visuals) |
| ODG-A15 | #131 | Responsive, RTL/LTR, keyboard, a11y | A15-M01..M08 | `STANDARD` | `clinical-ui` | A11,A13,A14 | T1 (responsive + a11y tests) + T2 wave gate |
| ODG-A16 | #132 | Part I regression suite | A16-M01..M07 | `STANDARD` | `clinical-ui` | A10..A15 | T2 comprehensive Part I regression suite |
| ODG-A17 | #133 | Evidence, handoff, and hard stop | A17-M01..M07 | `HIGH_RISK` | `governance` | A16 | T3 full repository verification & handoff gate |

## Implementer Brief Guidelines

- **Domain-Specific Skills Only**: Implementers load only relevant execution skills (e.g. `dentix-frontend-react`, `dentix-backend-fastapi`).
- **No Heavy Skill Preloading**: Orchestration and code review skills are NOT preloaded into implementer contexts.
- **Review Cadence**:
  - `STANDARD` waves (ODG-L1, ODG-L3, ODG-L4): Review conducted at wave boundary before PR.
  - `HIGH_RISK` tickets (ODG-L2, ODG-L5): Dedicated independent review before ticket closure.
- **Worktree Reuse**: A single worktree is reused across serial tickets in the same wave.

## Part I Requirement Coverage Verification

| Requirements | Disposition | Reason / Status |
|---|---|---|
| A0-M01..M04 | N/A issue creation | PASS_PRE_GRAPH; baseline evidence exists |
| A1-M01..M04 | N/A issue creation | PASS_PRE_GRAPH; ADR evidence exists |
| A2-M01..M04 | N/A issue creation | PASS_PRE_GRAPH; scaffold/route verified |
| A3-M01..M05 | N/A issue creation | PASS_PRE_GRAPH; anatomy verified |
| A4-M01..M03 | N/A issue creation | PASS_PRE_GRAPH; crown parity verified |
| A5-M01..M06 | N/A issue creation | PASS_PRE_GRAPH; roots approved |
| A6-M01..M05 | N/A issue creation | PASS_PRE_GRAPH; surfaces verified |
| A7-M01..M04 | N/A issue creation | PASS_PRE_GRAPH; renderer boundary verified |
| A8-M01..M04 | N/A issue creation | PASS_PRE_GRAPH; projection verified |
| A9-M01..M05 | N/A issue creation | PASS_PRE_GRAPH; visual rules verified |
| A10-M01..M06 | ODG-A10 (#126) | READY (ODG-L1 Wave) |
| A11-M01..M03 | ODG-A11 (#127) | BLOCKED_BY_A10 (ODG-L2 High-Risk Wave) |
| A12-M01..M11 | ODG-A12 (#128) | BLOCKED_BY_A11 (ODG-L3 Wave) |
| A13-M01..M04 | ODG-A13 (#129) | BLOCKED_BY_A12 (ODG-L3 Wave) |
| A14-M01..M05 | ODG-A14 (#130) | BLOCKED_BY_A13 (ODG-L3 Wave) |
| A15-M01..M08 | ODG-A15 (#131) | BLOCKED_BY_A11_A13_A14 (ODG-L3 Wave) |
| A16-M01..M07 | ODG-A16 (#132) | BLOCKED_BY_A10_A15 (ODG-L4 Gate) |
| A17-M01..M07 | ODG-A17 (#133) | BLOCKED_BY_A16 (ODG-L5 Hard-Stop Gate) |

**Total Part I Requirements**: 18 requirement groups, 95 micro-tasks. Missing requirement IDs: **0**.

## Gemini and Review Coverage (Part II Post-A17)

These requirements remain reserved for Gemini execution after ODG-A17 completes:

| Requirements | Future Bounded Nodes | Disposition |
|---|---|---|
| G0-M01..M05 | G0-KICKOFF | N/A_GEMINI_HARD_GATE |
| G1-M01..M18 | G1-SCHEMA-A, G1-SCHEMA-B, G1-MIGRATION-GATE | N/A_GEMINI_HARD_GATE |
| G2-M01..M16 | G2-TAXONOMY, G2-TEMPLATES | N/A_GEMINI_HARD_GATE |
| G3-M01..M13 | G3-MAPPER-CORE, G3-MAPPER-LEGACY, G3-SAFETY | N/A_GEMINI_HARD_GATE |
| G4-M01..M14 | G4-RUNNER, G4-BACKFILL, G4-INVARIANCE | N/A_GEMINI_HARD_GATE |
| G5-M01..M10 | G5-PROJECTION, G5-SHADOW-PERF | N/A_GEMINI_HARD_GATE |
| G6-M01..M06 | G6-CHART-INTEGRATION | N/A_GEMINI_HARD_GATE |
| G7-M01..M16 | G7-COMMANDS, G7-READS, G7-SECURITY | N/A_GEMINI_HARD_GATE |
| G8-M01..M15 | G8-FLOWS, G8-DISCOVERY, G8-SAFETY | N/A_GEMINI_HARD_GATE |
| G9-M01..M14 | G9-PLAN-CORE, G9-PLAN-PROJECTION | N/A_GEMINI_HARD_GATE |
| G10-M01..M20 | G10-CORE, G10-RCT-UI, G10-RESUME, G10-SAFETY | N/A_GEMINI_HARD_GATE |
| G11-M01..M12 | G11-APPOINTMENT, G11-SAFETY | N/A_GEMINI_HARD_GATE |
| G12-M01..M16 | G12-LINKAGE, G12-HANDOFF, G12-BILLING-SAFETY | N/A_GEMINI_HARD_GATE |
| G13-M01..M11 | G13-USAGE, G13-DEDUCTION, G13-INVARIANCE | N/A_GEMINI_HARD_GATE |
| G14-M01..M14 | G14-POLICY, G14-PARITY, G14-CUTOVER | N/A_GEMINI_HARD_GATE |
| G15-M01..M09 | G15-ATTACHMENT-CONTEXT | N/A_GEMINI_HARD_GATE |
| G16-M01..M13 | G16-INTERNAL, G16-PILOT, G16-STABILITY | N/A_GEMINI_HARD_GATE |
| R-M01..M10 per phase | RV-G0..RV-G16 | N/A_UNTIL_GEMINI_DELIVERY |

## Anti-Skip and Gate Enforcement

1. A17 closes only when A0-A17 pass or have explicit accepted deviations.
2. Gemini G0 requires the complete handoff and exact hard-stop statement.
3. Schema, migration, RLS, API, finance, and rollout nodes remain serial/high-risk.
4. G16 transitions require explicit approval and reversible tenant controls.
5. Every Gemini phase requires RV-Gx review before dependent work advances.
6. G11-M08 forbids auto-booking without explicit user action.
