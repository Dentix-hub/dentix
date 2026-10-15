---
name: dentix-testing-verification
description: Select the minimum sufficient verification gate for a DENTIX change. Activate when deciding what tests to run, not to duplicate testing across layers.
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
| PR → CI | CI is authoritative. Stop. |

## Reporting

**Success**: `PASS — <command> — <summary>` (one line)

**Failure**: Include failing command, relevant error, classification (new / pre-existing baseline), and next action.

HIGH_RISK or final reports may include additional evidence where useful.
