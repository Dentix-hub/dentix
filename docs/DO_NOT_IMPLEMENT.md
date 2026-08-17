# Finance V2 — DO NOT IMPLEMENT Without Separate Product Approval

These items are explicitly outside the assumed Finance V2 capability set. Their absence must **not** be reported as an incomplete Finance V2 task, and Gemini must not invent them to make a screen look more complete.

## P3 / separate product decisions

- Payment methods such as Cash / Card / Wallet on ordinary patient payments.
- Doctor settlement/payment history, including fabricated `Paid`, `Remaining`, or `Last settlement` states.
- Full invoice lifecycle / invoice entity.
- True double-entry general ledger.
- Bank reconciliation.
- Advanced receivables aging.

## Other explicitly unsupported assumptions in the master plan

- Refund workflows unless deliberately added later.
- Tax/VAT accounting unless deliberately added later.
- Insurance claim accounting beyond currently implemented capabilities.

## Enforcement

If an approved Finance V2 task appears to require one of these capabilities:

1. inspect whether the repository already contains a real supported implementation;
2. if it does not, do not fake it;
3. keep the Finance V2 task within the existing data model;
4. if the approved workflow truly cannot work without it, mark the task `BLOCKED` and describe the product/data-model decision required.
