# Dentix Design System V2 — Token Contract

Status: **TARGET CONTRACT — implementation pending**  
Direction: Dentix Clinical Workspace

This document defines the token vocabulary that Phase 4 must implement in CSS/Tailwind. Existing utilities remain valid until migrated; this contract does not authorize a blind global search/replace.

## Color roles

Canonical semantic roles:

- `background` — application canvas.
- `surface` — default **opaque** content surface.
- `surface-elevated` — transient/elevated opaque content surface.
- `surface-subtle` — low-emphasis section/row fill.
- `text-primary` — primary readable text.
- `text-secondary` — supporting text.
- `text-muted` — metadata/disabled-adjacent text that still meets contrast requirements.
- `border` — default separator/border.
- `border-strong` — emphasized separator.
- `input` — input surface.
- `primary` — primary action/selection.
- `success` — successful/healthy status.
- `warning` — caution/attention status.
- `danger` — destructive/error status.
- `info` — informational status.
- `selected` — selected row/control background.
- `focus` — keyboard focus ring.
- `disabled` — disabled surface/text treatment.
- `backdrop` — overlay backdrop; translucency allowed here.

Rules:
- Content-surface tokens are opaque by default.
- Semantic colors must not be repurposed as random decorative palettes.
- Feature-specific clinical colors must document their meaning at feature level.

## Radius scale

Target named tiers:

| Token | Intent |
|---|---|
| `radius-control` | buttons, inputs, compact controls |
| `radius-card` | cards/sections |
| `radius-overlay` | dialogs/popovers/drawers |
| `radius-pill` | tags/status pills only |

Initial target values: control `0.625rem`, card `0.75rem`, overlay `0.875rem`, pill `9999px`.

Arbitrary values such as `rounded-[2.5rem]`, `rounded-[3rem]` and decorative 100px corner shapes are migration debt.

## Shadow / elevation

| Token | Intent |
|---|---|
| `shadow-none` | flat/content default |
| `shadow-low` | subtle card/control separation |
| `shadow-medium` | dropdown/popover |
| `shadow-high` | modal/drawer/toast where needed |

Colored glow shadows are not part of the default elevation contract.

## Spacing rhythm

Use the existing Tailwind spacing scale but standardize composition around:

- `space-control` — 0.5rem
- `space-field` — 0.75rem
- `space-section` — 1.5rem
- `space-page` — responsive 1rem / 1.5rem / 2rem
- compact table cell: 0.625rem–0.75rem vertical
- standard table cell: 0.75rem–1rem vertical

Do not introduce component-specific arbitrary pixel gaps where a canonical spacing step works.

## Typography roles

| Role | Intent |
|---|---|
| `type-page` | one page title |
| `type-section` | section heading |
| `type-subsection` | local group heading |
| `type-body` | primary reading/content |
| `type-label` | form/control label |
| `type-caption` | metadata/supporting text |
| `type-numeric` | money/KPI/quantitative emphasis |
| `type-table` | dense data rows/headers |

Cairo/Inter remain the configured families. Heavy weight is reserved for hierarchy, not every metadata line.

## Motion tokens

| Token | Target | Use |
|---|---:|---|
| `motion-fast` | 120ms | hover/focus/compact state |
| `motion-standard` | 180ms | disclosure/menu/popover |
| `motion-emphasized` | 240ms | drawer/dialog spatial transition |

Rules:
- Default easing should be a calm ease-out for entering state and ease-in for leaving.
- Avoid scale/rotate/bounce unless state meaning requires it.
- Shared primitives must provide a reduced-motion path using `prefers-reduced-motion`.

## Z-index contract

| Layer | Token/value |
|---|---:|
| base | `z-base` / 0 |
| sticky | `z-sticky` / 10 |
| header | `z-header` / 20 |
| dropdown | `z-dropdown` / 40 |
| popover | `z-popover` / 50 |
| drawer | `z-drawer` / 60 |
| modal | `z-modal` / 70 |
| toast | `z-toast` / 80 |
| emergency/system | `z-system` / 90 |

`z-[9999]`, `z-[100]` and unrelated local escalation must be migrated gradually after the canonical overlay stack is proven.

## Phase 4 implementation gates

Phase 4 is not DONE until:
1. CSS variables exist for light/dark roles.
2. Tailwind aliases expose the semantic roles/scales.
3. representative shared primitives consume them.
4. legacy glass utilities remain isolated/explicit rather than driving content surfaces.
5. frontend build/tests pass.
6. AS-IS/golden screenshot differences are reviewed intentionally.