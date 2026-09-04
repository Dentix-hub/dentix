# DENTIX Branch Cleanup & Maintenance Guide

**Document Classification:** ENGINEERING RUNBOOK  
**Status:** DRAFT — FOR USE POST-REMOTE-QUALIFICATION  
**Authority:** `docs/engineering/DEVELOPMENT_WORKFLOW.md`

---

## 1. Prerequisites & Hard Gates

Branch cleanup MUST NOT be executed until ALL of the following criteria are met:

1. **Local Qualification**: All movements (Movement 0, Movement 1, Movement 2, Movement 3A) return `PASS`.
2. **Remote Qualification**: Remote pilots (Normal PR and High-Risk PR) succeed on GitHub.
3. **Verified Backup**: An external, verified Git bundle exists outside the repository with recorded SHA-256 hash.
4. **Explicit User Approval**: The user has reviewed and explicitly authorized remote branch pruning.

---

## 2. GitHub Platform Configuration

Enable automatic deletion of head branches upon PR merge:

1. Navigate to GitHub: **Repository Settings -> General -> Pull Requests**.
2. Check **Automatically delete head branches** (`delete_branch_on_merge = true`).
3. Alternatively, via GitHub CLI (requires repository admin permissions):
   ```bash
   gh repo edit Dentix-hub/dentix --delete-branch-on-merge=true
   ```

---

## 3. Pruning Safe Merged Branches

Only branches documented as `MERGED_TO_STAGING` in `docs/engineering/BRANCH_DISPOSITION_LEDGER.md` may be deleted.

### Step 3.1: Verify State
Run the repository state auditor:
```bash
python scripts/audit_development_state.py
```
Ensure the target branches appear in the `Merged into staging` list.

### Step 3.2: Delete Local Merged Branches
```powershell
# Safe deletion (will fail if branch is not fully merged)
git branch -d fix/odontogram-approved-crowns-plus-roots
git branch -d fix/odontogram-live-anatomy-integration
git branch -d fix/odontogram-phase1-reconciliation
git branch -d hotfix/ci-signal-pagination
git branch -d chore/github-actions-normalization
```

### Step 3.3: Delete Remote Merged Branches (One-by-One)
```powershell
git push origin --delete fix/odontogram-approved-crowns-plus-roots
git push origin --delete fix/odontogram-live-anatomy-integration
git push origin --delete fix/odontogram-phase1-reconciliation
git push origin --delete chore/github-actions-normalization
```

---

## 4. Protected Branches (NEVER DELETE)

The following local and remote branches must **never** be pruned:

* `main` and `staging` (protected canonical branches)
* `preserve/*` (historical local recovery snapshots)
* `backup/*` (pre-sync backup branches)
* `codex/production-release-2026-08-13` (historical release milestone)
* `feature/unified-clinical-workflow-vnext` (active worktree prototype)
* `chore/dtx-debate-review-integration` (active worktree branch)
