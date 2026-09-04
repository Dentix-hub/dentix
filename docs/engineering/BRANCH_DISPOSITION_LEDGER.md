# DENTIX Local Branch Disposition Ledger

**Authority:** `docs/engineering/DEVELOPMENT_WORKFLOW.md`
**Classification:** `ARCHITECTURE-REFERENCE`
**Scope:** Repository branch inventory, forensic ancestry verification, and disposition governance.

---

## 1. Governance & Disposition Policy

To prevent branch sprawl and ensure that no unmerged clinical or infrastructure work is lost, this ledger governs the lifecycle of all local branches.

### Core Principles
1. **Audit Snapshot vs. Mutable State**: Git branch heads are mutable pointers. This document records an **AUDIT SNAPSHOT** tied to a specific baseline commit, and assigns a deliberate **DISPOSITION** that remains authoritative until formally updated.
2. **Clinical Work Preservation**: Movement 0 establishes source-of-truth direction; it does **not** silently discard unique experimental product work. Unmerged clinical branches are explicitly marked as `SALVAGE_CANDIDATE`, `SUPERSEDED`, or `UNRESOLVED / PRESERVATION_ONLY`.
3. **Pruning Rules**: No branch may be deleted locally or remotely without:
   - Verification that its commits are fully contained in `staging` (`git merge-base --is-ancestor`),
   - An off-site verified Git bundle backup,
   - Explicit user approval post-Remote Qualification.

---

## 2. Audit Snapshot

* **Snapshot Timestamp:** 2026-09-04T08:50:00Z
* **Baseline Staging SHA:** `65be3b70f51d8ed203f72e7daa8a1b2838b73724`
* **Baseline Main SHA:** `86fbf612c0290f2534eb6e191af78ce2eaa7df26`
* **Local Workspace HEAD:** `d2f5a18b7d537acf903e842495cc334c13cff8e7` (`chore/workflow-v3-movement-0`)

| Branch Name | Snapshot SHA | Category | Ahead vs Staging | Behind vs Staging | Staging Ancestor? |
|---|---|---|---:|---:|:---:|
| `staging` | `65be3b70` | Canonical Baseline | 0 | 0 | YES |
| `main` | `46584940` | Canonical Production | 0 | 174 | YES |
| `chore/workflow-v3-movement-0` | `d2f5a18b` | Active Work | 1 | 0 | NO (ahead) |
| `fix/odontogram-approved-crowns-plus-roots` | `3aa54273` | Clinical Baseline Source | 0 | 1 | YES |
| `fix/odontogram-live-anatomy-integration` | `347d0f06` | Clinical Merged | 0 | 7 | YES |
| `fix/odontogram-phase1-reconciliation` | `72ea5c3b` | Clinical Merged | 0 | 28 | YES |
| `chore/github-actions-normalization` | `83767141` | Infrastructure Merged | 0 | 34 | YES |
| `hotfix/ci-signal-pagination` | `613c1724` | Infrastructure Merged | 0 | 91 | YES |
| `preserve/local-uncommitted-20260904` | `207bd8b9` | Safety Snapshot | 1 | 1 | NO |
| `backup/pre-github-sync-20260822-f6e762a1` | `f6e762a1` | Safety Snapshot | 8 | 403 | NO |
| `codex/production-release-2026-08-13` | `b35a3c20` | Historical Release | 296 | 981 | NO |
| `temp-cherry-pick` | `eb3f5ef0` | Historical Scratch | 279 | 981 | NO |
| `feat/odontogram-approval-slice` | `885a1738` | Clinical Prototype | 5 | 174 | NO |
| `feature/odontogram-foundation-codex` | `9b2c28f9` | Clinical Prototype | 22 | 120 | NO |
| `codex/odg-part1-final-local` | `b67e29b0` | Clinical Prototype | 3 | 52 | NO |
| `feature/unified-clinical-workflow-vnext` | `01280dc9` | Clinical Worktree | 5 | 174 | NO |
| `chore/dtx-debate-review-integration` | `585f9b17` | Infrastructure Worktree | 2 | 94 | NO |
| `develop` | `c2d904e5` | Legacy Branch | 133 | 981 | NO |
| `chore/agent-stack-normalization` | `8340a279` | Legacy Infrastructure | 4 | 697 | NO |

---

## 3. Branch Dispositions

| Branch Name | Disposition | Status | Action / Governance Boundary |
|---|---|---|---|
| `staging` | **CANONICAL_ACTIVE_BASELINE** | **FINAL** | Integration baseline for all feature development. Protected branch. |
| `main` | **CANONICAL_PRODUCTION** | **FINAL** | Production release branch. Protected branch. Promotion target only. |
| `chore/workflow-v3-movement-0` | **ACTIVE_WORK** | **UNRESOLVED** | Active local development branch for Workflow V3 Movement 0. Remains local until qualification. |
| `fix/odontogram-approved-crowns-plus-roots` | **MERGED_BASELINE_SOURCE** | **FINAL** | Canonical odontogram anatomy baseline merged into staging. Safe for pruning post-qualification. |
| `fix/odontogram-live-anatomy-integration` | **MERGED_TO_STAGING** | **FINAL** | Fully merged into staging. Retain until remote qualification; safe for cleanup post-qualification. |
| `fix/odontogram-phase1-reconciliation` | **MERGED_TO_STAGING** | **FINAL** | Fully merged into staging. Retain until remote qualification; safe for cleanup post-qualification. |
| `chore/github-actions-normalization` | **MERGED_TO_STAGING** | **FINAL** | Fully merged into staging. Retain until remote qualification; safe for cleanup post-qualification. |
| `hotfix/ci-signal-pagination` | **MERGED_TO_STAGING** | **FINAL** | Fully merged into staging. Retain until remote qualification; safe for cleanup post-qualification. |
| `preserve/local-uncommitted-20260904` | **PRESERVATION_ONLY** | **FINAL** | Quarantined preservation snapshot of uncommitted clinical prototypes. DO NOT DELETE. |
| `backup/pre-github-sync-20260822-f6e762a1` | **PRESERVATION_ONLY** | **FINAL** | Pre-sync recovery snapshot from 2026-08-22. DO NOT DELETE. |
| `codex/production-release-2026-08-13` | **PRESERVATION_ONLY** | **FINAL** | Release milestone snapshot. DO NOT DELETE. |
| `temp-cherry-pick` | **PRESERVATION_ONLY** | **FINAL** | Historical cherry-pick reference. Preserve locally. |
| `feat/odontogram-approval-slice` | **SUPERSEDED** | **FINAL** | Architecture superseded by approved crowns plus roots. Measured geometry preserved for salvage evaluation (tracked in Issue #144). |
| `feature/odontogram-foundation-codex` | **SALVAGE_CANDIDATE** | **UNRESOLVED** | Contains foundational odontogram SVG assets. Preserved for surgical salvage review. DO NOT DELETE. |
| `codex/odg-part1-final-local` | **SALVAGE_CANDIDATE** | **UNRESOLVED** | Contains Part 1 local odontogram work. Preserved for surgical salvage review. DO NOT DELETE. |
| `feature/unified-clinical-workflow-vnext` | **UNRESOLVED / PRESERVATION_ONLY** | **UNRESOLVED** | Attached to worktree `.worktrees/vnext`. Contains clinical vNext prototypes. Preserved; not yet reconciled. |
| `chore/dtx-debate-review-integration` | **ACTIVE_WORKTREE** | **UNRESOLVED** | Attached to worktree `.worktrees/dtx-debate-review`. Preserved for review integration. |
| `develop` | **UNRESOLVED / PRESERVATION_ONLY** | **UNRESOLVED** | Legacy develop branch. Preserved locally; not reconciled. |
| `chore/agent-stack-normalization` | **UNRESOLVED / PRESERVATION_ONLY** | **UNRESOLVED** | Legacy normalization branch superseded by Workflow V3. Preserved locally. |

---

## 4. Post-Remote Qualification Pruning Policy

When Remote Qualification is completed and explicit user approval is granted:
1. No branch deletion shall occur before verified Git bundles exist off-site.
2. Only branches classified with disposition `MERGED_TO_STAGING` or `MERGED_BASELINE_SOURCE` and status `FINAL` may be deleted (`git branch -d`).
3. Branches classified as `SALVAGE_CANDIDATE`, `PRESERVATION_ONLY`, or `UNRESOLVED` must remain untouched until dedicated review passes are scheduled.
