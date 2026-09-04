# DENTIX AI DEVELOPMENT WORKFLOW V2
## Final Micro-Task Implementation Plan
**Status:** Proposed / Ready for controlled implementation  
**Repository:** `Dentix-hub/dentix`  
**Primary target branch:** `staging` through a scoped implementation branch  
**Production promotion:** `staging -> main` only after validation  
**Prepared:** 2026-08-29

---

# 0. Executive Decision

DENTIX will **not replace** its native agent stack.

The existing repository governance remains authoritative:

1. Explicit current user requirement or approved plan.
2. Security, tenant isolation, RBAC, data integrity, and privacy.
3. `PROJECT_STANDARDS.md`.
4. Root `AGENTS.md`.
5. Task-specific repository documentation.
6. Native `.agents/skills/`.
7. General engineering conventions.

The new workflow adds a missing orchestration layer:

```text
PRODUCT DECISION
      |
      v
DISCOVERY / GRILL
      |
      v
DENTIX SPEC
      |
      v
ATOMIC GITHUB ISSUES
      |
      v
DEPENDENCY + PARALLEL-SAFETY GRAPH
      |
      +-------------------+
      |                   |
      v                   v
ISOLATED WORKTREE A   ISOLATED WORKTREE B
IMPLEMENTER           IMPLEMENTER
      |                   |
      +---------+---------+
                |
                v
        ORCHESTRATOR REVIEW
                |
                v
        DENTIX TEST / CI GATES
                |
                v
         PR -> `staging`
                |
                v
        STAGING VALIDATION
                |
                v
         `staging` -> `main`
```

The workflow deliberately separates:

- **Orchestration / architecture / acceptance authority**
- **Implementation**
- **Independent review**
- **CI / release authority**

The primary objective is **reliable completion with traceable evidence**, not raw issue throughput.

---

# 1. Why This Change Exists

The current DENTIX stack already has strong native discipline:

- `AGENTS.md`
- `PROJECT_STANDARDS.md`
- `dentix-plan-execution`
- `dentix-backend-fastapi`
- `dentix-frontend-react`
- `dentix-mobile-flutter`
- `dentix-security-tenancy-rbac`
- `dentix-database-migrations`
- `dentix-testing-verification`
- `dentix-systematic-debugging`
- `dentix-code-review`
- `dentix-performance`

The missing layer is the reliable transformation of a large approved goal into:

- small independent execution units,
- explicit dependencies,
- parallel-safe work,
- isolated implementer sessions,
- reviewable diffs,
- bounded context,
- issue-level completion evidence.

This plan fills that gap without importing a second competing engineering rulebook.

---

# 2. External Workflow Concepts Adopted

The workflow adopts these concepts from the reviewed AI workflow:

1. **Think before coding.**
2. **Convert discussion into an explicit spec.**
3. **Convert large plans/specs into atomic tickets.**
4. **Keep a strong orchestrator separate from implementers.**
5. **Delegate bounded work into isolated sessions/worktrees.**
6. **Parallelize only tasks proven to be independent.**
7. **Review implementer output independently.**
8. **Use the repository test/CI gates as final truth.**

The workflow does **not** adopt the external stack wholesale.

---

# 3. Explicit Non-Goals

The implementation MUST NOT:

- replace `AGENTS.md`,
- replace `PROJECT_STANDARDS.md`,
- weaken any tenant/RBAC/data-integrity rule,
- replace the 10 existing DENTIX native skills,
- bulk-install the entire Matt Pocock skills repository into `.agents/skills/`,
- restore ECC / Everything Claude Code,
- restore CodeRabbit,
- create duplicated skill authorities,
- permit agents to merge directly to `main`,
- allow implementer self-reports to count as verification,
- run security/RLS/database/finance work in parallel merely for speed,
- use uncontrolled shared-working-tree multi-agent editing,
- let a delegate relay commit or merge on behalf of the reviewer,
- introduce production application dependencies for agent orchestration,
- change application API/database/business contracts as part of this workflow migration.

---

# 4. Target Operating Model

## 4.1 Roles

### A. Orchestrator
Default preferred seat: **Codex reasoning session**.

Responsibilities:

- inspect repository truth,
- clarify requirements,
- create or approve the implementation spec,
- decompose work,
- classify dependencies,
- choose parallel-safe groups,
- construct self-contained delegate briefs,
- review every returned diff,
- rerun DENTIX verification,
- create/inspect PRs,
- decide readiness.

The orchestrator MUST NOT treat an implementer final message as evidence of completion.

### B. Implementer
Preferred bounded implementation runtime: **Antigravity (`agy`)** when locally available and authenticated.

Alternative: a **separate Codex CLI session**, not the orchestrator context.

Responsibilities:

- execute exactly one bounded ticket or one explicitly approved ticket batch,
- obey DENTIX repository instructions,
- modify only necessary files,
- run targeted verification,
- return structured results,
- never claim broader completion than its ticket.

### C. Independent Reviewer
A distinct read-only model/session.

Responsibilities:

- inspect requirements vs diff,
- inspect DENTIX-specific security and architecture,
- challenge findings where debate review is enabled,
- never silently modify code while acting as reviewer.

### D. Repository Gates
The existing DENTIX CI and branch governance remain final technical authority.

---

# 5. Required Branch and Worktree Model

## 5.1 Protected branch flow

Normal feature/fix flow:

```text
scoped branch -> staging -> main
```

Examples:

```text
feat/dtx-341-odontogram-root-rendering
fix/dtx-342-patient-cache-invalidation
test/dtx-343-finance-regression-coverage
refactor/dtx-344-appointment-query-seam
chore/dtx-345-agent-orchestration-v2
```

Production promotion:

```text
staging -> main
```

Emergency exceptions remain governed by existing repository branch rules.

## 5.2 Worktree isolation

Every parallel write-capable delegate MUST operate in its own worktree or equivalent isolated checkout.

Forbidden:

```text
Agent A edits C:\...\DENTIX
Agent B edits the same C:\...\DENTIX
Agent C edits the same C:\...\DENTIX
```

Required:

```text
DENTIX/
DENTIX-wt-dtx-341/
DENTIX-wt-dtx-342/
DENTIX-wt-dtx-343/
```

The orchestrator owns integration.

---

# 6. Ticket Contract

Every AI-executable DENTIX issue MUST contain the following fields.

## 6.1 Required fields

```text
Title
Source / parent spec
Problem
Objective
Scope
Explicit non-goals
Dependencies
Parallel-safety classification
Expected touch surface
Acceptance criteria
Required DENTIX skills
Risk classification
Verification commands / verification class
Completion evidence
```

## 6.2 Risk classifications

At minimum:

- `LOW`
- `NORMAL`
- `CLINICAL`
- `FINANCE`
- `AUTH_RBAC`
- `TENANCY_RLS`
- `DATABASE_MIGRATION`
- `DEPLOYMENT`
- `SECURITY`

A ticket can have multiple risk tags.

## 6.3 Parallel classifications

Each ticket MUST be explicitly one of:

- `PARALLEL_SAFE`
- `PARALLEL_AFTER:<ticket>`
- `SERIAL_ONLY`

No ticket is implicitly parallel-safe.

---

# 7. Parallelization Rules

## 7.1 Usually parallel-safe

Examples:

- unrelated frontend components,
- independent documentation,
- isolated test additions,
- backend endpoint work in a separate domain from unrelated UI work,
- separate modules with no shared contract change,
- static assets independent of active feature code.

## 7.2 Usually serial-only

The following default to `SERIAL_ONLY` unless the orchestrator proves otherwise:

- authentication,
- RBAC,
- tenant isolation,
- RLS,
- financial calculations,
- migrations touching related tables,
- shared API contract changes,
- shared central state refactors,
- the same component/file,
- the same service/CRUD seam,
- branch/deployment workflow changes,
- changes whose tests depend on an unsettled contract.

## 7.3 Maximum initial concurrency

Pilot maximum:

```text
2 simultaneous write-capable delegates
```

After successful validation:

```text
3 simultaneous delegates
```

Do not increase concurrency merely because more CLIs are available.

---

# 8. Deliverables Created by This Migration

Expected repository-level deliverables:

```text
docs/engineering/DENTIX_AI_DEVELOPMENT_WORKFLOW_V2.md
.agents/skills/dentix-orchestration/SKILL.md
.github/ISSUE_TEMPLATE/dentix-agent-task.yml
.github/ISSUE_TEMPLATE/config.yml
.github/pull_request_template.md
.delegate/config.json                 # only after local discovery + explicit approval
```

Expected existing files updated:

```text
AGENTS.md                              # minimal orchestration reference only
.agents/README.md                      # register new native orchestration skill
```

Optional Phase-2 review integration:

```text
External/global review-skills installation
review-main / review-debate delegate lanes
```

No application-runtime file should change merely to enable this workflow.

---

# 9. Implementation Program

# PHASE DWF-00 — Baseline Freeze and Forensic Preflight

## Objective
Prove the exact starting state before making agent-workflow changes.

### DWF-00.01
Create implementation branch from current `staging`:

```text
chore/dtx-ai-development-workflow-v2
```

### DWF-00.02
Record:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/staging
git rev-parse origin/main
```

### DWF-00.03
Confirm working tree is understood.

Do NOT discard unrelated local user work.

### DWF-00.04
Read in full:

```text
AGENTS.md
PROJECT_STANDARDS.md
.agents/README.md
.agents/skills/dentix-plan-execution/SKILL.md
.agents/skills/dentix-code-review/SKILL.md
.agents/skills/dentix-testing-verification/SKILL.md
.github/workflows/branch-governance.yml
.github/workflows/ci.yml
```

### DWF-00.05
Search for forbidden legacy stack remnants:

```text
CodeRabbit
coderabbit
Everything Claude Code
ECC
delegate-skills
review-skills
mattpocock/skills
```

### DWF-00.06
Do not remove unrelated historical documentation solely because a search term appears in prose.

Classify every match:

```text
ACTIVE_RUNTIME
ACTIVE_REPO_CONFIG
HISTORICAL_DOC
TEST_FIXTURE
FALSE_POSITIVE
```

### DWF-00.07
Capture baseline CI-required commands from the current workflows.

### Exit Gate DWF-00
PASS only when:

- base branch is known,
- no user work was lost,
- source-of-truth files were read,
- active legacy-agent state is known,
- current CI gates are documented.

---

# PHASE DWF-01 — Write the DENTIX Orchestration Contract

## Objective
Define workflow authority before installing external orchestration tooling.

### DWF-01.01
Create:

```text
docs/engineering/DENTIX_AI_DEVELOPMENT_WORKFLOW_V2.md
```

### DWF-01.02
Document the role model:

```text
User/Product Authority
Orchestrator
Implementer
Reviewer
CI
Release
```

### DWF-01.03
Document authority precedence.

It MUST match current DENTIX precedence.

### DWF-01.04
Document ticket lifecycle:

```text
DRAFT
-> READY
-> IN_PROGRESS
-> IMPLEMENTED
-> REVIEW_REQUIRED
-> VERIFIED
-> CLOSED
```

### DWF-01.05
Document forbidden state transition:

```text
IMPLEMENTED -> CLOSED
```

without independent verification.

### DWF-01.06
Document worktree isolation.

### DWF-01.07
Document dependency graph rules.

### DWF-01.08
Document parallel classifications.

### DWF-01.09
Document risk classifications.

### DWF-01.10
Document that external tools are transport/orchestration helpers, not DENTIX policy authorities.

### Exit Gate DWF-01
A reviewer must be able to answer from the document alone:

- Who may plan?
- Who may edit?
- Who may review?
- Who verifies?
- What makes a ticket complete?
- When is parallel work forbidden?
- What wins if an external skill conflicts with DENTIX?

---

# PHASE DWF-02 — Add One Native `dentix-orchestration` Skill

## Objective
Fill the genuinely missing native responsibility without duplicating existing skills.

### DWF-02.01
Create:

```text
.agents/skills/dentix-orchestration/SKILL.md
```

### DWF-02.02
Skill purpose:

> Orchestrate approved DENTIX work across atomic tickets, dependencies, isolated delegates, worktrees, independent review, and repository verification without replacing domain-specific DENTIX skills.

### DWF-02.03
The skill MUST delegate domain policy to existing skills.

Examples:

```text
backend task -> dentix-backend-fastapi
frontend task -> dentix-frontend-react
security task -> dentix-security-tenancy-rbac
migration task -> dentix-database-migrations
verification -> dentix-testing-verification
review -> dentix-code-review
plan execution -> dentix-plan-execution
```

### DWF-02.04
Do NOT duplicate their rule bodies.

### DWF-02.05
Define required orchestration algorithm:

1. Read source plan/spec.
2. Build ticket ledger.
3. Resolve dependencies.
4. Mark risk.
5. Mark parallel safety.
6. Build execution waves.
7. Create isolated brief per ticket.
8. Dispatch only ready tickets.
9. Review each returned diff.
10. Re-run repository verification.
11. Integrate only verified work.
12. Recalculate remaining graph.
13. Report `DONE`, `PARTIAL`, or `BLOCKED`.

### DWF-02.06
Define execution wave example:

```text
Wave 0: foundational contract
Wave 1: A + B in parallel
Wave 2: C after A
Wave 3: D after A+B+C
```

### DWF-02.07
Define hard rule:

> Same-file or same-contract uncertainty collapses parallel work into serial work.

### DWF-02.08
Define implementer evidence as untrusted until reviewer verification.

### DWF-02.09
Define no automatic merge.

### DWF-02.10
Update `.agents/README.md`.

Change:

```text
10 Native Skills
```

to:

```text
11 Native Skills
```

and add `dentix-orchestration`.

### DWF-02.11
Update `AGENTS.md` minimally.

Add only a concise rule such as:

> For multi-ticket or delegated parallel work, apply `dentix-orchestration` in addition to `dentix-plan-execution`. Parallel execution must use isolated worktrees and explicit dependency/parallel-safety classification.

Do not rewrite the rest of `AGENTS.md`.

### Exit Gate DWF-02
No existing skill responsibility is duplicated.

---

# PHASE DWF-03 — Introduce GitHub Issue Execution Contract

## Objective
Make GitHub Issues the execution source while master plans remain strategic sources.

### DWF-03.01
Create directory:

```text
.github/ISSUE_TEMPLATE/
```

### DWF-03.02
Create:

```text
.github/ISSUE_TEMPLATE/dentix-agent-task.yml
```

### DWF-03.03
Required Issue Form fields:

- Problem
- Objective
- Source spec / plan
- Scope
- Non-goals
- Dependencies
- Parallel classification
- Expected touch surface
- Acceptance criteria
- Risk
- Verification
- Completion evidence

### DWF-03.04
Acceptance criteria must be checklist-based.

### DWF-03.05
"Expected touch surface" is a review boundary, not permission to ignore necessary tests.

If an implementer must touch an unlisted production file, it must stop or explicitly report scope expansion.

### DWF-03.06
Create:

```text
.github/ISSUE_TEMPLATE/config.yml
```

Disable blank issues only if that matches project preference; otherwise leave blank issues enabled.

### DWF-03.07
Define recommended labels.

Workflow labels:

```text
agent:ready
agent:blocked
agent:in-progress
agent:review
agent:verified
```

Parallel labels:

```text
parallel:safe
parallel:serial
```

Risk labels:

```text
risk:clinical
risk:finance
risk:auth-rbac
risk:tenancy-rls
risk:database
risk:deployment
risk:security
```

### DWF-03.08
Do not assume labels exist.

Use `gh label list` or GitHub API to inspect first.

### DWF-03.09
Create only missing labels.

Do not rename unrelated existing labels.

### DWF-03.10
Define ticket branch mapping:

```text
Issue #341 feature -> feat/dtx-341-...
Issue #342 fix     -> fix/dtx-342-...
Issue #343 tests   -> test/dtx-343-...
```

### Exit Gate DWF-03
Create one dry-run example issue body locally and verify that an implementer can understand it without access to the orchestrator chat.

---

# PHASE DWF-04 — Add Pull Request Evidence Contract

## Objective
Force PRs to show ticket compliance and real verification.

### DWF-04.01
Create:

```text
.github/pull_request_template.md
```

### DWF-04.02
Template sections:

```text
Source Issue
Scope
Changes
Non-Goals Confirmed
Risk
DENTIX Skills Applied
Verification
Acceptance Criteria
Security / Tenancy / RBAC Impact
Database / Migration Impact
Screenshots (when UI)
Known Limitations
```

### DWF-04.03
Verification section must request exact commands/results.

### DWF-04.04
Security section must not permit "N/A" without consideration.

Suggested choices:

```text
No relevant change
Reviewed - no impact
Relevant change - details below
```

### DWF-04.05
Do not make the template so large that it becomes ignored.

### Exit Gate DWF-04
A PR should be auditable without reading the full agent conversation.

---

# PHASE DWF-05 — Install Delegate Transport Safely

## Objective
Add delegation without turning external skills into repository authority.

## Critical decision
Do NOT bulk-install all external skills into `.agents/skills/`.

Preferred installation strategy:

```text
External skills: global user tool installation
Project policy: repository-owned DENTIX files
Project lane map: .delegate/config.json
```

### DWF-05.01
Verify prerequisites:

```bash
node --version
git --version
```

Require Node 18+.

### DWF-05.02
Discover current CLIs.

At minimum investigate:

```text
codex
agy
```

### DWF-05.03
Verify authentication status.

Never store credentials in repository config.

### DWF-05.04
Inspect external package before installation.

### DWF-05.05
Install only required delegate skills.

Preferred minimum:

```text
delegate-setup
agy-delegate
codex-delegate
```

Do not install unrelated implementers merely because the package supports them.

### DWF-05.06
Prefer global skill installation where supported.

Reason:

- keeps DENTIX `.agents/skills/` native,
- avoids duplicated engineering rulebooks,
- allows external package updates independently,
- preserves repository policy boundaries.

### DWF-05.07
Do not run a write-capable delegate yet.

### Exit Gate DWF-05
PASS when:

- delegate tooling is installed,
- `codex` / `agy` availability is known,
- no external skill was copied into DENTIX native skill catalog unintentionally,
- repository diff contains no unexpected external package payload.

---

# PHASE DWF-06 — Configure DENTIX Delegate Fleet

## Objective
Create a small repository-specific lane map.

The current external fleet schema uses:

```text
<git-root>/.delegate/config.json
```

Project config is intentionally trust-bound to explicit local approval.

### DWF-06.01
Run delegate discovery.

### DWF-06.02
Do not invent model identifiers.

### DWF-06.03
Do not put model/effort dials in config unless verified and intentionally chosen.

### DWF-06.04
Initial target lane roles:

```text
feature
ui
tests
complex
```

Maximum initial lanes: 4.

### DWF-06.05
Preferred mapping policy, subject to local discovery:

```text
feature -> agy
ui      -> agy
tests   -> codex or agy based on available quotas/reliability
complex -> strongest explicitly approved implementer
```

### DWF-06.06
The orchestrator seat is NOT a lane.

If Codex is the orchestrator, a `codex` lane means a separate Codex CLI execution context.

### DWF-06.07
Create `.delegate/config.json` only after reviewing the exact proposed JSON.

### DWF-06.08
No secret fields.

### DWF-06.09
Validate config using delegate tooling.

### DWF-06.10
Re-load effective lane map and confirm project trust.

### DWF-06.11
Commit `.delegate/config.json` only if the team wants the intended lane structure versioned.

Authentication and approval hashes remain local metadata, not repository data.

### Exit Gate DWF-06
Every configured lane resolves cleanly or the phase is `BLOCKED`.

---

# PHASE DWF-07 — Read-Only Delegate Smoke Test

## Objective
Prove relay mechanics before allowing edits.

### DWF-07.01
Choose a simple repository question.

Example:

> Inspect the frontend architecture and identify the current canonical shared button component. Do not modify files.

### DWF-07.02
Run Antigravity delegate in read-only/plan mode.

### DWF-07.03
Verify:

- no tracked files changed,
- no untracked repo files unexpectedly created,
- result contains useful structured output,
- relay returns an understandable exit status.

### DWF-07.04
Run a separate Codex delegate read-only smoke if the Codex lane is configured.

### DWF-07.05
After every smoke:

```bash
git status --short
git diff --stat
```

### Exit Gate DWF-07
Zero Git-visible writes from read-only smoke tests.

Any write violation blocks write-capable rollout until understood.

---

# PHASE DWF-08 — Single-Ticket Write Pilot

## Objective
Prove one complete delegated lifecycle.

### Pilot selection rules

Choose a ticket that is:

- low or normal risk,
- no migration,
- no RLS,
- no auth/RBAC,
- no finance calculation,
- no deployment pipeline,
- no production emergency,
- objectively testable,
- small enough for one session.

### DWF-08.01
Create one real GitHub Issue using the new contract.

### DWF-08.02
Mark it `agent:ready`.

### DWF-08.03
Create dedicated branch.

### DWF-08.04
Create dedicated worktree.

### DWF-08.05
Construct self-contained delegate brief.

Required brief contents:

```text
Repository
Issue
Base SHA
Objective
Scope
Non-goals
Relevant DENTIX source-of-truth files
Required native skills
Expected touch surface
Acceptance criteria
Verification expectations
Forbidden actions
Final report format
```

### DWF-08.06
Dispatch one implementer.

### DWF-08.07
Implementer may run targeted tests.

### DWF-08.08
After return, orchestrator independently inspects:

```bash
git status
git diff
git diff --check
```

### DWF-08.09
Orchestrator checks ticket acceptance criteria one by one.

### DWF-08.10
Run `dentix-code-review`.

### DWF-08.11
Run relevant targeted tests independently.

### DWF-08.12
Run required broad verification for the touched subsystem.

### DWF-08.13
If failures exist:

- classify introduced vs baseline,
- return ticket to implementation if introduced,
- never close as verified.

### DWF-08.14
Create PR to `staging`.

### DWF-08.15
Wait for repository checks through normal CI flow.

### DWF-08.16
Only after green review/gates mark issue `agent:verified`.

### Exit Gate DWF-08
A full delegated ticket reaches verified PR state with no bypassed DENTIX rules.

---

# PHASE DWF-09 — Two-Ticket Parallel Pilot

## Objective
Prove dependency-aware concurrency.

### DWF-09.01
Choose two `PARALLEL_SAFE` tickets.

### DWF-09.02
Prove they do not share:

- production file touch surface,
- schema contract,
- API contract dependency,
- migration lineage,
- central state mutation,
- security boundary.

### DWF-09.03
Create two branches.

### DWF-09.04
Create two worktrees.

### DWF-09.05
Dispatch at most two write-capable delegates.

### DWF-09.06
No delegate can see or edit the other delegate's worktree.

### DWF-09.07
Review result A independently.

### DWF-09.08
Review result B independently.

### DWF-09.09
Run ticket-level targeted gates separately.

### DWF-09.10
Open separate PRs to `staging`.

### DWF-09.11
Do not combine them merely to reduce PR count.

### DWF-09.12
After first merge, refresh second branch from current `staging` if required and rerun affected verification.

### Exit Gate DWF-09
Both tickets integrate without conflict, hidden dependency, or verification regression.

---

# PHASE DWF-10 — Large Plan -> Ticket Graph Pilot

## Objective
Replace "one agent executes a giant plan" with a graph.

### DWF-10.01
Select one approved multi-phase DENTIX plan.

Do not select an emergency production remediation as the first graph pilot.

### DWF-10.02
Read the entire source plan.

### DWF-10.03
Extract every:

- phase,
- task ID,
- acceptance criterion,
- dependency,
- non-goal,
- validation command,
- user approval gate.

### DWF-10.04
Build graph before creating issues.

### DWF-10.05
No issue should contain an uncontrolled multi-day mega-phase.

### DWF-10.06
Ticket sizing rule:

A ticket should usually have:

```text
one coherent objective
one primary seam/module
clear observable acceptance
bounded verification
```

### DWF-10.07
Avoid pathological micro-ticketing.

Do not make one ticket per line/file if the work cannot independently pass acceptance.

### DWF-10.08
Map plan requirements to tickets in a coverage table.

Example:

| Plan ID | Ticket | Status |
| --- | --- | --- |
| P1.1 | #401 | mapped |
| P1.2 | #402 | mapped |
| P1.3 | #402 | mapped |
| P2.1 | #403 | mapped |

### DWF-10.09
Every plan requirement must map to at least one ticket or explicit `N/A` justification.

### DWF-10.10
Run ticket graph in dependency waves.

### DWF-10.11
After each wave, perform anti-skip reconciliation against the original plan.

### Exit Gate DWF-10
No original approved requirement disappears during ticket decomposition.

---

# PHASE DWF-11 — Optional Debate Review Integration

## Objective
Add model diversity after delegation is stable.

This phase is intentionally later.

### DWF-11.01
Do not begin until DWF-08 and DWF-09 pass.

### DWF-11.02
Inspect current `review-skills` release/README/SKILL before install.

The external repository is fast-moving; do not rely on stale assumptions.

### DWF-11.03
Install only:

```text
debate-review
babysit-pr
```

plus required delegate support if not already present.

### DWF-11.04
Add two read-only lanes:

```text
review-main
review-debate
```

### DWF-11.05
Use different implementers/models where possible.

### DWF-11.06
Never use a write-capable review lane.

### DWF-11.07
DENTIX review policy remains:

```text
.agents/skills/dentix-code-review/SKILL.md
```

External debate tooling is the review engine, not policy source.

### DWF-11.08
Map review severities carefully.

Do not silently replace DENTIX `CRITICAL/HIGH/MEDIUM/LOW/NOTE` meaning with external P0/P1/P2 semantics.

If both are used, document the mapping.

### DWF-11.09
First test with local/dry-run review.

### DWF-11.10
Do not allow `babysit-pr` to merge.

### DWF-11.11
Every babysitter fix must pass normal DENTIX review and verification.

### Exit Gate DWF-11
Debate review improves review evidence without bypassing native policy.

---

# PHASE DWF-12 — Governance Hardening

## Objective
Turn the successful pilot into repeatable repository practice.

### DWF-12.01
Review pilot failures.

Classify:

```text
TOOLING
PROMPT/BRIEF
TICKET_SIZING
DEPENDENCY_CLASSIFICATION
IMPLEMENTER_QUALITY
TEST_GAP
REVIEW_GAP
REPO_GOVERNANCE
```

### DWF-12.02
Update only the smallest responsible layer.

Examples:

- bad ticket shape -> workflow doc/template,
- repeated orchestration miss -> orchestration skill,
- backend implementation miss -> backend skill only if recurring,
- test truth mismatch -> testing skill/CI,
- tool relay issue -> external tooling, not DENTIX architecture.

### DWF-12.03
Add no new native skill unless one existing skill cannot own the recurring problem.

### DWF-12.04
Do not encode model-brand assumptions into permanent DENTIX architecture.

Roles are permanent; model assignments are replaceable.

### DWF-12.05
Set initial concurrency cap to 3.

### DWF-12.06
Define high-risk serial policy in workflow documentation.

### DWF-12.07
Define emergency bypass:

Emergency work may skip delegation/parallelism, but MUST NOT skip security, review, tests, or branch governance.

### Exit Gate DWF-12
The workflow is documented enough that a new orchestrator can use it without this chat.

---

# PHASE DWF-13 — Final Verification

## DWF-13.01 Repository diff review

Verify no accidental application changes.

### DWF-13.02 Legacy stack scan

Confirm no active:

```text
CodeRabbit
ECC
Everything Claude Code
```

was reintroduced.

### DWF-13.03 Duplication scan

Confirm the external package was not vendored into `.agents/skills` unless explicitly intended.

### DWF-13.04 Native skill registry

Confirm `.agents/README.md` matches actual native skill directories.

### DWF-13.05 YAML validation

Validate GitHub Issue Form YAML.

### DWF-13.06 Markdown/template sanity

Review rendered issue and PR templates.

### DWF-13.07 Delegate config validation

Run external config validator.

### DWF-13.08 Read-only relay smoke

Re-run.

### DWF-13.09 Single ticket pilot evidence

Must exist.

### DWF-13.10 Parallel pilot evidence

Must exist.

### DWF-13.11 Run relevant repository CI checks for changed files.

Because this migration is primarily repository tooling/documentation, do not invent irrelevant application tests; follow current CI and changed-file policy.

### DWF-13.12 Final status

Only one:

```text
DONE
PARTIAL
BLOCKED
```

### DWF-13.13 Final completion report

Must include:

- branch,
- commits,
- files changed,
- tools installed,
- lanes configured,
- pilot tickets,
- exact verification run,
- unresolved limitations,
- rollback instructions.

---

# 10. Required Delegate Brief Template

Every implementation dispatch should use a structure similar to this:

```text
DENTIX DELEGATE BRIEF
=====================

Ticket:
#<number> <title>

Repository:
Dentix-hub/dentix

Base:
<branch + SHA>

Role:
You are the bounded IMPLEMENTER for this ticket.
You are not the product owner, orchestrator, merger, or release authority.

Read first:
1. AGENTS.md
2. PROJECT_STANDARDS.md
3. <relevant native DENTIX skill files>
4. The complete GitHub issue/spec

Objective:
<one concise objective>

Scope:
- ...
- ...

Explicit non-goals:
- ...
- ...

Dependencies:
- ...

Expected touch surface:
- ...

Risk:
<...>

Acceptance criteria:
- [ ] ...
- [ ] ...

Verification expected:
- ...

Hard constraints:
- Preserve tenant isolation.
- Preserve RBAC.
- Preserve API contracts unless explicitly authorized.
- Do not alter database schema unless explicitly authorized.
- Do not merge.
- Do not silently expand scope.
- Do not report DONE if any acceptance criterion is unmet.

Final report:
1. Status: DONE | PARTIAL | BLOCKED
2. Files changed
3. Acceptance criteria status
4. Tests/commands run with exit status
5. Known limitations
6. Any scope expansion or unexpected dependency
```

---

# 11. Orchestrator Review Checklist

For every returned delegate result:

```text
[ ] Correct worktree?
[ ] Correct ticket?
[ ] Base SHA understood?
[ ] Diff inspected?
[ ] Unexpected files?
[ ] Acceptance criteria checked individually?
[ ] DENTIX domain skill applied?
[ ] Tenant/RBAC impact checked?
[ ] API compatibility checked?
[ ] Database impact checked?
[ ] Financial/clinical impact checked?
[ ] Targeted tests independently rerun?
[ ] Broad required gates rerun?
[ ] Baseline failures separated?
[ ] PR targets staging?
[ ] No direct unauthorized main path?
[ ] Issue state updated only after evidence?
```

---

# 12. GitHub Issue Lifecycle

Recommended operational state:

```text
DRAFT
  |
  v
agent:ready
  |
  v
agent:in-progress
  |
  v
agent:review
  |
  +--> agent:blocked
  |
  v
agent:verified
  |
  v
CLOSED
```

`agent:verified` means independent verification has passed.

It does **not** mean the implementer said it passed.

---

# 13. High-Risk Safety Matrix

| Area | Parallel Default | Reviewer Requirement | Additional Gate |
| --- | --- | --- | --- |
| Basic isolated UI | Safe if independent | Normal | frontend tests/build |
| Clinical UI | Conditional | clinical-aware review | visual + regression |
| Backend domain | Conditional | backend + tenancy | targeted backend |
| Finance | Serial | finance/data-integrity | finance regression |
| Auth/RBAC | Serial | security review | auth/RBAC regression |
| RLS/Tenancy | Serial | security/tenancy | PostgreSQL RLS gates |
| Migration | Serial | DB review | migration lineage/schema |
| CI/CD | Serial | deployment review | workflow/governance |
| PWA service worker | Conditional/serial | PWA review | stale-deployment tests |

---

# 14. Rollback Plan

If the new workflow causes instability:

## Repository rollback

Revert only workflow migration commits.

Expected removable files:

```text
docs/engineering/DENTIX_AI_DEVELOPMENT_WORKFLOW_V2.md
.agents/skills/dentix-orchestration/
.github/ISSUE_TEMPLATE/dentix-agent-task.yml
.github/ISSUE_TEMPLATE/config.yml
.github/pull_request_template.md
.delegate/config.json
```

Restore minimal edits to:

```text
AGENTS.md
.agents/README.md
```

## External tooling rollback

Remove/disable external global skills through the installation mechanism used.

Deleting `.delegate/config.json` disables repository lane declarations.

## Safety invariant

No application-runtime rollback should be required because the workflow migration must not modify application behavior.

---

# 15. Success Criteria

The migration is successful only when all are true:

1. Native DENTIX policy remains authoritative.
2. No duplicated external engineering rulebook lives under native skills.
3. One real ticket completes through delegate -> review -> verification -> PR.
4. Two independent tickets complete in parallel isolated worktrees.
5. No parallel worker edits the same checkout.
6. Every ticket maps to explicit acceptance criteria.
7. Implementer reports are independently verified.
8. Existing branch governance is respected.
9. High-risk work defaults to serial execution.
10. No CodeRabbit/ECC regression is introduced.
11. The workflow can be disabled without affecting application runtime.
12. A large plan can be decomposed without losing any original requirement.

---

# 16. Metrics

Do NOT optimize primarily for "issues per day".

Track:

```text
Requirement coverage rate
Ticket first-pass verification rate
Rework rate
Regression rate
Skipped-requirement count
Hidden-dependency incidents
Parallel conflict count
CI pass rate
Review finding escape rate
Median ticket cycle time
```

Primary quality targets:

```text
Skipped approved requirements: 0
Cross-worktree write collisions: 0
Unauthorized tenant/RBAC/API/schema changes: 0
False DONE reports accepted by orchestrator: 0
Direct feature -> main promotion violations: 0
```

---

# 17. Recommended Rollout Order

Do not reorder without a concrete reason:

```text
DWF-00 Baseline
DWF-01 Workflow contract
DWF-02 Native orchestration skill
DWF-03 Issue contract
DWF-04 PR evidence template
DWF-05 Delegate installation
DWF-06 Fleet config
DWF-07 Read-only smoke
DWF-08 Single-ticket pilot
DWF-09 Two-ticket parallel pilot
DWF-10 Large-plan graph pilot
DWF-11 Debate review
DWF-12 Governance hardening
DWF-13 Final verification
```

---

# 18. Explicit Tooling Decision

## Matt Pocock Skills
**Do not bulk-install into DENTIX.**

Use the concepts:

- grilling,
- spec-first work,
- ticket decomposition,
- dependency-aware execution,
- TDD/feedback-loop discipline.

DENTIX native skills remain the implementation policy.

## Delegate Skills
**Adopt as external orchestration transport**, initially with only:

- `delegate-setup`
- `agy-delegate`
- `codex-delegate`

Do not install unnecessary relays.

## Review Skills
**Adopt only after the delegate pilot succeeds.**

Use debate review as additional independent review, not replacement for `dentix-code-review`.

---

# 19. Codex Execution Start Prompt

Use the following prompt with this file.

```text
You are the primary implementation orchestrator for:

DENTIX_AI_DEVELOPMENT_WORKFLOW_V2_FINAL_IMPLEMENTATION_PLAN.md

Repository:
Dentix-hub/dentix

Your job is to execute the approved plan exactly, not redesign or shorten it.

MANDATORY START:
1. Read the plan in full.
2. Read root AGENTS.md in full.
3. Read PROJECT_STANDARDS.md in full.
4. Read .agents/README.md.
5. Read the native plan-execution, testing-verification, and code-review skills.
6. Inspect current git status, branch, main, staging, current CI, and branch governance.
7. Build a ledger for every DWF task ID before editing.
8. Do not silently skip or combine task IDs.
9. Execute in phase order.
10. Do not install external skills or write delegate configuration until the corresponding plan phase.
11. Do not bulk-install Matt Pocock Skills.
12. Do not reintroduce CodeRabbit, ECC, or duplicate native skills.
13. Do not change product runtime/API/database/business behavior as part of this migration.
14. Never report a phase PASS before its exit gate is actually verified.
15. Final state must be DONE, PARTIAL, or BLOCKED.

BRANCH:
Create/use a scoped chore/* branch based on current staging, consistent with repository governance.
Do not work directly on main.

EXTERNAL TOOLING:
Treat delegate-skills/review-skills as external transport/review engines only.
DENTIX AGENTS.md, PROJECT_STANDARDS.md, native skills, security rules, and current CI remain authoritative.

PARALLELISM:
Do not begin write-capable parallel execution until the single-ticket pilot is verified.
Use isolated worktrees.
Never allow two write-capable delegates to share a checkout.
High-risk work remains serial unless the plan explicitly proves otherwise.

VERIFICATION:
Record exact commands, exit codes, changed files, and acceptance results.
An implementer saying tests passed is not verification; rerun required gates independently.

Begin with DWF-00 only.
At the end of each phase:
- update the ledger,
- list PASS/BLOCKED/NOT_STARTED IDs,
- show verification evidence,
- re-read the next phase before proceeding.
```

---

# 20. Final Approval Statement

This plan intentionally evolves DENTIX from:

```text
Large plan -> one AI session -> broad implementation claim -> repeated forensic re-audit
```

toward:

```text
Approved goal
-> explicit spec
-> complete atomic ticket graph
-> isolated delegated implementation
-> independent DENTIX review
-> real repository verification
-> governed staging integration
-> controlled production promotion
```

The architecture is designed so that Codex, Antigravity, or future models can be replaced without changing the DENTIX engineering contract.

**The permanent asset is the workflow and evidence discipline, not any specific model.**
