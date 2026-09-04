<!-- STATUS: HISTORICAL / NON-AUTHORITATIVE -->
# STATUS: HISTORICAL / NON-AUTHORITATIVE
> **Archived Document** — This file records historical V2.1 pilot evidence and references retired `agent-ci-signal`. It is strictly **NON-AUTHORITATIVE**. Active DENTIX development is governed by `docs/engineering/DEVELOPMENT_WORKFLOW.md`.

---

# DENTIX Workflow V2.1 — Phase 7 Lean Pilot Evidence

## Current status

`BLOCKED_BY_TRUSTED_PROMOTION`

Phase 7 is not complete and no pilot metrics are claimed yet.

The deterministic signal workflow must exist on the repository default branch
before a `workflow_run` pilot can measure the V2.1 lifecycle. The 2026-08-30
preflight found both trusted artifacts absent from `main`:

- `.github/workflows/agent-ci-signal.yml`
- `.github/scripts/evaluate_ci_signal.py`

The active `Protect main and staging` ruleset remains enforced with strict
up-to-date checks, 15 configured entries, 12 unique required contexts, and
GitHub Actions integration ID `15368`.

## Pilot entry criteria

- [ ] The V2.1 bootstrap PR passes all required checks.
- [ ] The trusted signal workflow and evaluator are promoted to `main` through
      the normal protected-branch process.
- [ ] The promotion SHA is recorded.
- [ ] Issue #126 remains `STANDARD`, `risk:clinical-ui`, wave `ODG-L1`.
- [ ] The pilot PR records its initial head SHA and applies
      `agent:awaiting-ci`.
- [ ] The AI/model loop stops immediately after the PR/CI handoff.

## Measurement record

Fill this table from GitHub event timestamps and the accepted pilot evidence.
Do not estimate or fabricate unavailable values.

| Metric | Baseline / target | Pilot result |
|---|---:|---:|
| Accepted requirements | Preserve source coverage | PENDING |
| Model invocations | Record exact count | PENDING |
| Delegate invocations | Record exact count | PENDING |
| Reviewer invocations | One ODG-L1 wave review | PENDING |
| T1 runs | Record exact count | PENDING |
| T2 runs | One wave gate | PENDING |
| T3 runs | Required PR/protected integration | PENDING |
| PR count | One ODG-L1 wave PR | PENDING |
| GitHub workflow count | Record exact count | PENDING |
| AI polling calls | **0** | PENDING |
| READY → VERIFIED wall clock | Record GitHub timestamps | PENDING |
| PR open → green signal latency | Record GitHub timestamps | PENDING |
| First-pass acceptance | Record pass/fail | PENDING |
| Rework commits | Record exact count | PENDING |
| Loaded skills | Domain/gate skills only | PENDING |
| Escaped defects | 0 CRITICAL/HIGH | PENDING |
| AI credits/tokens | Record only if exposed | PENDING |

## Event-driven pilot procedure

1. Create the scoped ODG-L1 implementation branch/PR for Issue #126.
2. Record the PR number and exact head SHA.
3. Confirm the classifier reports `frontend=true`,
   `clinical_ui=true`, `clinical_semantics=false`, and
   `force_full=false` unless actual scope drift requires escalation.
4. Apply `agent:awaiting-ci` and stop the model loop.
5. Let GitHub Actions and `agent-ci-signal.yml` update the persistent state.
6. On a later user/model invocation, read the state once:
   - `agent:ci-green`: record timestamps and complete the evidence table.
   - `agent:ci-red`: load `dentix-systematic-debugging`, inspect the failed
     checks, make the smallest responsible fix, then return to
     `agent:awaiting-ci`.
7. Record the Phase 7 verdict without merging automatically.

## Acceptance

Phase 7 may be marked `PASS` only when the measurement table contains real
pilot evidence and demonstrates:

- unchanged requirement coverage;
- zero model-driven CI polling;
- no unacceptable CRITICAL/HIGH escape;
- reduced reviewer, broad-verification, and PR/CI cycles per accepted
  STANDARD requirement;
- complete clinical visual evidence;
- rework that does not erase the measured efficiency gain.
