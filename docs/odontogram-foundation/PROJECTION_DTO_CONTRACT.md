# Demo Projection DTO Contract

## Boundary

The Clinical Chart Projection is a frontend-only, serializable view model. It describes what a chart instance should display; it is not a production clinical schema, persistence model, billing object, or clinical source of truth.

The DTO is normalized by `domain/clinicalChartProjection.js` and currently uses schema version `1`.

## Projection shape

```js
{
  schemaVersion: 1,
  projectionId: 'demo-target-coverage',
  dentition: 'permanent', // permanent | primary | mixed
  toothOrder: ['18', '17', '16'], // explicit FDI identities
  teeth: {
    16: toothVisualState,
  },
  selection: targetOrNull,
}
```

`toothOrder` controls which registered anatomy positions belong to the instance. A mixed-dentition projection may combine permanent and primary FDI keys explicitly.

## Tooth visual state

Every normalized tooth has:

- `toothKey`: stable FDI identity;
- `lifecycle`: semantic lifecycle code such as `PRESENT`;
- `findings`: serializable visual finding entries;
- `procedures`: serializable visual procedure entries;
- `selection`: `{ isSelected, targets }`;
- `disabled`: boolean interaction state;
- `annotations`: display-only notes.

Finding and procedure entries contain a presentation-only `visualId`, semantic `code`, visual `phase`, one or more targets, and optional annotations. Visual phases are `existing`, `planned`, `active`, and `completed`. A9 maps these semantics to SVG presentation rules.

## Target subshape

All targets carry an FDI `toothKey` and one of these kinds:

| Kind | Required detail | Meaning |
| --- | --- | --- |
| `tooth` | none | Whole tooth |
| `surface` | `surfaceCode` | Named crown surface |
| `root` | `rootId` | Anatomy-registry root |
| `canal` | `rootId`, nullable `canalId` | Root-owned canal placeholder |

`canalId: null` is deliberate in this foundation: it preserves a target slot without claiming that the demo DTO defines the future canonical canal taxonomy.

## Safety rules

- Every tooth and root reference is checked against the anatomy registry.
- Target entries nested under a tooth must refer to that same tooth.
- DTO factories return frozen plain objects that survive JSON serialization.
- Unknown codes remain semantic data until the Visual Rule Registry supports them.
- No renderer, API, service, tenant, pricing, or workflow behavior is embedded in this DTO.
