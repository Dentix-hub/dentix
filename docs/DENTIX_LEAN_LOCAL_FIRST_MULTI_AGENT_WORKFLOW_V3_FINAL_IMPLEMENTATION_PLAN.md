# DENTIX Lean Local-First Multi-Agent Workflow V3
## FINAL IMPLEMENTATION PLAN

**Status:** FINAL — READY FOR CONTROLLED EXECUTION<br>
**Date:** 2026-09-04<br>
**Repository:** `Dentix-hub/dentix`<br>
**Primary local repository:** `C:\Users\es\DENTIX`

---

# 0. Purpose

This plan establishes one lean DENTIX development workflow.

It preserves the strong parts of the current system:

- local-first implementation,
- targeted verification,
- one coherent feature/fix branch,
- one PR to `staging`,
- deterministic CI classification,
- validated staging promotion,
- production-like smoke,
- zero AI CI polling.

It also restores the useful multi-agent separation that was lost during the September workflow simplification:

- **Codex** = leader / planner / risk classifier / acceptance authority,
- **Antigravity** = primary implementer for NORMAL work,
- **Codex high-risk writer** = sensitive-core author for HIGH_RISK work,
- **GitHub** = integration / CI / release boundary,
- optional delegate transport only after local proof.

This plan must never recreate V2 as a second workflow layer.

---

# 1. Constitutional Rule — Exactly One Workflow

There must be exactly one active DENTIX development workflow:

`docs/engineering/DEVELOPMENT_WORKFLOW.md`

Everything else operates under it.

```text
DEVELOPMENT_WORKFLOW.md
        │
        ├── AGENTS.md
        ├── dentix-orchestration
        ├── native DENTIX skills
        ├── optional planning helpers
        ├── optional delegate transport
        └── GitHub CI/CD
```

`dentix-orchestration` is not another workflow.

No skill, historical plan, plugin, delegate config, or review helper may define a competing:

- branch lifecycle,
- issue lifecycle,
- testing lifecycle,
- review lifecycle,
- CI lifecycle,
- release lifecycle.

If a lower-level instruction conflicts with `DEVELOPMENT_WORKFLOW.md`, the lower-level instruction is wrong and must be corrected or archived.

---

# 2. Authority Order

```text
1. NON-NEGOTIABLE SAFETY / INTEGRITY
   - tenant isolation
   - authorization / RBAC
   - privacy
   - clinical record integrity
   - financial integrity
   - data integrity
   - production safety

2. CURRENT USER REQUIREMENT / APPROVED PRODUCT DECISION
   - only within layer-1 constraints

3. PROJECT_STANDARDS.md
   - architecture authority

4. docs/engineering/DEVELOPMENT_WORKFLOW.md
   - development lifecycle authority

5. AGENTS.md
   - cross-runtime execution and safety contract

6. ACTIVE PRODUCT / DOMAIN SPEC
   - product semantics and acceptance criteria

7. RELEVANT .agents/skills/
   - domain implementation guidance

8. EXTERNAL SKILLS
   - optional methodology / transport only

9. GENERAL ENGINEERING PRACTICE
```

Historical plans may preserve product requirements and acceptance criteria, but cannot control current execution mechanics unless the active workflow explicitly adopts them.

---

# 3. Precondition #0 — Local-First Isolation Contract

Workflow V3 must qualify locally before any GitHub write.

## During Local Qualification

Forbidden:

```text
git push
PR creation
remote branch creation
remote branch deletion
GitHub setting changes
GitHub Issue creation for workflow execution
deliberate CI triggering
branch-protection mutation
```

Allowed:

- local branches,
- local commits,
- local tests,
- local review,
- local Git bundles,
- local task briefs,
- Antigravity execution,
- Codex execution,
- read-only GitHub queries,
- `git fetch` after preservation and Git-integrity repair.

## Remote Qualification is Separate

```text
LOCAL QUALIFICATION
        ↓
LOCAL_ACCEPTANCE = PASS
        ↓
STOP
        ↓
EXPLICIT USER APPROVAL
        ↓
REMOTE QUALIFICATION
```

GitHub-specific behavior must not be claimed proven locally.

---

# 4. Mandatory Backup Rule

After every completed local movement:

```powershell
git bundle create <external-path>\DENTIX_V3_<movement>_<timestamp>.bundle --all
git bundle verify <external-path>\DENTIX_V3_<movement>_<timestamp>.bundle
Get-FileHash <bundle> -Algorithm SHA256
```

Requirements:

1. bundle stored outside `C:\Users\es\DENTIX`,
2. verification passes,
3. SHA256 recorded,
4. second copy stored off-device when practical:
   - Google Drive,
   - USB,
   - another disk,
   - trusted external storage.

A movement is not complete until its backup gate passes.

---

# 5. Current Verified Discovery Facts

Local discovery found:

- primary workspace was on `fix/odontogram-approved-crowns-plus-roots`,
- local HEAD was `3aa5427354d6d253b135893c4196e4abfa96bd01`,
- valuable untracked work existed, including:
  - `frontend/src/features/clinical-chart-v2/`,
  - `docs/clinical-vnext/`,
  - multiple local workflow/product documents,
- a corrupted Codex ref existed under `.git/refs/codex/turn-diffs/captures/.../base`,
- `git log --all` and `git fsck` were affected,
- three registered worktrees existed,
- an unregistered `odg-l3` worktree remnant existed,
- multiple competing odontogram/clinical-chart implementations existed,
- `gh` was installed and authenticated,
- `agy 1.1.22` was installed,
- `codex-cli 0.147.0` was installed,
- `codex.cmd` works while bare `codex` resolves to a blocked PowerShell `.ps1`,
- delegate skills already existed globally:
  - `delegate-setup`,
  - `agy-delegate`,
  - `codex-delegate`,
- `grill-with-docs`, `wayfinder`, and `to-spec` were not found.

The earlier local audit used stale `origin/staging` data after a failed fetch.

Authoritative GitHub verification showed current `staging` at:

`65be3b70f51d8ed203f72e7daa8a1b2838b73724`

and that commit contains:

`3aa5427354d6d253b135893c4196e4abfa96bd01`

as a parent.

Therefore the older local conclusion that `3aa54273...` was still unmerged must not be reused after refresh.

---

# 6. Preservation Pass — Before Movement 0

No V3 implementation starts before preservation completes.

## Required preservation layers

Valuable untracked work must exist in all three forms:

```text
1. external filesystem backup
2. local preservation branch + commit
3. external verified Git bundle
```

No push.

## Broken-ref recovery

The exact broken Codex ref must be:

1. confirmed,
2. copied outside the repo,
3. quarantined,
4. followed by successful `git fsck`,
5. followed by successful `git log --all`.

No generalized ref cleanup.

## Origin refresh

Only after preservation and Git integrity pass:

```text
git fetch origin
```

Then local remote-tracking SHAs must be cross-checked against authenticated GitHub API values.

## Worktrees

Registered worktrees are not deleted during preservation.

The orphaned `odg-l3` path is inventoried first.

## Preservation Exit Gate

```text
Git integrity: PASS
valuable local work preserved: PASS
external backup manifest: PASS
local preservation commit: PASS
Git bundle verification: PASS
working tree controlled: PASS
origin refs refreshed: PASS
no remote write: PASS
```

Only then does Movement 0 begin.

---

# 7. Preserve the Current GitHub Lifecycle

```text
LOCAL WORK
    ↓
ONE COHERENT FEATURE/FIX
    ↓
ONE SHORT-LIVED BRANCH
    ↓
TARGETED LOCAL VERIFICATION
    ↓
ONE PR → staging
    ↓
AUTHORITATIVE CI
    ↓
MERGE
    ↓
STAGING DEPLOYMENT
    ↓
PRODUCTION-LIKE STAGING SMOKE
    ↓
PROMOTE WHEN RELEASE-READY
    ↓
PRODUCTION DEPLOYMENT + HEALTH CHECK
```

Do not restore:

- issue-per-microtask,
- PR-per-microtask,
- worktree-per-task,
- full test matrix after every edit,
- full CI duplication at each branch hop,
- AI CI polling.

---

# 8. Two Risk Classes Only

Use only:

```text
NORMAL
HIGH_RISK
```

Do not restore FAST/STANDARD/HIGH_RISK as three separate execution workflows.

Reuse the same risk concepts already encoded by the current CI classifier.

---

# 9. NORMAL Work

Examples:

- ordinary frontend,
- ordinary backend,
- tests,
- docs,
- routine debugging,
- performance,
- non-sensitive refactors,
- isolated product changes.

Flow:

```text
Codex Leader
    ↓
Antigravity Implementer
    ↓
targeted tests
    ↓
Codex Leader acceptance review
```

Codex Leader acceptance is not called independent review.

Acceptance is based on:

- real `git diff`,
- scope,
- acceptance criteria,
- targeted test evidence.

---

# 10. HIGH_RISK Work

Includes material changes to:

- authentication,
- RBAC,
- tenant isolation,
- RLS,
- finance,
- ledger/payment semantics,
- schema,
- migrations,
- irreversible data,
- clinical semantics,
- medical records,
- security controls,
- deployment/governance,
- major shared contracts.

## Writer policy

Sensitive core:

```text
Codex High-Risk Writer
```

Allowed Antigravity adjacent work:

- tests,
- docs,
- fixtures,
- presentation-only UI around unchanged sensitive contracts,
- mechanical support files outside the sensitive core.

## Review policy

HIGH_RISK requires a separate read-only reviewer context.

Roles:

```text
Codex Leader
Codex High-Risk Writer
Fresh/Independent Reviewer
```

A writer reviewing its own summary is not independent review.

A fresh isolated read-only Codex context is acceptable as fallback if no genuinely different safe reviewer is available.

---

# 11. Native DENTIX Skills

Keep the current 10:

1. `dentix-plan-execution`
2. `dentix-backend-fastapi`
3. `dentix-frontend-react`
4. `dentix-mobile-flutter`
5. `dentix-security-tenancy-rbac`
6. `dentix-database-migrations`
7. `dentix-testing-verification`
8. `dentix-systematic-debugging`
9. `dentix-code-review`
10. `dentix-performance`

Add exactly one:

11. `dentix-orchestration`

Target:

```text
11 native DENTIX skills
```

No return to the 183+ skill ecosystem.

---

# 12. Lean `dentix-orchestration`

It is a router, not a workflow framework.

Responsibilities:

1. read current authority,
2. classify NORMAL vs HIGH_RISK,
3. load only relevant native skills,
4. perform active-work reconciliation,
5. detect duplicate/shadow work,
6. create bounded local task brief,
7. choose writer,
8. define allowed/forbidden paths,
9. enforce snapshot/failure contract,
10. inspect real diff,
11. trigger acceptance/review boundary,
12. stop at PR/CI handoff.

It must not own:

- CI thresholds,
- coverage percentages,
- backend architecture,
- frontend architecture,
- security semantics,
- branch-protection details,
- duplicated test commands.

---

# 13. Duplicate-Work Guard

Before substantial work:

1. inspect local branches,
2. inspect remote branches read-only,
3. inspect open PRs when relevant,
4. inspect blocked/open Issues when ticketed,
5. search commits for ticket IDs,
6. detect competing implementation.

For ticketed work:

```bash
git log --all --oneline --grep="<TICKET_ID>"
```

If unreconciled prior work exists:

```text
STOP NEW IMPLEMENTATION
```

Choose one:

- continue,
- reconcile,
- supersede,
- salvage,
- archive/delete later.

Never create a second implementation silently.

---

# 14. Delegate Write Safety Contract

Before a write-capable delegate runs, record:

```text
task_id
current branch
base_sha
status_before
allowed_paths
forbidden_paths
risk_class
timeout
task_brief
```

Requirements:

- unrelated user changes identifiable,
- bounded touch surface,
- no ambiguous mixed working tree,
- no destructive rollback assumptions.

---

# 15. Delegate Failure / Rollback Contract

After delegation:

1. inspect `git status`,
2. inspect real `git diff`,
3. reject forbidden-path changes,
4. run targeted verification,
5. only then accept.

On crash/timeout/non-zero exit:

If safe restoration is provable:

- restore only delegate-created/modified paths,
- remove only delegate-created files proven absent before execution,
- verify status equals `status_before`.

If not provable:

```text
STOP
PRESERVE DIFF
REPORT FAILED/PARTIAL DELEGATION
REQUIRE RECONCILIATION
```

Generic recovery must not use:

```text
git reset --hard
git clean -fd
```

---

# 16. External Skill Policy

External skills are not authorities.

## Optional planning helpers

Install/use only if later useful:

- `grill-with-docs`
- `wayfinder`
- `to-spec`

Use selectively.

## Not core dependencies

Do not require:

- `to-tickets`
- external `implement`
- external `tdd`
- external `code-review`

DENTIX already has native execution/testing/review contracts.

## Already installed but disabled for DENTIX

`babysit-pr`:

```text
DO NOT USE
```

because it risks reintroducing PR/CI polling.

`debate-review`:

```text
OPTIONAL / DISABLED BY DEFAULT
```

until independent read-only review lanes are proven.

ECC may remain externally cached but has no DENTIX authority.

---

# 17. One Owner Per Dynamic Rule

No native skill hard-codes CI coverage thresholds.

Example:

Bad:

```text
Coverage must be 70%.
```

Correct:

```text
Use the active CI configuration as the source of truth.
```

Owners:

| Rule | Owner |
|---|---|
| Architecture | `PROJECT_STANDARDS.md` |
| Development lifecycle | `DEVELOPMENT_WORKFLOW.md` |
| Cross-agent invariants | `AGENTS.md` |
| CI coverage | `.github/workflows/ci.yml` |
| CI risk classification | classifier script |
| Branch governance | `branch-governance.yml` |
| Backend guidance | backend skill |
| Frontend guidance | frontend skill |
| Security guidance | security skill |
| Testing method | testing skill |
| Review method | review skill |

---

# 18. Documentation Classification

Every workflow/agent document must be:

```text
ACTIVE
PRODUCT-SPEC
RUNTIME-AI
HISTORICAL
```

Historical files must begin with:

```text
STATUS: HISTORICAL / NON-AUTHORITATIVE
```

Historical files may preserve history/evidence/product requirements, but cannot control current workflow execution.

---

# 19. Documents Requiring Cleanup

Review at minimum:

- `docs/soul.md`
- `docs/HERMES_AGENT_GUIDE.md`
- old V2/V2.1 workflow evidence
- old delegate dry-runs
- retired `agent-ci-signal` references
- obsolete `.agent/` references
- stale coverage statements
- old workflow plans in active engineering paths

`docs/AI_GOVERNANCE_RULES.md` must clearly separate:

- in-product DENTIX AI runtime governance,
- repository coding-agent development governance.

---

# 20. Static Authority Guard

Create:

`.github/scripts/check_agent_authority.py`

It is a deterministic linter.

Checks may include:

1. skill catalog matches directories,
2. no retired `.agent/` references in active authority,
3. no retired `agent-ci-signal` references,
4. no stale hard-coded coverage values in native skills,
5. one active development workflow authority,
6. historical docs have archive headers,
7. active docs link to current authorities,
8. external skills are never higher-authority than DENTIX rules.

It is not a semantic AI oracle.

---

# 21. Separate Live Repository Audit

Use a separate read-only local tool/process for:

- remote branch inventory,
- ahead/behind counts,
- stale merged branches,
- duplicate ticket work,
- blocked issues,
- main/staging governance drift,
- PR state.

Suggested local tool:

`scripts/audit_development_state.py`

Do not mix live GitHub state into the static authority linter unless necessary.

---

# 22. GitHub Authentication

Preferred:

Local:

```text
existing authenticated gh session
```

Actions:

```text
GITHUB_TOKEN
```

PAT:

```text
fallback only
```

Never store credentials in repository files.

---

# 23. Branch Rules After Adoption

Normal feature/fix:

```text
staging
  ↓
one local branch
  ↓
local implementation
  ↓
targeted verification
  ↓
local acceptance
  ↓
push only when ready
  ↓
one PR → staging
  ↓
merge
  ↓
branch auto-delete
```

Avoid:

- branch-per-microtask,
- remote branch before useful work exists,
- stale branch accumulation,
- worktree-per-task.

---

# 24. Worktree Rule

Normal serial development uses the primary checkout.

Use worktrees only when:

- truly concurrent independent writers are required,
- touch surfaces are disjoint,
- concurrency provides real value.

Historical worktrees must be reconciled during local hygiene.

---

# 25. Main Promotion Rule

## Normal

```text
validated staging → main
```

## Reconciliation

If history shape requires a main-based reconciliation commit, allow only:

```text
release/promotion-*
```

with proof:

- based on current main when required,
- exact tree identity with validated staging,
- valid staging smoke evidence,
- no unauthorized deployment workflow mutation.

## Emergency

Allow:

```text
hotfix/*
```

only with:

- HIGH_RISK,
- fresh full CI,
- explicit human approval,
- no reuse claim from staging,
- immediate reconciliation back into staging.

Reject generic `release/*` as a reusable escape route.

---

# 26. Branch Cleanup

After Local Qualification passes and Remote Qualification is approved:

1. enable GitHub `delete_branch_on_merge = true`,
2. perform one deliberate branch reconciliation pass,
3. delete only branches proven merged/superseded/archived,
4. preserve unique work until reconciled.

Do not create a scheduled destructive branch-deletion bot by default.

---

# 27. Movement 0 — Truth, Authority and Local Repository Hygiene

**Mode: LOCAL ONLY**

Goals:

1. establish one authority tree,
2. remove/mark conflicting active docs,
3. correct coverage ownership,
4. scope runtime AI governance,
5. create authority linter,
6. create live-state audit tooling,
7. reconcile local workflow-history artifacts,
8. reconcile existing worktrees,
9. classify legacy local branches,
10. reconcile duplicate/shadow clinical-chart work,
11. prepare branch-governance changes locally,
12. prepare branch-cleanup activation instructions,
13. prepare main-promotion tightening locally.

No GitHub settings changes.
No remote branch deletion.

## Movement 0 Gate

```text
one active workflow authority
no known active authority conflict
authority linter PASS
live-state audit PASS or explicit exceptions
duplicate/shadow work has disposition
worktree state understood
no source-of-truth ambiguity
Git bundle backup PASS
NO REMOTE WRITE
```

---

# 28. Movement 1 — Lean Orchestration With Manual Handoff

**Mode: LOCAL ONLY**

Create:

`dentix-orchestration`

No dependency on automatic `agy`.

Implement:

- NORMAL / HIGH_RISK,
- model roles,
- active-work preflight,
- task brief,
- allowed/forbidden paths,
- snapshot contract,
- rollback/failure contract,
- manual Antigravity handoff,
- Codex acceptance terminology,
- separate reviewer rule for HIGH_RISK.

Manual flow:

```text
Codex creates brief
→ user starts Antigravity
→ Antigravity edits local branch
→ targeted tests
→ Codex reviews git diff
```

## Gate

A normal local task works without:

- GitHub writes,
- extra issues,
- extra PRs,
- worktree ceremony,
- repeated broad tests,
- automatic transport.

Then create and verify an off-repo Git bundle.

---

# 28B. Pre-Movement-2 Corrective Gate — External Skill Provenance

**Status:** POST-MOVEMENT-1 CORRECTIVE QUALIFICATION (APPEND-ONLY)
**Gate Name:** `EXTERNAL_SKILL_PROVENANCE = PASS`

### 1. Rationale for this Corrective Gate
The initial Movement 1 completion report incorrectly treated the workflow as ready for Movement 2 without establishing external-skill provenance. The required external-skill provenance artifacts (`docs/engineering/EXTERNAL_SKILLS_LOCK.json`, `scripts/verify_external_skills.py`, and `backend/tests/test_external_skill_provenance.py`) were not implemented. External skills must never be introduced or executed in DENTIX without deterministic, immutable provenance qualification.

### 2. Canonical Upstream Reference
- **Repository:** `https://github.com/amElnagdy/delegate-skills.git`
- **Pinned Immutable Commit:** `b781ee2e23089630e2fbee1cfd6174afe4edeb76`
- **Declared Version:** `0.5.0`
- **License:** `MIT`

### 3. Covered External Skills
1. `delegate-setup` (upstream: `skills/delegate-setup`)
2. `agy-delegate` (upstream: `skills/agy-delegate`)
3. `codex-delegate` (upstream: `skills/codex-delegate`)

### 4. Verification Commands

#### A. Authoritative Full-Gate Verification Command
To establish complete provenance, both the lock manifest must be verified against the pinned upstream source checkout AND the installed skills must be verified against that validated manifest:
```bash
python scripts/verify_external_skills.py --source-root <local-checkout-at-pinned-commit>
```
Targeted automated test suite (offline fixtures):
```bash
python -m pytest backend/tests/test_external_skill_provenance.py -q
```

#### B. Installed-Only Diagnostic Command
To inspect installed skills without re-verifying against the upstream source checkout:
```bash
python scripts/verify_external_skills.py --diagnostic
```
*(Note: Omission of `--source-root` performs diagnostic inspection only, cannot emit `EXTERNAL_SKILL_PROVENANCE = PASS`, and exits with code 2 if installed skills match or 1 if mismatches are found).*

### 5. Pass/Fail Criteria
1. `docs/engineering/EXTERNAL_SKILLS_LOCK.json` exists, conforms to deterministic schema, contains valid `file_count == len(files)`, declared version `0.5.0`, license `MIT`, and strictly contains no machine-specific absolute paths, Windows drive paths, or path traversal elements.
2. Complete reference source tree at pinned commit `b781ee2e23089630e2fbee1cfd6174afe4edeb76` is verified via `git ls-tree -r --name-only` and `git cat-file -p` blobs, with zero unexpected, zero missing, and zero modified source files.
3. Installed skills file tree matches pinned commit `b781ee2e23089630e2fbee1cfd6174afe4edeb76` for all three skills.
4. Zero modified files, zero missing files, and zero unexpected files in installed skills (ignoring non-source artifacts: `.git`, `__pycache__`, `*.pyc`, and OS metadata).
5. Strict read-only verification: verifier never writes into, alters, or reinstalls skills.
6. Exit code 0 on full exact match; non-zero on any provenance failure or diagnostic-only run.

### 6. Movement 2 Blocking Prerequisite
Movement 2 MUST NOT begin unless `EXTERNAL_SKILL_PROVENANCE = PASS`.
Installed-tree comparison alone cannot establish provenance. If any provenance check fails, is unverified, or is run only in diagnostic mode, Movement 2 is strictly BLOCKED.

### 7. Historical Truth & Bundle Integrity
- The existing Movement 0 and Movement 1 recovery bundles (`DENTIX_V3_movement_0_final_*.bundle`, `DENTIX_V3_movement_1_*.bundle`) were created prior to this qualification and do not contain this fix.
- This is recorded as an append-only post-Movement-1 corrective qualification.
- Existing commit IDs (`d2f5a18b`, `dc0ba2fc`, `fbe1b784`, `ee9aafa4`) and bundle metadata are preserved unchanged.
- A requalified bundle may only be created after review and explicit user approval.

---

# 29. Movement 2 — Windows Delegate Transport Proof

**Mode: LOCAL ONLY**

**Prerequisite Gate:** `EXTERNAL_SKILL_PROVENANCE = PASS` (Movement 2 MUST NOT begin unless the provenance gate passes).

Initial:

```text
AUTOMATIC_AGY_DELEGATION = OFF
```

Use already installed:

- `delegate-setup`
- `agy-delegate`
- `codex-delegate`

Do not commit runtime config as authority before proof.

Test:

1. runtime discovery,
2. auth,
3. shell behavior,
4. explicit `codex.cmd`,
5. `agy` read-only task,
6. zero-write proof,
7. tiny write task,
8. timeout,
9. non-zero exit,
10. forbidden-path violation,
11. rollback/preservation,
12. structured result,
13. Codex diff inspection.

Do not change PowerShell ExecutionPolicy merely to pass.

## Gate

If successful:

```text
AUTOMATIC_AGY_DELEGATION = LOCALLY_PROVEN
```

If not:

```text
MANUAL HANDOFF REMAINS SUPPORTED
```

Then create/verify off-repo Git bundle.

---

# 30. Movement 3A — Local Pilot Qualification

**Mode: LOCAL ONLY**

These prove local implementation mechanics only.

They do not claim GitHub behavior is proven.

## Pilot A — NORMAL Local

Prove:

- Codex planning,
- active-work guard,
- Antigravity implementation,
- targeted tests,
- Codex acceptance review,
- one coherent local branch,
- rollback contract,
- no unnecessary test repetition.

No push.

## Pilot B — HIGH_RISK Local

Use a controlled high-risk test surface.

Prove:

- Codex Leader planning,
- Codex sensitive-core authoring,
- Antigravity only in allowed adjacent scope,
- risk-specific local verification,
- separate read-only reviewer,
- Codex final acceptance.

No push.

## Gate

```text
NORMAL local pilot PASS
HIGH_RISK local pilot PASS
failure/rollback PASS
duplicate-work guard PASS
targeted verification PASS
model-role boundaries PASS
no second workflow introduced
Git bundle backup PASS
NO REMOTE WRITE
```

---

# 31. LOCAL_ACCEPTANCE_GATE

No GitHub write before all of these pass:

```text
Preservation Pass PASS
Git integrity PASS
valuable local work preserved
Movement 0 PASS
Movement 1 PASS
Movement 2 resolved
Movement 3A NORMAL PASS
Movement 3A HIGH_RISK PASS
authority linter PASS
live-state audit PASS / accepted exceptions
one workflow only
11 native skills consistent
no stale active workflow authority
rollback/failure behavior proven
duplicate-work guard proven
targeted-test strategy proven
final local forensic review PASS
second local double-check PASS
latest Git bundle verified
latest backup copied outside repo/device
```

Not included here because they require real GitHub activity:

- end-to-end CI classifier proof,
- branch deletion after merge,
- live PR behavior,
- no-polling behavior around live CI.

---

# 32. Remote Qualification — Explicit User Approval Required

Transition:

```text
LOCAL_ACCEPTANCE = PASS
        ↓
STOP
        ↓
USER APPROVAL
        ↓
REMOTE QUALIFICATION
```

No automatic continuation.

---

# 33. Remote Qualification Activation

Before remote pilots:

1. verify no unexpected remote drift,
2. enable GitHub `delete_branch_on_merge = true`,
3. do not clean historical remote branches yet unless explicitly approved,
4. preserve the current five-workflow GitHub Actions normalization,
5. do not publish the whole Workflow V3 integration yet.

---

# 34. Remote Pilot 1 — NORMAL

Use one tiny coherent NORMAL task.

```text
local implementation complete
→ push one short-lived branch
→ one PR → staging
→ AI stops
```

Prove:

1. one PR only,
2. classifier selects expected selective CI,
3. no AI polling,
4. later explicit invocation reads state once,
5. merge works,
6. GitHub auto-deletes the head branch.

Do not combine V3 docs/governance with this pilot.

## Gate

```text
PR mechanics PASS
selective CI PASS
no polling PASS
merge PASS
auto-delete PASS
```

---

# 35. Remote Pilot 2 — HIGH_RISK

Use one controlled, auditable HIGH_RISK task.

```text
Codex sensitive writer
+ allowed Antigravity adjacent work
→ separate reviewer
→ local verification
→ push one branch
→ one PR
→ AI stops
```

Prove:

1. HIGH_RISK classifier path,
2. expected broad/full validation,
3. separate review evidence,
4. no polling,
5. merge and cleanup.

## Gate

```text
high-risk classification PASS
required validation PASS
review boundary PASS
no polling PASS
merge PASS
cleanup PASS
```

---

# 36. Final Workflow V3 Integration PR

Only after both Remote Qualification pilots pass.

Create one coherent integration branch containing finalized workflow-system changes:

- `DEVELOPMENT_WORKFLOW.md`
- `AGENTS.md`
- `.agents/README.md`
- new `dentix-orchestration`
- native skill consistency fixes
- authority cleanup
- `AI_AGENT_STACK.md`
- `AI_GOVERNANCE_RULES.md` clarification
- authority linter
- live-state audit tooling
- PR/Issue template updates if still needed
- branch-governance tightening
- archive moves / historical headers

No unrelated product implementation.

---

# 37. Final Remote Hygiene

After the V3 integration PR merges:

1. verify active authority on `staging`,
2. verify exactly 11 native skills,
3. verify no conflicting active docs,
4. reconcile stale remote branches,
5. delete only branches with safe disposition,
6. preserve unique historical work before deletion,
7. verify no competing workflow files remain active,
8. verify the five-workflow Actions normalization remains intact.

Production promotion remains separate unless explicitly approved.

---

# 38. No AI CI Polling

Hard rule:

```text
PR created / CI triggered
→ AI reports reference
→ AI stops
```

Forbidden:

- repeated Actions refresh,
- status-query loops,
- "wait until green" loops,
- deployment polling.

Later:

```text
user invokes again
→ read current state once
→ act
```

Remote Qualification explicitly proves this behavior.

---

# 39. Testing Strategy

During implementation:

```text
smallest targeted tests only
```

Before PR:

```text
relevant subsystem confidence checks only
```

PR:

```text
GitHub classifier is authoritative
```

After staging merge:

```text
do not repeat the full PR matrix
use deployment + staging smoke
```

staging → main:

```text
reuse validated staging evidence when provenance passes
```

hotfix:

```text
fresh full CI
```

---

# 40. Explicitly Rejected Mechanics

Do not reintroduce:

- two active workflows,
- V2 state-machine ceremony,
- FAST as a separate workflow,
- micro-ticket issue spam,
- micro-PRs,
- worktree-per-task,
- remote branch-per-subtask,
- AI CI polling,
- repeated full local suites,
- repeated full CI for same revision,
- all-skills preloading,
- 183+ skill stack,
- CodeRabbit dependency,
- Antigravity Kit dependency,
- ECC as DENTIX authority,
- babysit-pr loop,
- debate-review as default,
- mandatory TDD for trivial work,
- mandatory spec generation for tiny clear fixes,
- unproven `agy` assumptions,
- generic `release/* → main`,
- destructive rollback of unknown local work.

---

# 41. Final Target Workflow After Adoption

## NORMAL

```text
USER
  ↓
CODEX LEADER
plan / scope / active-work check
  ↓
ANTIGRAVITY
implementation
  ↓
targeted local tests
  ↓
CODEX LEADER
acceptance of actual git diff
  ↓
push one ready branch
  ↓
one PR → staging
  ↓
classified CI
  ↓
AI STOPS
  ↓
merge
  ↓
branch auto-delete
  ↓
staging deploy + smoke
```

## HIGH_RISK

```text
USER
  ↓
CODEX LEADER
plan / scope / active-work check
  ↓
CODEX HIGH-RISK WRITER
sensitive core
  +
ANTIGRAVITY
allowed adjacent work
  ↓
targeted + risk-specific verification
  ↓
SEPARATE READ-ONLY REVIEWER
  ↓
CODEX LEADER ACCEPTANCE
  ↓
one PR
  ↓
high-risk/full CI
  ↓
AI STOPS
```

---

# 42. Completion Criteria

V3 is complete only when:

- exactly one active workflow exists,
- local-first is explicit,
- preservation/backup policy is active,
- NORMAL defaults to Antigravity after proof,
- Codex remains leader/control plane,
- HIGH_RISK sensitive core uses Codex writer,
- NORMAL acceptance is not mislabeled independent review,
- HIGH_RISK uses a separate reviewer,
- delegate failure cannot contaminate unknown user work,
- automatic delegation can be disabled without breaking workflow,
- active-work guard prevents duplicate/shadow implementation,
- one coherent task normally produces one branch and one PR,
- merged branches disappear automatically,
- worktrees are exceptional,
- targeted tests are standard,
- CI classifier remains authoritative,
- no duplicated broad-validation loop exists,
- zero AI polling,
- five-workflow GitHub Actions normalization remains intact,
- generic `release/*` cannot bypass production policy,
- historical docs cannot override active rules,
- dynamic values have one owner,
- authority linter passes,
- live-state audit is available,
- both remote qualification pilots pass,
- final V3 integration PR passes,
- final forensic review finds no second workflow.

---

# 43. Execution Order

```text
PRESERVATION PASS
        ↓
LOCAL ONLY
Movement 0 — Truth / Authority / Repo Hygiene
        ↓
backup bundle
        ↓
Movement 1 — Lean Orchestration / Manual Handoff
        ↓
backup bundle
        ↓
Movement 2 — Windows Delegate Proof
        ↓
backup bundle
        ↓
Movement 3A — NORMAL + HIGH_RISK Local Pilots
        ↓
backup bundle
        ↓
FINAL LOCAL FORENSIC REVIEW
        ↓
DOUBLE CHECK
        ↓
LOCAL_ACCEPTANCE = PASS
        ↓
STOP
        ↓
EXPLICIT USER APPROVAL
        ↓
REMOTE QUALIFICATION
Pilot 1 NORMAL
        ↓
Pilot 2 HIGH_RISK
        ↓
FINAL WORKFLOW V3 INTEGRATION PR
        ↓
REMOTE HYGIENE
        ↓
FINAL FORENSIC CLOSEOUT
```

---

# 44. Immediate Next Action

Do not start Movement 0 yet.

Immediate next action:

```text
LOCAL-ONLY PRESERVATION PASS
```

Requirements:

- external backup,
- SHA256 manifest,
- broken-ref quarantine,
- local preservation commit,
- external Git bundle,
- no push,
- no PR,
- no remote branch creation,
- no V3 implementation.

After Preservation returns `PASS`, begin Movement 0 locally.

---

# 45. Final Design Principle

The workflow must reduce decisions, not multiply them.

Target:

```text
one workflow
one local task
one clear owner
one implementation route
one review boundary
one PR
one CI decision
one release path
```

Never again:

```text
workflow on top of workflow
skill on top of skill
ticket on top of ticket
branch on top of branch
review on top of review
test on top of test
```

This is the final operating principle of DENTIX Workflow V3.
