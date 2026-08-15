# DENTIX Finance V2 — Gemini Execution Package

## Purpose

This package converts the original **DENTIX Finance V2** redesign/refactor plan into a controlled execution system for an AI coding agent. It does **not** replace the original plan. `MASTER_SPEC.md` remains the source of product/design truth.

## Required operating model

Do not ask the agent to “implement the whole plan.” Execute **one phase at a time** and, inside a phase, work in small batches of related task IDs.

Execution loop:

```text
Read MASTER_SPEC + EXECUTION_PROTOCOL + CURRENT_STATE + current PHASE file
        ↓
Inspect the real repository before editing
        ↓
Select a small batch of eligible task IDs
        ↓
Implement
        ↓
Run required tests/checks
        ↓
Record concrete evidence in IMPLEMENTATION_LEDGER
        ↓
Independent requirement audit
        ↓
Only VERIFIED tasks count as complete
        ↓
Pass phase gate → checkpoint/commit → next phase
```

## File order for Gemini

1. `EXECUTION_PROTOCOL.md`
2. `CURRENT_STATE.md`
3. `IMPLEMENTATION_LEDGER.md`
4. `MASTER_SPEC.md` **as reference**, not as a single execution request
5. The single `PHASE_XX_*.md` file currently being executed
6. `DO_NOT_IMPLEMENT.md`

## Hard rules

- Phase 0 is a **hard gate** before visual redesign implementation.
- Do not skip task IDs.
- Do not mark a task `VERIFIED` without evidence.
- `PARTIAL` is not complete.
- Do not implement P3 product decisions unless the user separately approves them.
- Do not fabricate backend fields or product capabilities.
- The backend remains the source of truth for authoritative financial calculations.
- Existing tenant isolation, RBAC, financial visibility, patient data, and financial writes must survive the migration.

## Recommended session boundary

Use a fresh agent session after each phase or major checkpoint. Carry forward only:

- this package,
- repository state,
- `CURRENT_STATE.md`,
- `IMPLEMENTATION_LEDGER.md`,
- test results / known blockers.

This reduces context drift and “I finished” claims that are not backed by evidence.
