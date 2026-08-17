# Gemini Start Prompt — DENTIX Finance V2

Use this prompt at the beginning of a new implementation session.

> You are implementing DENTIX Finance V2 in an existing production repository.
>
> Read these files before editing code: `README_FIRST.md`, `EXECUTION_PROTOCOL.md`, `CURRENT_STATE.md`, `IMPLEMENTATION_LEDGER.md`, `DO_NOT_IMPLEMENT.md`, and the single current `PHASE_XX_*.md` file. Use `MASTER_SPEC.md` as the product/design source of truth and read the source sections referenced by the current phase.
>
> Do not implement the whole master plan in one pass. Work only on the current phase, in a small batch of eligible task IDs. Inspect the actual repository before making changes; do not assume example paths or APIs are exact.
>
> Before coding, report the task IDs selected, their dependencies, the exact repository areas you inspected, and any blocking mismatch between the plan and the real code. Then implement the batch.
>
> Update `IMPLEMENTATION_LEDGER.md` with concrete implementation and verification evidence. A task may be marked VERIFIED only after every acceptance criterion is proven. PARTIAL is failure for completion purposes.
>
> Do not fabricate fields, endpoints, permissions, payment methods, invoices, doctor settlement history, accounting semantics, or financial numbers. The backend is authoritative for financial formulas. Preserve tenant isolation, RBAC, financial visibility, patient data, and existing financial writes.
>
> Run all relevant automated and manual verification for the batch. Audit against the task acceptance criteria after implementation rather than trusting your own completion summary.
>
> Do not say DONE/COMPLETE/FINISHED while any current-phase task remains NOT_STARTED, IN_PROGRESS, PARTIAL, or BLOCKED. Do not advance to the next phase until the current phase gate passes and `CURRENT_STATE.md` is updated.
