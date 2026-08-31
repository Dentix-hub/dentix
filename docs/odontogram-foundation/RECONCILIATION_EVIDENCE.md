# Odontogram Foundation Protected-Branch Reconciliation

## Purpose

The A0–A9 foundation was completed on the local `feature/odontogram-foundation-codex` branch but was not present on either protected integration branch. This reconciliation preserves the bounded commits and moves that verified prerequisite onto the current `staging` lineage before ODG-L1 / Issue #126 begins.

## Reconciliation metadata

| Field | Value |
| --- | --- |
| Source branch | `feature/odontogram-foundation-codex` |
| Source range | `c0e27897^..5d757b52` |
| Source tip | `5d757b52eaa569ea30b49dd4a3cb7cf7f016d812` |
| Protected `main` revalidated | `44a0930e57216ea7dcd1d62e8942da16cefaad8e` |
| Protected `staging` base | `1b9630ea85b596959ae63d09e24ba4ea52c76c7c` |
| Reconciliation branch | `feat/odg-foundation-reconcile` |
| Date | `2026-08-31` |

## Scope and boundaries

- Preserves the original A0–A9 commit sequence.
- Adds no schema, migration, backend API, persistence, finance, appointment, lab, inventory, or Part II work.
- Does not include or modify the separate untracked `frontend/src/features/clinical-chart-v2/` workspace.
- Keeps renderer state outside the canonical clinical source of truth.
- ODG-A10 remains pending until this baseline passes review, T2, PR CI, and protected integration.

## Verification

T1 command:

```text
npm.cmd run test -- src/features/clinical-chart/tests src/features/dental/DentalChartSVG.test.jsx
```

Result: exit code `0`; `11` test files passed; `89` tests passed; no failures.

T2 and protected integration evidence are recorded on the reconciliation PR before ODG-L1 begins.
