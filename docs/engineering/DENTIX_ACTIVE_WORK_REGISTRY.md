# DENTIX Active Work Registry

This file is the operational source of truth for dispatching new DENTIX work. It records the reconciliation baseline of 2026-09-01: protected `main` at `3c06e4e811172f761a3a3ba84e2866bf8050b1ec` and protected `staging` at `31e3fe138598cc79fa62ae722ea9b777865074d4`.

## Active

| Field | Authority |
| --- | --- |
| Program | Odontogram Part I |
| Foundation | A0-A9 reconciled by PR #141 and authoritative on `staging` |
| Active wave | ODG-L1 |
| Active issue | #126 / ODG-A10 (next only; do not implement while `agent:blocked`) |
| Product branch / PR | None. Create a fresh bounded branch from current `staging` only after #126 becomes `agent:ready`. |
| Target branch | `staging` |
| Touch surface | `frontend/src/features/clinical-chart/rendering/`, `frontend/src/features/clinical-chart/components/`, focused clinical-chart tests, and the odontogram tracker/evidence |
| Dependencies | PR #141 foundation and PR #143 CI-signal synchronization are integrated |
| Blockers | None after the registry/preflight reconciliation PR is protected and #126 is relabeled `agent:ready` |

The reconciliation branch `chore/dtx-active-work-reconciliation` is governance-only and carries this registry plus the Active Work Preflight rule. It is not product implementation.

## Deferred

| Work | Reason | Reactivation condition |
| --- | --- | --- |
| Draft PR #135 / DWF-11 Debate Review | Optional write-concurrency/review lane; not justified during the Lean Pilot | Explicit product decision after Lean Pilot evidence |
| Issue #144 / measured geometry from PR #115 | Unique MIT-attributed geometry requires license, clinical, product, adapter, and visual review | Explicit approval and scheduling against the current native renderer; never merge #115 |
| `feature/unified-clinical-workflow-vnext` at `01280dc9` and its clean worktree | Five unique experimental commits, no PR; the accepted Part I ADR classifies this work as reference/prototype material, not the canonical renderer | Explicit product-authority reactivation after the Part I handoff |
| Primary-checkout `docs/clinical-vnext/` and `frontend/src/features/clinical-chart-v2/` | Preserved user-owned, untracked approval/reference artifacts; decision D-003 keeps them noncanonical | Separate forensic intake after Part I; do not copy, clean, or execute them during ODG-L1 |

## Superseded / Salvage

| Old work | Replacement or evidence | Disposition |
| --- | --- | --- |
| PR #75 | Newer #138/#139 ancestry reconciliation and current protected history | Closed as superseded; no content salvage |
| PR #115 | Current #141 architecture plus bounded salvage issue #144 | Closed; never blind merge |
| PR #76 | Patch-equivalent integration through merged PR #78; #78 is in both protected histories | Closed; no missing domain salvage |
| `feature/odontogram-foundation-codex` at `5d757b52` | PR #141 reconciliation evidence records source range `c0e27897^..5d757b52` and protected refinements | Integrated and superseded by current `staging` |

## Preserved Orphan Work

- Local histories with unproven unique work remain non-executable and are not cleanup-ready: `backup-before-main-sync`, `chore/agent-stack-normalization`, `backup/pre-github-sync-20260822-f6e762a1`, `codex/production-release-2026-08-13`, `develop`, and `temp-cherry-pick`.
- Remote mobile/finance/recovery component branches without an open PR have no approved active plan and do not overlap ODG-L1. Preserve them for a separate branch-cleanup audit unless exact integration is proven.
- Clean worktrees proven integrated are `CLEANUP_READY` only; this incident does not delete them: `fix-staging-i18n`, `review-super-admin-hardening`, detached `ci-signal-pagination`, DTX-120/122/123 contract worktrees, `dtx-ai-workflow-v2`, `dtx-odontogram-ticket-graph`, `dtx-sync-ci-signal-main-into-staging`, `odg-foundation-reconcile`, and `DENTIX-consolidate`.
- The clean `dtx-debate-review` worktree remains deferred with PR #135. The clean `vnext` worktree remains preserved reference work. The primary checkout remains protected because it contains untracked user work.

## Next Executable Work

Exactly one: **Issue #126 — ODG-A10, render the stable root layer for all tooth families.**

It may begin only after this registry/preflight change is authoritative on protected `staging`, protected validation is green, and #126 is changed from `agent:blocked` to `agent:ready`. Issues #127-#133 remain blocked by their recorded dependency graph.
