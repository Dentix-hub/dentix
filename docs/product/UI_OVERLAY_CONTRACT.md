# Dentix Design System V2 — Overlay Contract

Status: **TARGET CONTRACT — implementation pending**

## Canonical public surface

The target shared API is:

- `DentixDialog`
- `DentixConfirmDialog`
- `DentixDrawer`
- `DentixBottomSheet`
- `DentixPopover`
- `DentixMenu`
- `DentixTooltip`
- `DentixSelect`
- `DentixDatePicker`

Names may be compatibility-exported through current `Modal`, `ConfirmDialog`, `Select`, `Tooltip` and `DateTimePicker` while consumers migrate.

## Portal root

Transient content must render through one documented portal strategy. The default target is `document.body`/library portal with a shared overlay-layer contract; feature code must not create arbitrary portal roots.

## Backdrop

- Backdrop may be translucent and may use restrained blur.
- Backdrop and content surface are separate concepts.
- Content surface is opaque by default.
- Backdrop click behavior is explicit per primitive, not accidental bubbling.

## Surface

- Uses `surface-elevated`/opaque light-dark tokens.
- Uses `radius-overlay` and documented elevation.
- Never relies on the global decorative background for legibility.
- Supports constrained viewport height and safe-area padding.

## Focus

Every blocking overlay must:
1. remember the previously focused trigger/element;
2. move focus into the overlay intentionally;
3. trap focus while blocking;
4. close on Escape unless the workflow explicitly prevents cancellation;
5. return focus to the trigger/appropriate fallback after close.

Popover/menu/select use library-standard focus management and must not steal focus from unrelated controls.

## Scroll lock

- Lock document scrolling only for blocking overlays.
- Preserve the exact prior body overflow/style state and restore it on final close.
- Nested blocking overlays use a reference-count/stack model; a child closing must not unlock scrolling while a parent remains open.

## Nested overlays

A shared stack must establish ordering and dismissal ownership. Escape/outside click acts on the topmost dismissible overlay first. `z-[9999]` escalation is forbidden for migrated code.

## RTL

- Position with logical start/end semantics.
- Drawer direction is intentional, not inferred from a hard-coded left/right class.
- Keyboard arrows follow the underlying accessible primitive expectations for menus/selects/calendar controls.
- Reusable overlays never force `dir="rtl"` merely because current copy is Arabic.

## Mobile modes

- confirmation → dialog or bottom sheet depending context;
- small task → dialog/bottom sheet;
- contextual preview → popover on large screens, sheet/drawer when space requires;
- medium form → drawer/sheet;
- complex or multi-step workflow → dedicated/fullscreen workspace unless existing route semantics require compatibility during migration.

## Reduced motion

Overlay transitions consume shared motion tokens and become effectively immediate/minimal under `prefers-reduced-motion` while preserving focus and visibility semantics.

## External primitive boundary

External accessibility primitives must be wrapped inside `frontend/src/shared/ui/`. Feature code should consume Dentix wrappers rather than importing Radix/Headless overlay primitives directly after migration.

The first implementation may use an already-installed, proven primitive (for example Radix Dialog) behind the wrapper, but the public contract belongs to Dentix.

## Compatibility migration

1. Introduce canonical wrappers and tests.
2. Keep current public exports as compatibility wrappers.
3. Migrate representative high-risk consumers.
4. Detect raw overlay implementations.
5. Warn on new violations.
6. Deprecate/remove legacy wrappers only after reference proof.

## Required interaction tests

- initial focus
- Tab / Shift+Tab containment
- Escape
- outside click where enabled
- trigger focus return
- body scroll lock + exact restoration
- nested overlay lock/order
- RTL rendering smoke
- mobile drawer/sheet smoke
- reduced-motion smoke
- opaque surface regression
