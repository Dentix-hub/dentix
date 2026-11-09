# Commercial controls: C1–C6 completion

Status: local implementation; remote delivery and staging acceptance pending.
Base: staging `c4c7eb5998039bdadffc23bff31f65d0464d091b` (PR #366).
Branch: `fix/commercial-controls-completion`.

## Result

- C1: tenant-row serialization makes first admission and duplicate-key lookup one atomic operation, including the first daily window. Matching retries do not dispatch chat, clinic analysis or Scribe again. Child work derives a stable server-owned key and consumes zero extra units. Actor, operation and payload conflicts remain denied. Pending/uncertain requests are not presented as finished insights.
- C2: limits come from the linked database plan, including a started future paid period. Disabled/zero/missing anchors give zero; legacy labels do not grant a budget. Existing usage is retained. Feature denies are resolved by the commercial guard rather than a second, differently keyed quota override algorithm.
- C3: apply requires explicit selections, current anchor, revision and reason. The complete batch is validated under locks before writes. Existing/retired, scheduled and platform contracts are refused by this repair operation; normal subscription workflows remain available. No expiry, account or clinical data is rewritten.
- C4: overrides are restored as actual override records. Reconciliation snapshots use JSON and restore both label and FK. Unsafe assignment/scheduled-downgrade/default-plan undo requires its canonical workflow instead of a generic setter. Unsupported assignment/downgrade undo buttons are removed.
- C5: both synchronous/Scribe and async policy lookup failures deny provider work; clinical history is unaffected.
- C6: undo locks the target and rejects superseded actions, changed policy revisions and changed subscription boundaries/scheduled contracts. Repeated reversal is a conflict. Commercial undo cannot enable a security-disabled clinic. Financial undo remains prohibited.

## Deliberate compatibility and safety behavior

`POST /api/v1/admin/subscriptions/reconcile-tenants` now requires reviewed input. A request without selections returns 409 rather than silently mapping every legacy tenant:

```json
{
  "reason": "Owner reviewed these synthetic mappings",
  "mappings": [{
    "tenant_id": 101,
    "plan_id": 3,
    "expected_revision": 1,
    "expected_plan_id": null
  }]
}
```

IDs above are examples, not configuration instructions. An existing valid plan anchor cannot be changed through reconciliation. A stale or ineligible item rejects the whole batch.

Completed chat replay returns a status acknowledgement, not cached patient/tool data whose visibility may have changed. Financial/Scribe replay accepts only a typed result envelope; free-form diagnostic notes are not results. A completed legacy reservation without a trustworthy result is not redispatched.

Historical audits lacking causal policy markers cannot be automatically reversed. The operator receives a conflict and must use current validated controls. This conservative restriction prevents old logs from overriding newer security/payment decisions.

No migrations, price changes, trial/registration changes, clinical calculations, production mutations or real provider calls are included.

## Verification

Evidence directory: `/home/ubuntu/dentix-task-artifacts/completion-20261105/`.

- Before implementation: eight additional independent regression probes failed on the base.
- Focused gate: 117 passed, including new same-key PostgreSQL acquisition/security-race gates, existing PostgreSQL quota/provider concurrency, PR-01 patient/financial/stale-session security, subscription lifecycle/webhooks, policy/RBAC and Super Admin acceptance.
- Frontend focused gate: AuditLogViewer, four passed.
- Ruff and diff whitespace checks passed.
- Final full backend: 1915 passed, 1 skipped, exit 0. The skip is the existing TestClient refresh/session tracking limitation; no test skip was added. Frontend full: 178 files / 1184 tests passed. Production build and design guardrails completed; the latter reports pre-existing design debt without failing. Logs and backend JUnit are retained in the evidence directory.

Legacy reconciliation tests now supply explicit reviewed input. The audit assertion checks the actual JSON plan ID. PR-01 fixture setup now supplies a valid AI plan rather than relying on missing-plan fallback. Role, provider-call, patient-visibility and persisted-state assertions were retained.

New tests: `test_commercial_completion.py` and `test_commercial_completion_postgres.py`. PostgreSQL tests require an explicit isolated TEST_DATABASE_URL; local execution used a fresh cluster on localhost:56483 initialized with the production preflight. This does not certify live staging configuration or a production provider.

## Staging owner review path

1. Confirm the deployed revision and approved plan configuration.
2. Repeat one AI request with one key in chat and financial analysis: no second provider dispatch or tool execution; changed payload/actor conflicts.
3. Review pending/uncertain outcomes and shared quota across users. Check disabled/zero plans and future paid-period boundaries.
4. Save an AI deny; verify provider work stays blocked, including a policy-store failure in the isolated test gate.
5. Preview reconciliation; missing selection or a stale revision must not write. Apply an explicitly reviewed synthetic unassigned clinic; verify history/end dates/accounts unchanged.
6. Change a tenant override and undo it; inspect the real effective policy and audit. Supersede an action with a security disable; undo of the older action must conflict.

Use synthetic clinics and mocked provider transport. Actual catalog reconciliation, live provider smoke, push/PR, merge and production promotion remain separate owner-authorized operations.
