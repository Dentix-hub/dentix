# DENTIX Local Branch Disposition Ledger

**Audit Date:** 2026-09-04  
**Status:** ACTIVE AUDIT LEDGER — MOVEMENT 0  
**Authority:** `docs/engineering/DEVELOPMENT_WORKFLOW.md`

This ledger classifies all existing local branches in the DENTIX repository to prevent uncoordinated branch sprawl, avoid accidental loss of unmerged work, and prepare for safe branch hygiene after Remote Qualification.

---

## 1. Classification Taxonomy

Branches are grouped into three unambiguous categories:

1. **`MERGED_TO_STAGING`**: Branches whose work is 100% contained in current `staging` (`65be3b70`). These are safe for local and remote deletion after Remote Qualification completes.
2. **`HISTORICAL_PRESERVED`**: Permanent snapshot branches containing legacy release milestones or safety recovery snapshots. These must **never** be deleted without explicit off-site archive proof.
3. **`ACTIVE_OR_FEATURE_SPECIFIC`**: Branches holding ongoing feature prototypes or worktree integrations. These are preserved intact.

---

## 2. Comprehensive Branch Inventory

| Branch Name | Classification | Ahead | Behind | HEAD Commit | Disposition / Action |
|---|---|---:|---:|---|---|
| `staging` | **CANONICAL** | 0 | 0 | `65be3b70` | Canonical integration branch. Protected. |
| `main` | **CANONICAL** | 0 | 44 | `86fbf612` | Canonical production branch. Protected. |
| `chore/workflow-v3-movement-0` | **ACTIVE WORK** | 0 | 0 | `65be3b70` | Current active feature branch for Workflow V3 Movement 0. |
| `chore/github-actions-normalization` | `MERGED_TO_STAGING` | 0 | 1 | `a0df449c` | Fully merged into staging. Safe for cleanup post-remote qualification. |
| `fix/odontogram-approved-crowns-plus-roots` | `MERGED_TO_STAGING` | 0 | 0 | `3aa54273` | Fully merged into staging. Safe for cleanup post-remote qualification. |
| `fix/odontogram-live-anatomy-integration` | `MERGED_TO_STAGING` | 0 | 2 | `cc78ce88` | Fully merged into staging. Safe for cleanup post-remote qualification. |
| `fix/odontogram-phase1-reconciliation` | `MERGED_TO_STAGING` | 0 | 4 | `91f9e6bf` | Fully merged into staging. Safe for cleanup post-remote qualification. |
| `hotfix/ci-signal-pagination` | `MERGED_TO_STAGING` | 0 | 11 | `1b9630ea` | Fully merged into staging. Safe for cleanup post-remote qualification. |
| `preserve/local-uncommitted-20260904` | `HISTORICAL_PRESERVED` | 1 | 1 | `207bd8b9` | Snapshot of untracked clinical-chart-v2 and docs before V3 recovery. DO NOT DELETE. |
| `backup/pre-github-sync-20260822-f6e762a1` | `HISTORICAL_PRESERVED` | 8 | 403 | `f6e762a1` | Historical pre-sync backup from 2026-08-22. DO NOT DELETE. |
| `codex/production-release-2026-08-13` | `HISTORICAL_PRESERVED` | 296 | 981 | `4e43e260` | Historical August 2026 production release milestone. DO NOT DELETE. |
| `temp-cherry-pick` | `HISTORICAL_PRESERVED` | 279 | 981 | `c830b86a` | Historical cherry-pick branch. Preserve locally. |
| `feature/unified-clinical-workflow-vnext` | `ACTIVE_OR_FEATURE_SPECIFIC` | 5 | 174 | `01280dc9` | Attached to `.worktrees/vnext`. Contains clinical vNext prototypes. Preserved. |
| `chore/dtx-debate-review-integration` | `ACTIVE_OR_FEATURE_SPECIFIC` | 2 | 94 | `585f9b17` | Attached to `.worktrees/dtx-debate-review`. Preserved. |
| `feat/odontogram-approval-slice` | `ACTIVE_OR_FEATURE_SPECIFIC` | 5 | 174 | `d601b34e` | Feature slice for odontogram approval. Preserved. |
| `feature/odontogram-foundation-codex` | `ACTIVE_OR_FEATURE_SPECIFIC` | 22 | 120 | `b4931a5e` | Foundational odontogram SVGs and assets. Preserved. |
| `codex/odg-part1-final-local` | `ACTIVE_OR_FEATURE_SPECIFIC` | 3 | 52 | `32145e69` | Part 1 local odontogram work. Preserved. |
| `develop` | `ACTIVE_OR_FEATURE_SPECIFIC` | 133 | 981 | `9a82f341` | Legacy develop branch. Preserved. |
| `chore/agent-stack-normalization` | `ACTIVE_OR_FEATURE_SPECIFIC` | 4 | 697 | `7650ea9c` | Legacy agent stack normalization branch. Preserved. |

---

## 3. Post-Remote Qualification Pruning Policy

When Remote Qualification is completed and user approval is granted:
1. No branch deletion shall occur before verified Git bundles exist off-site.
2. Only branches classified as `MERGED_TO_STAGING` may be deleted (`git branch -d`).
3. Historical and active feature branches remain untouched.
