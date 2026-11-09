---
name: grill-with-docs
description: A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go.
disable-model-invocation: true
---

Call the Skill tool twice, for "grilling" and "domain-modeling".

## Dentix adaptation

Use this skill only when explicitly requested by the owner, selected by an AGENTS.md routing rule, or required as a documented dependency of an explicitly authorized skill. This skill never overrides AGENTS.md, PROJECT_STANDARDS.md or DEVELOPMENT_WORKFLOW.md. Stay within the authorized task scope.

Ask at most four independent, high-impact questions per round; defer the rest without assuming their answers. Investigate facts with available tools; do not spawn sub-agents unless the owner explicitly authorizes it. When a term or decision merits a glossary entry or ADR, propose it in the final summary using docs/adr/README.md conventions. Do not create or modify GLOSSARY.md, ADR files or other repository files without explicit owner approval and an in-scope task.
