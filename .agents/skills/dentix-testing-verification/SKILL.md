---
name: dentix-testing-verification
description: Select the minimum sufficient verification gate for a DENTIX change. Activate when deciding what tests to run, not to duplicate testing across layers. Also activate when fixing a bug.
---

# DENTIX Verification Policy

## Purpose

This skill answers one question: **What is the minimum sufficient verification for this diff?**

It does NOT create a separate testing workflow. It selects the gate.

## Principles

1. **CI is the integration authority.** Active CI configuration (`.github/workflows/ci.yml`) owns required commands, coverage flags, and thresholds. Do not hard-code thresholds here.
2. **No fake passes.** Every claimed test result must be backed by executed commands and real exit codes.
3. **Baseline separation.** Distinguish pre-existing baseline failures from introduced regressions.
4. **No duplication.** Do not rerun an unchanged expensive gate at the same confidence boundary when no relevant code changed after the previous successful run.

## Verification Cadence

| Phase | What to run |
|---|---|
| During implementation | Smallest targeted test covering the changed behavior |
| Before acceptance | One final relevant verification pass |
| Before PR | Additional subsystem lint/build checks only when appropriate |
| Final slice of a multi-PR plan | One full local run (see DEVELOPMENT_WORKFLOW §4) |
| PR → CI | CI is authoritative. Stop. |

## Reporting

**Success**: `PASS — <command> — <summary>` (one line)

**Failure**: Include failing command, relevant error, classification (new / pre-existing baseline), and next action.

HIGH_RISK or final reports may include additional evidence where useful.

## Test Quality
- Expected values come from an independent source (spec, brief, or worked example), not from the code under test.
- Test through the public interface; mock only external boundaries.
- Finance, ledger and commission tests include at least one hand-worked case with the arithmetic shown in the test.

## Bug-Fix Verification
Applies when a reported bug's root cause is not established by existing evidence.
1. Before hypothesizing, run one command that fails specifically on the reported symptom. Record sanitized output. If reproduction is impossible, stop and report attempted approaches and missing prerequisites.
2. Minimise the repro. Rank up to five plausible, falsifiable hypotheses and present them to the owner; unattended execution may continue only within existing authorization.
3. Change one variable at a time. Tag temporary logs `[DEBUG-<id>]` and remove them (grep) before the PR.
4. Write and run a failing regression test BEFORE the fix, using the narrowest stable public interface (service entry point, API route, or UI behavior) that reproduces the reported bug. If no suitable interface can reproduce it, document the limitation.
5. Use real PostgreSQL for bugs involving RLS, tenant isolation, concurrency or database-level finance behavior; SQLite results do not count. Pure calculation bugs may use unit tests.
6. For finance, auth or clinical fixes, add a test that existing records and permissions on the affected path behave as before (e.g. historical entries unchanged, unauthorized roles still rejected).
7. Repro artifacts, logs and PR text contain no real patient data or secrets: use synthetic data and `<REDACTED>`.
8. State the confirmed root cause in the PR description.
