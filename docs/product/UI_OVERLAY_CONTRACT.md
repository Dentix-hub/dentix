# Dentix Design System V2 — Overlay Contract

Status: **IMPLEMENTED FOUNDATION — compatibility migration active**

## Canonical public surface

The shared Dentix API is:

- `DentixDialog`
- `DentixConfirmDialog`
- `DentixDrawer`
- `DentixBottomSheet`
- `DentixPopover`
- `DentixMenu`
- `DentixTooltip`
- `DentixSelect`
- `DentixDatePicker`

Historical `Modal`, `ConfirmDialog`, `Select`, `Tooltip` and `DateTimePicker` exports remain compatibility paths while consumers migrate. Feature code must not depend on the implementation library when a Dentix wrapper exists.

## Implementation boundary

- Blocking overlays (`DentixDialog`, `DentixDrawer`, `DentixBottomSheet`) are implemented on the already-installed Radix Dialog primitive.
- `DentixPopover` wraps the already-installed Headless UI popover primitive.
- `DentixMenu` and `DentixTooltip` wrap Radix primitives.
- Content surfaces consume opaque Dentix semantic surface tokens.
- Feature code receives Dentix contracts; the underlying library remains replaceable.

## Portal and layer model

Transient content uses the underlying accessible library portal to `document.body`. Feature code must not create arbitrary portal roots.

Canonical z layers are:

`base < sticky < header < dropdown < popover < drawer < modal < toast < system`

Migrated shared code uses named layers rather than `z-[9999]` escalation.

## Backdrop and surface

- Backdrop may be translucent and may use restrained blur.
- Backdrop and content surface are separate concepts.
- Blocking overlay content uses the opaque `surface-elevated` role.
- Overlay radius/elevation consume `radius-overlay` and `shadow-high`/`shadow-medium` as appropriate.
- Backdrop click behavior is explicit per primitive.

## Focus and keyboard

Every blocking Dentix overlay:

1. captures the invoking element before the focus scope mounts;
2. moves/traps focus through the accessible primitive;
3. handles Tab / Shift+Tab containment;
4. closes on Escape when dismissible;
5. restores focus to the invoking element after close.

The compatibility `Modal` now inherits this behavior instead of implementing a separate focus/scroll system.

## Scroll lock and nesting

Radix owns reference-counted document scroll locking for blocking overlays. Regression tests prove that:

- one open modal owns one lock;
- a nested child creates a second lock;
- closing the child leaves the parent lock active;
- the final close restores the prior scroll state.

Escape/outside dismissal applies to the topmost dismissible overlay first.

## RTL

- Drawer uses logical `end` positioning rather than hard-coded left/right.
- Reusable overlays do not force an Arabic direction.
- Arabic/light and English/dark visual baselines are exercised in CI.
- Overlay interaction regression executes against an RTL patient workflow.

## Mobile and reduced motion

- `DentixBottomSheet` provides the canonical compact/mobile sheet surface.
- `DentixDrawer` and dialog primitives are viewport constrained.
- Motion consumes named durations and global `prefers-reduced-motion` handling.
- Playwright executes overlay interaction coverage in both visual desktop and mobile projects with reduced motion enabled.

## Compatibility migration evidence

Representative migration: `frontend/src/shared/ui/modals/PaymentModal.jsx` moved from a raw fullscreen overlay to shared `Modal`, `Button`, `Input` and existing `DateTimePicker`. Its exact submission payload is regression-tested, including the existing date-to-local-midnight behavior.

Existing raw feature overlays are **not** silently rewritten. The design-system guardrail reports them as legacy debt and rejects newly-added guarded violations in pull-request diffs.

## Known legacy debt

The current report contains 50 raw fullscreen overlay patterns and 14 arbitrary z-index findings across the legacy application. Some shared date-picker internals still use their historical Headless UI layering while their public Dentix boundary and regression protection are in place. These are staged migration items, not hidden acceptance exceptions.

## Required interaction coverage — implemented

- opaque content surface
- Enter / Space activation
- Tab / Shift+Tab containment
- Escape
- outside click
- trigger focus return
- body scroll lock + restoration
- nested overlay lock/order
- RTL smoke
- mobile project smoke
- reduced-motion smoke
