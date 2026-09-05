<!-- CLASSIFICATION: ACTIVE -->
# DENTIX Clinical Chart & Odontogram State Disposition

**Audit Date:** 2026-09-04
**Forensic Status:** `DOCUMENTED, NOT RECONCILED`
**Classification:** `ACTIVE`
**Authority:** `PROJECT_STANDARDS.md` & `docs/engineering/DEVELOPMENT_WORKFLOW.md`

---

## 1. Problem Context & Forensic Verdict

During late August and early September 2026, multiple parallel odontogram and clinical chart implementations emerged across different branches and uncommitted workspaces:
1. Canonical live anatomical chart with approved crowns and phase 1 roots.
2. Experimental `clinical-chart-v2/` prototype.
3. Evolutionary `vnext` clinical workflow prototype.
4. Measured clinical anatomy prototype (Issue #144).
5. Foundational SVG and anatomy codex prototypes.

Forensic Verdict: **`DOCUMENTED, NOT RECONCILED`**

> [!IMPORTANT]
> **Movement 0 establishes source-of-truth direction; it does not silently discard unique experimental product work.**
> Declaring the current `staging` implementation as the canonical active development baseline provides immediate development stability, but alternative prototype branches are preserved because they may contain unsalvaged unique work. No branch merge or salvage occurs in this fix pass.

---

## 2. Canonical Active Development Baseline

The single active and canonical clinical chart implementation in DENTIX is:

* **Location**: `frontend/src/features/odontogram/` and `frontend/src/pages/PatientDetails.jsx`
* **Baseline Commit**: `65be3b70f51d8ed203f72e7daa8a1b2838b73724` (merged into `staging`)
* **Key Features**:
  - Restores approved dental crowns and outlines with phase 1 roots anatomy.
  - Connected directly to live patient records and clinical treatment plans.
  - Fully integrated with notation labels, primary/permanent dentition, and responsive RTL/LTR layouts.

**Development Rule**: All new clinical chart features, bugfixes, or enhancements MUST branch from `staging` and modify this canonical codebase. Shadow renderers or parallel odontogram components are strictly prohibited.

---

## 3. Explicit Clinical Branch Dispositions

All clinical branches and snapshots are explicitly classified below to ensure complete transparency without premature deletion:

| Branch / Asset | Status / Disposition | Detail & Preservation Location |
|---|---|---|
| `fix/odontogram-approved-crowns-plus-roots` | **MERGED BASELINE / ACTIVE SOURCE** | Merged into `staging` (`65be3b70`). Represents the authoritative active crown and root baseline. |
| `feature/odontogram-foundation-codex` | **SALVAGE_CANDIDATE** | Contains foundational odontogram SVG assets and anatomical paths. Preserved for future surgical salvage review. Not reconciled. |
| `codex/odg-part1-final-local` | **SALVAGE_CANDIDATE** | Contains Part 1 local odontogram work. Preserved for surgical salvage review. Not reconciled. |
| `feat/odontogram-approval-slice` | **SUPERSEDED** | Active chart path superseded by canonical staging crowns/roots; unique measured tooth geometry is preserved and tracked in open salvage Issue #144. |
| `feature/unified-clinical-workflow-vnext` | **UNRESOLVED / PRESERVATION_ONLY** | Attached to worktree `.worktrees/vnext`. Evolutionary UI workflow prototype. Preserved intact for future design evaluation; not reconciled. |
| `preserve/local-uncommitted-20260904` | **PRESERVATION_ONLY** | Quarantined preservation branch (commit `207bd8b9`) capturing untracked `clinical-chart-v2` and `docs/clinical-vnext` prototypes prior to V3 recovery. Also backed up in external local recovery bundle. |

---

## 4. Preservation & Quarantined Prototypes

The experimental iterations have been preserved and quarantined so that no intellectual work is lost:

1. **`clinical-chart-v2` & `docs/clinical-vnext`**:
   - **Preservation Branch**: `preserve/local-uncommitted-20260904` (commit `207bd8b9`)
   - **External Safety Archive**: External local recovery bundle
   - **Status**: Quarantined prototype; not active in product.

2. **`vnext` Worktree**:
   - **Location**: `.worktrees/vnext` (relative to repository root)
   - **Branch**: `feature/unified-clinical-workflow-vnext` (commit `01280dc9`)
   - **Status**: Preserved as reference prototype for future clinical workflow designs; not reconciled.

---

## 5. Governance & Invariants

* **No Shadow Renders**: AI coding agents and human developers MUST NOT initiate a second or parallel chart component.
* **Evolution over Replacement**: When evolutionary features from `vnext`, `clinical-chart-v2`, or codex assets are brought into the product, they must be merged surgically through standard pull requests into the canonical chart components on `staging`.
* **Explicit Salvage Only**: Salvaging work from `SALVAGE_CANDIDATE` branches requires dedicated, scoped tasks with explicit user approval.
