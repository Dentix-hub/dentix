# Odontogram and Clinical VNext Ticket Graph Pilot

Status: `GRAPH_BOUND` — Wave 1 ready

## Source lock

- Source: `docs/DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md`
- Status: Final execution plan
- SHA-256: `27A300E5DA8BEF9CCC6FA7E68D78975C9A628B813C828B3C7547FAA8F2A9AFFF`
- Existing tracker: `docs/odontogram-foundation/TASK_TRACKER.md`
- Pilot authority: Codex Part I only

G0-G16 remain reserved for Gemini after A17 produces a valid handoff and Codex
declares `WAITING FOR GEMINI VNEXT EXECUTION`.

## Preserved boundaries

- Keep the Dentix chart identity; do not redesign from zero.
- Renderer state is not the clinical source of truth.
- A package-owned DTO must not become the Dentix canonical clinical schema.
- Do not add dependencies when Dentix already has usable capabilities.
- Later clinical complexity belongs in the domain model, not the renderer.
- Part I adds no schema, migration, production API, finance, appointment, lab,
  inventory, treatment-plan backend, or legacy-migration work.
- Preserve old data; avoid giant modal-first flows.
- Do not begin Part II before the A17 hard gate.
- G11 must never auto-book an appointment without explicit user action.

## Part I ticket graph

| Key | Objective | Requirements | Depends on | Class | Verification |
| --- | --- | --- | --- | --- | --- |
| ODG-A10 | Root layer for every tooth family | A10-M01..M06 | A0-A9 | serial | renderer tests, lint, build, visuals |
| ODG-A11 | Notation and labels after roots | A11-M01..M03 | A10 | serial | tests and desktop evidence |
| ODG-A12 | Complete demo fixture matrix | A12-M01..M11 | A11 | serial | fixture/render tests |
| ODG-A13 | Isolated dual-chart compare | A13-M01..M04 | A12 | serial | state/layer isolation tests |
| ODG-A14 | Simple shell and inspector UI | A14-M01..M05 | A13 | serial | component tests and browser evidence |
| ODG-A15 | Responsive, RTL/LTR, keyboard, a11y | A15-M01..M08 | A11,A13,A14 | serial | responsive and accessibility gates |
| ODG-A16 | Part I regression suite | A16-M01..M07 | A10..A15 | serial | targeted/full tests, lint, serial build |
| ODG-A17 | Evidence, handoff, and hard stop | A17-M01..M07 | A16 | serial | evidence and handoff checklist |

```text
Wave 0 (reconciled pre-graph): A0-A9
Wave 1: A10
Wave 2: A11 -> A12
Wave 3: A13 -> A14
Wave 4: A15
Wave 5: A16
Wave 6: A17 -> WAITING FOR GEMINI VNEXT EXECUTION
```

## GitHub issue binding

| Key | Issue | Lifecycle |
| --- | --- | --- |
| ODG-A10 | #126 | `agent:ready` |
| ODG-A11 | #127 | `agent:blocked` by #126 |
| ODG-A12 | #128 | `agent:blocked` by #126, #127 |
| ODG-A13 | #129 | `agent:blocked` by #128 |
| ODG-A14 | #130 | `agent:blocked` by #128, #129 |
| ODG-A15 | #131 | `agent:blocked` by #127, #129, #130 |
| ODG-A16 | #132 | `agent:blocked` by #126-#131 |
| ODG-A17 | #133 | `agent:blocked` by #132 |

## Part I coverage

| Requirements | Disposition | Reason/status |
| --- | --- | --- |
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
| A10-M01..M06 | ODG-A10 | READY |
| A11-M01..M03 | ODG-A11 | BLOCKED_BY_A10 |
| A12-M01..M11 | ODG-A12 | BLOCKED_BY_A11 |
| A13-M01..M04 | ODG-A13 | BLOCKED_BY_A12 |
| A14-M01..M05 | ODG-A14 | BLOCKED_BY_A13 |
| A15-M01..M08 | ODG-A15 | BLOCKED_BY_A11_A13_A14 |
| A16-M01..M07 | ODG-A16 | BLOCKED_BY_A10_A15 |
| A17-M01..M07 | ODG-A17 | BLOCKED_BY_A16 |

## Gemini and review coverage

These requirements are present but N/A for this Codex pilot because the source
assigns them to Gemini after the Part I gate.

| Requirements | Future bounded nodes | Disposition |
| --- | --- | --- |
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

## Gates and anti-skip result

1. A17 closes only when A0-A17 pass or have explicit accepted deviations.
2. Gemini G0 requires the complete handoff and exact hard-stop statement.
3. Schema, migration, RLS, API, finance, and rollout nodes remain serial/high-risk.
4. G16 transitions require explicit approval and reversible tenant controls.
5. Every Gemini phase requires RV-Gx review before dependent work advances.
6. G11-M08 forbids auto-booking without explicit user action.

Every A0-A17 micro-task maps to a ticket or evidenced pre-graph N/A. Every
G0-G16 range maps to bounded future nodes. R-M01..M10 remain a repeated review
gate. No original requirement, non-goal, validation family, role boundary, or
approval gate disappears, and no Part II authority is inferred.
