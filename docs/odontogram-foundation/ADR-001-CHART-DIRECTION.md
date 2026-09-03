# ADR-001: Dentix Native Odontogram Renderer Direction

- Status: Accepted
- Date: 2026-08-29
- Decision owners: DENTIX / Codex Part I
- Scope: Frontend odontogram foundation only
- Controlling plan: `DENTIX_ODONTOGRAM_FIRST_EXECUTION_AND_VNEXT_HANDOFF_FINAL_MASTER_PLAN.md`

## Context

Dentix already has a minimalist SVG odontogram, crown paths, tooth layout, notation, and adjacent clinical UI. Separate experimental work also explored raster tooth assets and procedure-specific images. The approved product direction is to preserve the recognizable Dentix chart rather than replace it with an image atlas or a new visual system.

The foundation must add useful anatomy now, remain simple to operate, and avoid coupling a drawing library to future clinical persistence or workflow rules.

## Decision

Adopt **Dentix Native Renderer + Root Extension + Data-Driven Rules**.

1. Preserve the current Dentix chart shell, layout, minimalist line language, and crown styling.
2. Add roots as the first anatomy extension; do not redesign every tooth from scratch.
3. Render with Dentix-owned React/SVG components and normalized geometry.
4. Keep anatomy, projected clinical state, visual rules, rendering, and interaction intents as separate layers.
5. Treat images and the pre-existing `clinical-chart-v2` experiment as references/prototypes, not as the canonical renderer or schema.
6. Keep the renderer deterministic: the same anatomy plus Projection DTO and layer configuration must produce the same visual result.

## Architectural layers

### 1. Anatomy Registry

Owns stable visual anatomy definitions: dentition, tooth identity, tooth class, crown outline access, root outlines, root/canal identifiers, orientation, and clickable surface geometry. It contains no patient state and no workflow decisions.

### 2. Projection DTO

A frontend-facing, serializable view model describing what should be shown for a chart instance: teeth, lifecycle state, findings, procedures, targets, status/lifecycle, notation, and read-only state. It is an adapter boundary, not the future canonical backend schema.

### 3. Visual Rule Registry

Maps projected semantic states to presentation instructions such as layer, color token, opacity, stroke/fill style, pattern, and target geometry. Rules are data-driven and independently testable; they do not mutate the projection.

### 4. Renderer

Combines normalized anatomy with resolved visual rules to produce the SVG chart. It owns drawing order, clipping, transforms, visual selection/focus states, and accessible SVG markup. It is a pure presentation boundary wherever practical.

### 5. UI Interaction Layer

Owns chart controls, selected tooth/surface state, layer filters, inspector presentation, responsive behavior, and conversion of pointer/keyboard actions into renderer interaction intents. It does not persist clinical facts directly.

## One-way dependency and data flow

```text
Anatomy Registry ─────┐
                     ├─> Renderer ─> accessible SVG output
Projection DTO ─> Visual Rule Registry ┘           │
                                                     └─> interaction intents
                                                          │
                                                          v
                                                   UI Interaction Layer
```

The renderer may depend on anatomy contracts and resolved visual instructions. Domain/persistence code must never depend on internal SVG paths, component state, or package-owned DTOs.

## Renderer non-responsibilities

The renderer explicitly does not own or decide:

- persistence, API mutations, database identifiers, or synchronization;
- pricing, billing, ledgers, claims, or any financial calculation;
- clinical workflows, approvals, treatment-plan progression, or appointment orchestration;
- lab or inventory workflows;
- history storage, event sourcing, audit retention, or migration;
- clinical truth, diagnosis validity, permission/RBAC decisions, or tenant isolation;
- ordering of procedures beyond the explicit visual layer rules supplied to it.

It emits typed interaction intents such as tooth, surface, root, or canal selection. A future integration layer decides whether and how those intents become commands.

## Future-readiness targets

The contracts and anatomy identifiers must support later additive work without replacing this renderer:

- targeting a whole tooth, named surface, root, or canal;
- layered `existing`, `planned`, `active`, and `completed` visuals;
- simultaneous findings and procedures with deterministic z-order;
- more than one independent chart instance on the same page;
- read-only history comparison with separate DTOs and layer filters;
- permanent, primary, and mixed dentition;
- Arabic RTL and English LTR shells without mirroring clinical tooth identity incorrectly;
- future adapters from canonical VNext clinical models without adopting renderer DTOs as backend schemas.

## Consequences

### Positive

- Dentix retains a familiar, consistent chart.
- Root anatomy can be added incrementally and tested separately.
- Findings/procedures become rules rather than a growing library of pasted tooth images.
- Multiple independent chart instances are feasible because state is passed by contract.
- Gemini can later integrate real clinical projections without coupling the clinical core to SVG internals.

### Trade-offs

- Root and surface geometry require deliberate Dentix-owned maintenance.
- Programmatic visuals may need targeted visual regression coverage.
- The demo Projection DTO must later be adapted, not promoted directly into a production clinical schema.

## Supersession and compatibility note

If an earlier exploratory document selected per-tooth raster variants as the primary chart strategy, this ADR supersedes that choice for the Part I foundation. Existing assets remain preserved and may serve as visual references, but runtime procedure/finding representation must follow native geometry and data-driven rules.

## Acceptance mapping

- A1-M01: direction and root-first native-renderer decision are explicit.
- A1-M02: all five architectural layers are defined.
- A1-M03: renderer non-responsibilities are explicit.
- A1-M04: root/canal targeting, lifecycle layers, and multi-instance readiness are explicit.
