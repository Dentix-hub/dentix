# DENTIX Clinical Chart & Odontogram State Disposition

**Audit Date:** 2026-09-04  
**Status:** ACTIVE TRUTH RECORD — MOVEMENT 0  
**Authority:** `PROJECT_STANDARDS.md` & `docs/engineering/DEVELOPMENT_WORKFLOW.md`

---

## 1. Problem Context & Duplicate Work Prevention

During late August and early September 2026, multiple parallel odontogram and clinical chart implementations emerged across different branches and uncommitted workspaces:
1. Canonical live anatomical chart with approved crowns and phase 1 roots.
2. An experimental `clinical-chart-v2/` prototype.
3. A `vnext` evolutionary chart prototype.

This document establishes the canonical single source of truth for the DENTIX clinical chart to prevent shadow implementations or duplicate codebases from developing concurrently.

---

## 2. Canonical Production Truth

The single active and canonical clinical chart implementation in DENTIX is:

* **Location**: `frontend/src/features/odontogram/` and `frontend/src/pages/PatientDetails.jsx`
* **Commit**: `65be3b70f51d8ed203f72e7daa8a1b2838b73724` (merged into `staging`)
* **Key Features**:
  - Restores approved dental crowns and outlines with phase 1 roots anatomy.
  - Connected directly to live patient records and clinical treatment plans.
  - Fully integrated with notation labels, primary/permanent dentition, and responsive RTL/LTR layouts.

**Rule**: All new clinical chart features, bugfixes, or enhancements MUST branch from `staging` and modify this canonical codebase.

---

## 3. Preserved Prototypes & Experimental Work

The experimental iterations have been preserved and quarantined so that no intellectual work is lost:

1. **`clinical-chart-v2` & `docs/clinical-vnext`**:
   - **Preservation Branch**: `preserve/local-uncommitted-20260904` (commit `207bd8b9`)
   - **External File Backup**: `C:\Users\es\DENTIX_RECOVERY_20260904_075309\untracked-backup\frontend\src\features\clinical-chart-v2\`
   - **External Docs Backup**: `C:\Users\es\DENTIX_RECOVERY_20260904_075309\untracked-backup\docs\clinical-vnext\`

2. **`vnext` Worktree**:
   - **Location**: `C:\Users\es\DENTIX\.worktrees\vnext`
   - **Branch**: `feature/unified-clinical-workflow-vnext` (commit `01280dc9`)
   - **Status**: Preserved as a reference prototype for future clinical workflow designs.

---

## 4. Governance & Development Invariant

* **No Shadow Renders**: AI coding agents and human developers MUST NOT initiate a second or parallel chart component.
* **Evolution over Replacement**: When evolutionary features from `vnext` or `clinical-chart-v2` are brought into the product, they must be merged surgically through standard pull requests into the canonical chart components on `staging`.
