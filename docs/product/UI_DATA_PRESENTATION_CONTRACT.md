# Dentix Data Presentation Contract — Plan 02 Phase 9

Status: **TARGET CONTRACT — implementation pending**

## Two table modes

### Standard DataTable
Use for small/medium datasets where the primary goal is readable comparison and simple row actions.

Required states:
- loading/skeleton;
- empty;
- error when the owning query exposes one;
- normal rows;
- optional pagination when real dataset size requires it.

### Dense DataTable / DataGrid-like
Use `AdvancedTable`/TanStack foundation for high-frequency operational data where sorting/filtering/pagination/virtualization are already needed.

Do not invent spreadsheet features or bulk operations unless the product already has them.

## Semantics and accessibility

- Keep semantic `<table>`, `<thead>`, `<tbody>`, `<th>`, `<td>` when tabular relationships matter.
- Sortable header controls must be keyboard operable and expose sort state (`aria-sort` or equivalent accessible control semantics).
- A clickable row must have a keyboard-equivalent route/action. Prefer a real link/button in the primary cell over `<tr onClick>`.
- Row action buttons need accessible names.
- Focus-visible state must remain visible in light/dark themes.

## Scanability

- Align numbers/money consistently; numeric content may use tabular numerals.
- Status appears in a semantic badge, not a decorative color alone.
- Primary identifier remains visually strongest in the row.
- Secondary metadata is quieter but readable.
- Avoid a card per row on desktop when comparison across rows is important.

## Sorting

- Sorting only appears on columns that support meaningful sort behavior.
- Visual direction indicator and accessible sort state are both required.
- Preserve current client/server sorting semantics; do not silently move a server dataset to client-only sorting.

## Filtering/search

- Global search and column filters must state their scope.
- Search input uses the shared input/search pattern.
- Empty clinic/data and "no results for current filter" are different states.
- Server-backed patient search behavior remains server-backed.

## Pagination / virtualization

- Preserve existing pagination source of truth (server vs client).
- Virtualization is an optimization, not a visual mode; it must preserve keyboard/action accessibility.
- Sticky headers must use opaque/readable surface treatment.

## Mobile adaptation

Choose by data shape:
1. horizontal scroll for genuinely tabular comparison;
2. prioritized-column list for operational tasks;
3. stacked detail rows only when comparison is secondary.

Do not hide important existing columns/actions on mobile without an intentional alternative.

## Column visibility

Column visibility controls are allowed only where the existing capability is already present/required. `AdvancedTable` currently owns visibility state but does not establish a product-wide requirement to expose a column chooser.

## Bulk actions

Bulk selection/actions are only permitted where the current product already supports them. Plan 02 does not add bulk features.

## Shared visual rules

- opaque table/header surfaces by default;
- quiet border hierarchy;
- canonical compact/standard cell spacing;
- no hover scale transform on rows;
- hover/selected/focus are distinct semantic states;
- loading skeleton dimensions should resemble final rows.

## Current migration decisions

- `DataTable.jsx`: retain as standard table path but merge state/visual/accessibility contract.
- `AdvancedTable.jsx`: harden as dense/capable base.
- feature-specific tables may remain where domain logic requires them, but should consume shared tokens and row/action patterns.

Phase 9 becomes DONE after representative patient, finance and inventory/data-heavy surfaces demonstrate these rules with tests.