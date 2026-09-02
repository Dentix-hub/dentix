---
name: dentix-plan-execution
description: Execute an approved DENTIX implementation plan without skipping requirements. Use when a task references a plan, checklist, or acceptance criteria.
---

# DENTIX Plan Execution Discipline

## Execution Lifecycle
When executing an approved plan or specification:
1. **Read Requirements**: Read the complete plan or spec and identify all numbered requirements and acceptance criteria before writing code.
2. **Track Checklist**: Maintain an internal checklist during execution to ensure every requirement is accounted for.
3. **Follow Workflow**: Adhere strictly to `docs/engineering/DEVELOPMENT_WORKFLOW.md` (one branch, targeted tests, one PR into staging).
4. **Targeted Verification**: Run targeted local tests during implementation to verify changed behavior.
5. **Truthful Reporting**: Report final completion truthfully as `DONE`, `PARTIAL`, or `BLOCKED`. Never mark work as `DONE` if planned requirements remain unaddressed.

## Scope & Quality Rules
- **No Scope Shrinking**: Never drop acceptance criteria without explicit user authorization.
- **No Placeholders**: Never substitute real implementation with `TODO` stubs or dummy mocks when real integration is required.
- **No Fake Verification**: Every claimed test passage must be backed by executed terminal commands and real exit codes.
