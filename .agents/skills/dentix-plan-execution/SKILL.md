---
name: dentix-plan-execution
description: Execute an approved multi-phase DENTIX implementation plan without skipping requirements. Use when a task references a plan, phases, a checklist, acceptance criteria, or asks to implement all planned work.
---

# DENTIX Plan Execution Discipline

## Purpose
Enforce rigorous, complete execution of approved implementation plans across the DENTIX repository. Prevent skipped plan items, premature completion claims, silent reduction of acceptance criteria, and "done with important parts" shortcuts.

## Required Execution Algorithm

1. **Read & Decompose**:
   - Read the referenced implementation plan in its entirety.
   - Extract every phase, task ID, acceptance criterion, file constraint, verification step, and non-goal.
2. **Build Ledger**:
   - Construct a task ledger with explicit statuses: `NOT_STARTED`, `IN_PROGRESS`, `PASS`, `BLOCKED`, `N/A`.
   - Initialize all items as `NOT_STARTED`.
3. **Phase-by-Phase Order**:
   - Execute strictly in plan order unless explicit parallel execution is authorized.
   - Before beginning each phase, inspect the working tree and confirm the phase assumptions remain valid.
4. **Execution & Verification**:
   - Mark active phase/task as `IN_PROGRESS`.
   - Implement every mandatory requirement surgically.
   - Execute the specified verification commands (tests, linter, build).
   - Only after successful verification, mark the task/phase `PASS`.
5. **Anti-Skip Checkpoint**:
   - After completing each phase, review all remaining tasks.
   - Explicitly verify: *Which numbered plan IDs remain `NOT_STARTED` or `BLOCKED`?*
   - Never proceed to final completion if any planned item is unaddressed.
6. **Reporting & Integrity**:
   - Final status must strictly be `DONE`, `PARTIAL`, or `BLOCKED`.
   - `PARTIAL` or `BLOCKED` work must never be disguised as `DONE`.
   - Record exact verification commands, exit codes, and diff summaries.

## Scope & Quality Rules
- **No Scope Shrinking**: Never shorten an approved plan or drop acceptance criteria without explicit user authorization.
- **No Placeholders**: Never substitute real implementation with `TODO`, stub comments, or dummy mocks when real integration is required.
- **No Fake Verification**: Never claim a test, lint, or build command passed without actually executing it and inspecting the output.
- **Documentation vs Implementation**: Never present documentation or planning updates as completed feature implementation.
