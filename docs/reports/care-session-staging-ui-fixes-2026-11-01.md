# Care-session staging UI corrections

Status: implementation DONE for the five reported screenshot defects.

| Reported behavior | Correction |
| --- | --- |
| Historical visit dialog remains English in Arabic | Resolve the active i18n translation in the dialog and pass the parent's translator; translate static historical/completed/tooth labels too. |
| Second Add button appears inert | Display an actionable localized validation message for missing measurement/value/procedure. Valid input adds a procedure-scoped observation; it does not submit the entire visit. |
| Selected procedure tooth is blank | Infer the sole tooth from procedure targets or the treatment tooth, populate the editable field, and update it when the selected procedure changes. Unrelated rerenders preserve manual overrides; ambiguous multi-tooth procedures require explicit entry. |
| Old session form still available | With native writes enabled, remove legacy session creation from treatment editing and open the unified workspace/history. Existing legacy session records remain readable. Flag-off behavior stays compatible. |
| One procedure appears repeatedly in active items | Suppress linked legacy and renderer projections using verified work-item provenance and the server's explicit visual source identifiers. Preserve separate procedures, including matching codes and unrelated numeric ID collisions. |

No database records are deleted or merged. No schema, migration, permissions or financial calculations change.

Verification: 99 tests passed across 13 relevant workflow, editor, inspector, adapter, projection, history, RCT and i18n files. A final locale/inspector subset after the last static-label translation passed 16 tests (overlapping selection). ESLint, production/PWA/marketing build, whitespace checks and diff design guardrails passed. Logs: `/tmp/dentix-session-ui-fixes/`.

Staging path, approximately five minutes:

1. In Arabic, open Record Past Visit and verify translated labels, including the badge and completed status.
2. Select a tooth-specific procedure, verify its tooth populates, switch procedures and verify the new tooth. Enter a measurement/value and Add; verify a row appears. Try an empty Add and verify the explanatory message.
3. Edit a treatment with native writes enabled. Verify the legacy Add Session form is absent, old recorded visits remain visible, and the new button opens unified visits/workspace.
4. Inspect a tooth represented by a native procedure, linked treatment and visual projection: show one active item. Verify genuinely independent procedures still appear separately.
