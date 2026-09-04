# DENTIX — Remote Branch Cleanup R2B Final Semantic Audit Report

- **Execution Date:** 2026-09-02
- **Canonical Repository:** `C:\Users\es\DENTIX-CLEAN`
- **Verified Rescue Bundle:** `C:\Users\es\DENTIX-RESCUE-20260902-063921\dentix-all.bundle`
- **Canonical Staging SHA:** `bed2b6932eaf9d0800a3945754e4dac7671dee6f`

---

## 1. Before

**Exact Remote Branch Count:** **46**

- **Protected / Active Branches (3):**
  - `origin/main`
  - `origin/staging`
  - `origin/feat/odontogram-approval-slice` (Preserved for open GitHub Issue #144)
- **Historical Divergent Branches Analyzed (43):**
  - Finance Family (7 branches)
  - Security / RLS / Auth / Upload Family (7 branches)
  - Production Migration Family (3 branches)
  - Deployment / Dependency / Container Family (7 branches)
  - Documentation / Historical Verification / Audit Family (6 branches)
  - Mobile Family (13 branches)

---

## 2. Cluster Summary

### Cluster 1: Finance Family (7 branches)
- **Branches:** `fix/finance-navigation-deeplinks-20260823`, `fix/finance-server-reports-export-20260823`, `fix/finance-truth-period-aggregates-20260823`, `hotfix/finance-decimal-boundaries-20260823`, `fix/finance-five-destinations-20260823`, `fix/finance-reports-repair-20260823`, `fix/finance-mobile-rtl-a11y-cleanup-20260823`
- **Terminal Branches:** `fix/finance-five-destinations-20260823`, `fix/finance-server-reports-export-20260823`, `fix/finance-truth-period-aggregates-20260823`
- **Semantic Conclusion:** All finance capabilities (Finance V2 truth, period summaries, 5-destination navigation layout, server reports export, PostgreSQL Decimal handling, granular RBAC, and DentixDrawer/DentixDialog migration) are fully merged and active on staging (via PRs #85, #86, #87, #88 and commits `ca900e7`, `3184b3f`, `6868308`, `468e232`).

### Cluster 2: Security / RLS / Auth / Upload Family (7 branches)
- **Branches:** `fix/logout-server-session-revocation`, `fix/file-path-boundary-hardening`, `fix/file-path-boundary-hardening-v2`, `fix/rls-contract-parity-v3`, `test/phase6-tenant-adversarial-contracts`, `test/rls-contract-parity`, `fix/staging-upload-500-20260824`
- **Terminal Branches:** `fix/rls-contract-parity-v3`, `fix/file-path-boundary-hardening-v2`, `fix/staging-upload-500-20260824`, `test/phase6-tenant-adversarial-contracts`
- **Semantic Conclusion:** All security, tenant RLS, file path traversal, multi-device session isolation, and upload error handling are fully merged or superseded by modern architecture on staging (including `models.UserSession`, RLS migration `d4e5f6a7b8c9_subscription_payments_rls.py`, `test_cross_tenant_http_adversarial.py`, and `test_file_service_path_boundary.py`).

### Cluster 3: Production Migration Family (3 branches)
- **Branches:** `fix/production-migration-contract`, `fix/production-migration-contract-staging`, `fix/production-migration-contract-v2`
- **Terminal Branch:** `fix/production-migration-contract-v2`
- **Semantic Conclusion:** Production preflight authority, startup migration contracts, and separation of migration owner vs runtime roles in CI are fully merged and active on staging (commits `5670057` and `215b2f9`).

### Cluster 4: Deployment / Dependency / Container Family (7 branches)
- **Branches:** `chore/python-dependency-normalization`, `chore/retire-legacy-deployment-surfaces`, `chore/retire-legacy-requirements`, `chore/production-container-nonroot-hardening`, `chore/git-release-governance`, `test/stale-deployment-recovery-contract`, `test/stale-deployment-recovery-contract-v2`
- **Terminal Branches:** `chore/git-release-governance`, `test/stale-deployment-recovery-contract-v2`, `chore/production-container-nonroot-hardening`, `chore/retire-legacy-requirements`
- **Semantic Conclusion:** Staging utilizes canonical `pyproject.toml` / `uv.lock`, has retired all legacy deployment surfaces (Caddyfile, Procfile, legacy Dockerfiles), enforces non-root container hardening, maintains active branch governance workflows, and tests stale chunk recovery.

### Cluster 5: Documentation / Historical Verification / Audit Family (6 branches)
- **Branches:** `docs/live-production-surface-verification`, `docs/live-production-surface-verification-v2`, `docs/phase8-truth-normalization`, `docs/phase8-truth-normalization-v2`, `chore/plan-01-project-truth-inventory`, `chore/mobile-pr22-recovery-audit`
- **Terminal Branches:** N/A (Documentation artifacts)
- **Semantic Conclusion:** Temporary phase ledgers, historical audits, and point-in-time documentation from August 2026. Living documentation on staging (`PROJECT_STANDARDS.md`, `PROJECT_TRUTH.md`) is the canonical source of truth.

### Cluster 6: Mobile Family (13 branches)
- **Branches:** `fix/mobile-ux-responsive-forensic`, `feat/mobile-ux-responsive-forensic-pass`, `test/mobile-recovery-integration`, `fix/mobile-overlay-patient-kpi-regressions`, `fix/mobile-appointments`, `fix/mobile-dashboard-tables`, `fix/mobile-inventory`, `fix/mobile-labs`, `fix/mobile-patient-clinical`, `fix/mobile-shared-primitives`, `fix/mobile-shell-current`, `test/mobile-responsive-gate`, `release/mobile-staging-to-main-20260820`
- **Terminal Branches:** `release/mobile-staging-to-main-20260820`, `test/mobile-recovery-integration`
- **Semantic Conclusion:** Historical PR #22 forensic changes were decomposed, recovered into staging in atomic scoped slices, promoted to main (`10b394d`), and subsequently upgraded into the PWA architecture (`9d3e0ba`).

---

## 3. Deleted Superseded (35 branches)

1. `fix/finance-navigation-deeplinks-20260823`
2. `fix/finance-server-reports-export-20260823`
3. `fix/finance-truth-period-aggregates-20260823`
4. `hotfix/finance-decimal-boundaries-20260823`
5. `fix/finance-five-destinations-20260823`
6. `fix/finance-reports-repair-20260823`
7. `fix/finance-mobile-rtl-a11y-cleanup-20260823`
8. `fix/logout-server-session-revocation`
9. `fix/file-path-boundary-hardening`
10. `fix/file-path-boundary-hardening-v2`
11. `fix/rls-contract-parity-v3`
12. `test/phase6-tenant-adversarial-contracts`
13. `test/rls-contract-parity`
14. `fix/staging-upload-500-20260824`
15. `fix/production-migration-contract`
16. `fix/production-migration-contract-staging`
17. `fix/production-migration-contract-v2`
18. `chore/python-dependency-normalization`
19. `chore/retire-legacy-deployment-surfaces`
20. `chore/retire-legacy-requirements`
21. `chore/production-container-nonroot-hardening`
22. `chore/git-release-governance`
23. `test/stale-deployment-recovery-contract`
24. `test/stale-deployment-recovery-contract-v2`
25. `feat/mobile-ux-responsive-forensic-pass`
26. `test/mobile-recovery-integration`
27. `fix/mobile-overlay-patient-kpi-regressions`
28. `fix/mobile-appointments`
29. `fix/mobile-dashboard-tables`
30. `fix/mobile-inventory`
31. `fix/mobile-labs`
32. `fix/mobile-patient-clinical`
33. `fix/mobile-shared-primitives`
34. `fix/mobile-shell-current`
35. `test/mobile-responsive-gate`

**Total Deleted Superseded:** **35**

---

## 4. Deleted Historical Only (8 branches)

1. `docs/live-production-surface-verification`
2. `docs/live-production-surface-verification-v2`
3. `docs/phase8-truth-normalization`
4. `docs/phase8-truth-normalization-v2`
5. `chore/plan-01-project-truth-inventory`
6. `chore/mobile-pr22-recovery-audit`
7. `fix/mobile-ux-responsive-forensic`
8. `release/mobile-staging-to-main-20260820`

**Total Deleted Historical Only:** **8**

---

## 5. Deleted Redundant Cluster Ancestors (0 branches)

**Total Deleted Redundant Ancestors:** **0**

---

## 6. Salvage Queue (0 retained salvage branches among the 43)

All 43 historical branches have been accounted for: their useful features are already present, enhanced, or superseded on current staging.

- **Note on Issue #144:** `feat/odontogram-approval-slice` remains preserved on remote for open Issue #144.

---

## 7. Review Required (0 branches)

**Total Review Required:** **0**

---

## 8. Hard Preserved Branches (3 branches)

1. `main`
2. `staging`
3. `feat/odontogram-approval-slice` (Open GitHub Issue #144)

---

## 9. After

**Exact Remote Branch Count:** **3**

```text
  origin/HEAD -> origin/main
  origin/feat/odontogram-approval-slice
  origin/main
  origin/staging
```

---

## 10. Target State Assessment

Every remaining remote branch has a clear, documented, and governed purpose:
- `main`: Production authoritative branch.
- `staging`: Pre-production integration branch.
- `feat/odontogram-approval-slice`: Actively tracked by open GitHub Issue #144 for measured odontogram geometry evaluation.

GitHub is no longer used as an unindexed archive of historical experiments. Full disaster recovery is permanently preserved in `C:\Users\es\DENTIX-RESCUE-20260902-063921\dentix-all.bundle`.

---

## 11. Verdict

**`REMOTE_R2B_COMPLETE`**
