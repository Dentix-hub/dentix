# Odontogram Foundation Decision Log

| ID | Date | Decision | Rationale | Status |
| --- | --- | --- | --- | --- |
| D-001 | 2026-08-29 | Use `feature/odontogram-foundation-codex` for Part I execution. | Required by the controlling plan and isolates chart foundation work. | Locked |
| D-002 | 2026-08-29 | Treat `origin/main@89d67010` as the revalidated source-main baseline. | This is the latest fetched main at A0 execution time. | Locked |
| D-003 | 2026-08-29 | Preserve the pre-existing `clinical-chart-v2` experiment but do not make it the canonical module. | It contains useful prototypes and user-owned work, while the approved architecture requires `features/clinical-chart/`. | Locked |
| D-004 | 2026-08-29 | Keep renderer state presentational and emit interaction intents instead of persistence commands. | Prevents the renderer from becoming the clinical source of truth. | Locked |

New decisions, deviations, and reversals must be appended here with evidence and the affected micro-task.

