# DENTIX AI Development Workflow V2.1
# Final Lean Master Implementation Plan

**Repository:** https://github.com/Dentix-hub/dentix  
**Target branch:** `staging`  
**Production branch:** `main`  
**Audit date:** 2026-08-30  
**Audited `staging` SHA:** `1b74eca07308f7e5bb48da351d765f9e5fd03c42`  
**Status:** FINAL IMPLEMENTATION PLAN — not yet implemented  
**Primary goal:** Maximize accepted development work per AI credit while preserving DENTIX safety, traceability, testing, and GitHub governance.

---


# TEMPORARY LEAN BOOTSTRAP EXECUTION OVERRIDE

**Authority:** Explicitly approved by the DENTIX Product Authority for implementing Workflow V2.1 itself.  
**Scope:** Applies only while executing this V2.1 workflow-redesign plan.  
**Purpose:** Prevent the current expensive V2 orchestration ceremony from recursively consuming excessive AI development credits while the workflow itself is being redesigned.

The current V2 orchestration ceremony **MUST NOT** be applied recursively to this implementation.

For **THIS PLAN ONLY**:

1. Execute directly from this approved master plan.
2. Use **one scoped implementation branch** and **one working checkout/worktree** unless true parallel writers are explicitly required.
3. Do **not** create one GitHub Issue, branch, worktree, PR, reviewer session, or CI cycle per `LWF-*` micro-task.
4. `LWF-*` task IDs are **implementation/checklist units**, not release units.
5. Execute strictly **phase-by-phase**.
6. Do **not** run broad tests/build/CI after every `LWF-*` task.
7. During a phase, run only cheap targeted checks needed to catch syntax/configuration errors or directly validate the changed artifact.
8. Run required **phase-level verification once** at the end of the phase.
9. Do **not** invoke an independent reviewer after every task.
10. Independent **Codex review** is required only at:
    - the CI/governance redesign gate;
    - final completion before merge.
11. Do **not** use AI/model turns to poll GitHub Actions, deployments, Vercel, Hugging Face, or any asynchronous job.
12. After pushing a PR or triggering CI, stop the model loop and report `AWAITING_CI`.
13. Do **not** deploy or promote to `main` as part of this bootstrap implementation.
14. Do **not** modify `.delegate/config.json` write-lane routing during the bootstrap implementation unless this plan explicitly reaches the later model-routing pilot.
15. Do **not** activate DWF-11 debate review.
16. Do **not** spawn additional agents/subagents for deterministic, single-surface edits.
17. Do **not** reread unchanged repository policy files repeatedly in the same session.
18. Preserve all security, tenant/RBAC/RLS, finance, clinical-semantics, branch-governance, and no-fake-verification rules.
19. A phase may be marked `PASS` only after its phase-level verification.
20. Final status must remain strictly `DONE`, `PARTIAL`, or `BLOCKED`.

**Primary bootstrap optimization goal:**

```text
Complete the workflow redesign with the minimum necessary
AI calls, review sessions, repeated context loading,
and verification cycles,
without reducing correctness or repository safety.
```

---

# EXECUTION OWNERSHIP DURING THE BOOTSTRAP

## Gemini 3.7 Flash inside Antigravity — Primary Implementer

Gemini 3.7 Flash is the default implementer for this bootstrap because most work is bounded repository policy/configuration work: Markdown, YAML, deterministic scripts, issue/PR templates, labels, and CI workflow edits.

Flash owns:

- Phase 0 — Freeze and baseline
- Phase 1 — Core contract rewrite
- Phase 2 — GitHub contract surfaces
- Phase 3 — CI classifier and conditional execution
- Phase 4 — deterministic CI signal
- Phase 6 — Odontogram retrofit
- fixes resulting from Codex review findings
- preparation of final implementation evidence

Flash must **not**:

- merge to `staging` or `main`
- enable DWF-11 by default
- change write-lane routing prematurely
- poll CI with model turns
- claim `DONE` before all required phases/gates are complete

## Codex — Reviewer / High-Risk Validator Only

During this bootstrap, Codex is intentionally **not** the primary implementer.

Codex is invoked only for:

1. **CI / governance review gate** after Phase 3 + Phase 4.
2. **Final forensic review** after the complete V2.1 bootstrap implementation.

This is deliberate to minimize expensive reasoning/model calls while keeping independent review where it matters most.

## GitHub — Coordination and Deterministic CI

GitHub remains responsible for:

- issues / labels / wave state
- branches / PRs
- status checks
- protected branch governance
- CI/CD execution
- persistent green/red state

GitHub automation should replace model waiting wherever deterministic automation can do the job.

---

# GEMINI 3.7 FLASH — START PROMPT

Use this prompt to start the implementation in Antigravity:

```text
You are the primary implementer for the DENTIX AI Development Workflow V2.1 Lean Bootstrap.

Repository:
https://github.com/Dentix-hub/dentix

Target integration branch:
staging

Approved implementation plan:
DENTIX_AI_DEVELOPMENT_WORKFLOW_V2_1_LEAN_MASTER_IMPLEMENTATION_PLAN_EXECUTION_READY.md

IMPORTANT:
The Temporary Lean Bootstrap Execution Override at the top of the plan is explicitly approved by the DENTIX Product Authority and applies to this plan only.

Your job:
1. Read the complete approved plan once before editing.
2. Confirm current staging HEAD and compare it with the audited base SHA recorded in the plan.
3. If staging changed, inspect only the workflow-relevant drift before continuing.
4. Execute the plan phase-by-phase.
5. Treat LWF task IDs as checklist units, NOT separate PR/review/CI units.
6. Use one scoped implementation branch/worktree unless true parallel writers are required.
7. Do not create a separate issue/branch/worktree/PR/reviewer/CI cycle for every LWF micro-task.
8. During each phase, run only cheap targeted validation necessary for the artifact you just changed.
9. Run one required phase-level verification at the end of each phase.
10. Do not invoke independent review after every task.
11. Stop after Phase 3 + Phase 4 and prepare a concise review package for Codex.
12. After Codex review, fix only validated findings, then continue.
13. Do not use model turns to poll GitHub Actions or deployment.
14. After triggering CI, report AWAITING_CI and stop.
15. Do not merge to staging or main.
16. Do not activate DWF-11 debate review.
17. Do not change .delegate/config.json write routing until the plan reaches the measured routing pilot.
18. Do not weaken security, tenancy/RBAC/RLS, finance, clinical semantics, branch governance, or verification truthfulness.
19. Preserve every approved requirement; final status must be DONE, PARTIAL, or BLOCKED.

Execution style:
- surgical edits
- minimal context rereads
- deterministic scripts over conversational reasoning when possible
- concise progress reporting
- no repetitive status narration
- no redundant full-suite runs

Begin with Phase 0.
```

---

# CODEX REVIEW GATE 1 — CI / GOVERNANCE

Invoke Codex **once** after Gemini finishes Phase 3 + Phase 4 and before continuing to the Odontogram retrofit.

Use this prompt:

```text
Perform a focused independent review of the DENTIX Workflow V2.1 bootstrap implementation, limited to Phase 3 and Phase 4.

Repository:
https://github.com/Dentix-hub/dentix

Review scope:
- CI change classifier
- conditional CI execution
- required status-context preservation
- GitHub ruleset compatibility
- protected staging/main behavior
- HIGH_RISK force-full behavior
- branch-governance preservation
- platform branch-protection preservation
- workflow_run security model
- agent-ci-signal workflow
- permissions
- no-AI-polling behavior

Do NOT redesign the entire workflow.
Do NOT review unrelated application code.
Do NOT suggest stylistic refactors unless they affect correctness or safety.

Required checks:
1. Can any required status context disappear and leave a PR permanently blocked?
2. Can a FAST/STANDARD classification incorrectly bypass a required high-risk gate?
3. Do staging/main pushes still run full validation?
4. Does HIGH_RISK reliably force full validation?
5. Is unknown/ambiguous classification fail-safe?
6. Can untrusted PR code execute with elevated workflow_run permissions?
7. Are workflow permissions minimal?
8. Can the CI signal mark green prematurely?
9. Can the signal workflow merge or mutate code? It must not.
10. Does any part of the implementation reintroduce model-driven CI polling?
11. Does cd.yml still deploy only the intended tested protected-branch revision?
12. Are current GitHub required status contexts/ruleset constraints preserved?

Output:
- PASS or FAIL
- findings only, ordered CRITICAL/HIGH/MEDIUM/LOW
- exact file/location
- impact
- smallest remediation

If there are no actionable findings, state:
PASS — CI/GOVERNANCE GATE APPROVED
```

---

# GEMINI — POST-REVIEW INSTRUCTION

After Codex Review Gate 1:

```text
Apply only validated Codex findings from the CI/Governance review.

For every finding:
- verify it against the actual code/config first;
- make the smallest correct fix;
- run the smallest directly relevant check;
- do not broaden scope;
- do not rerun unrelated full suites.

When all validated findings are resolved:
- rerun the Phase 3/4 gate once;
- record exact evidence;
- continue with Phase 6.
```

---

# CODEX REVIEW GATE 2 — FINAL FORENSIC REVIEW

Invoke Codex **once** after Gemini has completed the entire bootstrap implementation and all non-CI local/phase gates.

Use this prompt:

```text
Perform the final forensic review of the complete DENTIX AI Development Workflow V2.1 Lean Bootstrap implementation.

Repository:
https://github.com/Dentix-hub/dentix

Authority:
DENTIX_AI_DEVELOPMENT_WORKFLOW_V2_1_LEAN_MASTER_IMPLEMENTATION_PLAN_EXECUTION_READY.md

Review the actual diff against the full approved plan.

Primary goal:
Detect missing requirements, contradictions, unsafe shortcuts, CI/governance regressions, excessive remaining ceremony, or places where the implementation claims lean behavior but still performs per-micro-ticket review/test/CI cycles.

Required review dimensions:
1. Requirement coverage — no LWF requirement silently skipped.
2. FAST/STANDARD/HIGH_RISK classification is explicit and enforceable.
3. T0/T1/T2/T3 cadence is internally consistent.
4. STANDARD review is wave-level, not per-ticket.
5. HIGH_RISK remains strict.
6. No model-driven CI/deployment polling remains.
7. GitHub remains the persistent coordination layer.
8. Worktree isolation remains strict for concurrent writers.
9. Serial wave reuse does not permit concurrent shared-checkout writers.
10. Issue/PR templates reinforce the new behavior instead of the old expensive behavior.
11. No stale fixed coverage thresholds remain in agent policy.
12. Debugging skill is failure-only.
13. Code-review trigger is wave/high-risk/final, not every trivial diff.
14. Required CI contexts/ruleset behavior remain safe.
15. staging/main protected pushes still receive full validation.
16. Odontogram #126–#133 are reclassified without losing any source requirement.
17. #127 clinical semantics remains high-risk.
18. #132/#133 retain the Part I regression/handoff hard gate.
19. .delegate write routing remains unchanged until the measured routing pilot.
20. DWF-11 debate remains optional/deferred.
21. No automatic merge or unauthorized production promotion was introduced.
22. Telemetry is sufficient to compare speed/credit efficiency after the pilot.

Do not redesign unless required to fix a real defect.
Do not demand per-ticket ceremony that the approved V2.1 plan intentionally removed.

Output:
- FINAL VERDICT: PASS / PARTIAL / FAIL
- missing requirements
- findings by severity
- exact locations
- smallest remediation
- remaining blockers before the V2.1 pilot

If clean, state:
FINAL VERDICT: PASS — READY FOR LEAN PILOT
```

---

# BOOTSTRAP EXECUTION SUMMARY

The intended temporary execution path is:

```text
Gemini 3.7 Flash / Antigravity
          │
          ├─ Phase 0
          ├─ Phase 1
          ├─ Phase 2
          ├─ Phase 3
          └─ Phase 4
                 │
                 ▼
          CODEX REVIEW #1
          CI / GOVERNANCE ONLY
                 │
                 ▼
          Gemini fixes findings
                 │
                 ├─ Phase 6
                 └─ remaining bootstrap work
                 │
                 ▼
          CODEX REVIEW #2
          FINAL FORENSIC REVIEW
                 │
                 ▼
          Gemini fixes validated findings
                 │
                 ▼
          PR / CI
                 │
                 ▼
          AWAITING_CI
          AI STOPS
```

After Workflow V2.1 is implemented and accepted, this temporary bootstrap override expires and the normal V2.1 workflow becomes authoritative.

---

## 0. Executive decision

DENTIX keeps Workflow V2's architecture.

We do **not** remove:

- GitHub Issues / PRs / branch governance.
- Dependency graphs.
- Worktree isolation for concurrent writers.
- `staging` → `main` promotion discipline.
- CI/CD.
- Requirement coverage ledgers.
- High-risk security / tenancy / RBAC / finance / migration controls.
- Independent review where risk justifies it.
- The existing 11 native DENTIX skills.

We change one core assumption:

```text
OLD V2:
micro-ticket = implementation unit
             = review unit
             = verification unit
             = PR unit
             = CI unit

V2.1 LEAN:
micro-ticket = scope / traceability unit

wave or high-risk boundary = review unit
wave or phase              = verification unit
wave                       = normal PR unit
high-risk ticket           = individual PR unit
release / protected push   = full CI unit
```

The target is:

```text
small tasks remain small
WITHOUT
making every small task pay a full AI-review-test-PR-CI lifecycle.
```

---

# 1. Inputs used for this plan

This final plan reconciles:

1. Current repository state on `staging`.
2. `DENTIX_LEAN_WORKFLOW_AMENDED_PLAN (1).md`.
3. `DENTIX_AI_WORKFLOW_MISTAKES_RETROSPECTIVE_AND_LEAN_IMPROVEMENT_PLAN.md`.
4. The earlier DENTIX workflow review brief.
5. Direct inspection of:
   - `AGENTS.md`
   - `.agents/README.md`
   - core workflow skills
   - `.delegate/config.json`
   - GitHub Issue / PR templates
   - `docs/engineering/DENTIX_AI_DEVELOPMENT_WORKFLOW_V2.md`
   - `docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md`
   - current GitHub Actions workflows
   - current repository ruleset
   - Issues #126–#133
   - PR #134
   - PR #135
   - pilot PRs #121, #124, #125

---

# 2. Repository truth — final audited snapshot

## 2.1 Workflow V2 is already live on `staging`

The repository already contains the V2 contract, 11 native skills, agent issue/PR templates, delegate configuration, protected branches, CI/CD workflows, and the Odontogram graph.

The architecture works. The problem is its cost profile.

## 2.2 DWF-10 already started

PR **#134** (`docs(workflow): map odontogram plan to ticket graph`) was merged into `staging`.

Current graph:

```text
#126 → #127 → #128 → #129 → #130 → #131 → #132 → #133
```

All eight are currently treated as clinical-risk and serial.

Therefore the lean redesign must **retrofit the graph before #126 implementation starts**.

## 2.3 PR #135 is open and must not be merged as-is

PR #135 proposes:

- `review-main` → `agy`, read-only
- `review-debate` → `codex`, read-only
- write concurrency cap 2 → 3
- debate/pilot hardening text

Its own gate says debate smoke did not run because external-provider data sharing still needs explicit authorization.

Decision:

```text
DO NOT MERGE #135 during V2.1.
Preserve its branch as deferred evidence.
Do not raise write concurrency to 3 yet.
Revisit optional debate review only after the lean pilot.
```

## 2.4 Current write routing is still Codex-only

Committed `.delegate/config.json`:

```text
feature → codex
ui      → codex
tests   → codex
complex → codex
```

Antigravity is a supported runtime/environment, but committed `staging` does **not** currently route normal write work to a cheaper Antigravity lane.

Process waste must be reduced first; model routing is a later measured experiment.

---

# 3. Corrections from direct repo audit

## 3.1 Path filtering exists partially

Path filtering already exists in:

- `.github/workflows/mobile.yml`
- `.github/workflows/design-system-guardrails.yml`

But several expensive required workflows are broad, including:

- `ci.yml`
- `cross-tenant-http-postgres.yml`
- `rls-concurrency.yml`
- `mobile-responsive.yml`
- `stale-deployment-recovery.yml`
- `history-secret-scan.yml`
- `platform-branch-protection.yml`

Correct conclusion:

> DENTIX already uses path scoping selectively, but its heaviest required PR gates remain mostly broad.

## 3.2 Naive workflow `paths:` filtering would be unsafe

The active ruleset **Protect main and staging** requires named checks including:

- Backend Tests + Security
- Frontend Tests
- Frozen Dependency Reproducibility
- E2E Critical Path (Playwright)
- Validate Production Container
- Concurrent Tenant Isolation
- Reproduce / Recover Stale Frontend Assets
- Responsive Acceptance Matrix
- Full Git History Secret Scan
- Verify GitHub branch enforcement
- Validate promotion path
- Protect authoritative CD workflow

Some contexts are duplicated with/without an integration ID.

Therefore required workflows must not simply disappear on low-risk PRs.

V2.1 should keep required check contexts materialized while conditionally skipping expensive work inside them.

## 3.3 Stale coverage policy exists in three places

Actual current CI:

```text
--cov-fail-under=52
```

Stale `70%` references exist in:

1. `AGENTS.md`
2. `.agents/README.md`
3. `.agents/skills/dentix-testing-verification/SKILL.md`

Decision:

```text
Remove hard-coded coverage percentages from agent policy.
The current CI configuration is the only operational threshold source.
```

## 3.4 The pilot proves CI fan-out

A one-file test-only PR (#124) triggered nine workflows:

- Dentix CI
- Platform Branch Protection
- Branch Governance
- History Secret Scan
- Design System Guardrails
- RLS Concurrency
- Stale Deployment Recovery
- PostgreSQL HTTP IDOR Gate
- Mobile Responsive Gate

Its `Dentix CI` run also executed:

- Backend Tests + Security
- Frontend Tests
- Frozen Dependency Reproducibility
- E2E Critical Path
- Validate Production Container

This is direct evidence that low-risk changes currently pay high-risk pipeline cost.

---

# 4. Working environment and roles

## Codex

Remains default:

- orchestrator
- plan interpreter
- dependency/risk classifier
- complex implementer
- high-risk implementer
- governed reviewer/integrator where required

Codex should **not** spend model turns:

- polling CI/deployment
- rereading unchanged policy files
- rerunning broad tests after every micro-ticket
- creating extra reviewer sessions for trivial diffs
- delegating trivial work to an equally expensive model without value

## Antigravity

Remains:

- supported DENTIX development runtime / IDE environment
- candidate delegate execution path
- future cheaper-lane candidate for bounded FAST work
- possible read-only reviewer through `agy` after authorization/proof

It is not yet the committed automatic write router.

## GitHub

Remains the persistent coordination/control plane:

```text
approved plan
→ issues
→ dependency graph / wave state
→ branches/worktrees
→ PR
→ checks
→ staging
→ full protected-branch CI
→ CD
→ main promotion
```

GitHub carries persistent state so AI context does not have to.

## User / Product Authority

User intervention remains required for:

- approving goals/plans
- meaningful scope expansion
- disputed clinical semantics
- finance semantics
- auth/RBAC/tenant policy changes
- destructive migrations
- external provider/data-sharing authorization
- production promotion
- explicitly human-governed merge decisions

User intervention should **not** be required for:

- each micro-task
- each targeted local test
- ordinary dependency bookkeeping
- waiting for CI
- repeatedly checking GitHub Actions
- normal FAST/STANDARD work inside an approved wave

---

# 5. Current automation vs target automation

| Activity | Current | V2.1 target |
|---|---|---|
| Plan decomposition | AI while session active | same, but lean classification |
| Issue/label creation | AI/tool when invoked | same |
| Worktree/delegate dispatch | active orchestration | same, fewer unnecessary worktrees |
| Local implementation | AI | same |
| PR creation | AI/tool | wave PR by default |
| CI after PR/push | automatic | automatic |
| CD after successful protected push CI | automatic via `workflow_run` | unchanged |
| CI waiting | can become model polling | **model polling forbidden** |
| CI state signal | fragmented | deterministic green/red signal |
| AI auto-resume | not proven | not assumed in V2.1 |
| Merge | not auto-merge | unchanged |
| Debate review | blocked/unproven | optional after pilot only |

Target flow:

```text
USER approves plan
        ↓
CODEX classifies and creates waves
        ↓
delegates implement
        ↓
wave gate
        ↓
PR
        ↓
AI STOPS
        ↓
GitHub runs checks
        ↓
GitHub records green/red
        ↓
next AI invocation reads ONE state
        ↓
continue or debug
```

Important: a GitHub label/comment is a **resume signal**, not proof that GitHub can reopen an interactive Codex/Antigravity session. True automatic wake is deferred until a supported secure runtime webhook is proven.

---

# 6. Execution modes

Every executable ticket must declare:

```text
execution_mode
risk_class
parallel_class
wave_id
verification_tier
review_policy
pr_strategy
```

## FAST

Initial allowlist:

```text
tests-only
OR docs-only
OR isolated presentational UI

AND touched-file pilot cap ≤ 3
AND one subsystem
AND no shared contract
AND no auth/RBAC/tenancy/RLS
AND no finance
AND no migration
AND no security-control change
AND no clinical semantics
AND no deployment/governance change
AND no irreversible data behavior
AND actual files remain inside expected touch surface
```

The 3-file cap is a pilot threshold, not permanent doctrine.

FAST:

- no independent reviewer per ticket
- T1 where relevant
- mechanical orchestrator diff/scope inspection
- T2 once per wave if required
- wave PR allowed
- no model CI polling

## STANDARD

For ordinary product work outside the HIGH_RISK closed list.

Initial wave budget:

```text
≤ 5 tickets
one subsystem
compatible risk family
no HIGH_RISK ticket mixed in
one commit per ticket
```

STANDARD:

- T1 where needed
- independent review once per wave
- reviewer distinct from implementer
- T2 once at wave boundary
- one PR per wave
- no polling

## HIGH_RISK

Closed list:

- authentication
- RBAC
- tenant isolation / RLS
- finance / money / invoices / commissions
- migrations / model-schema lineage
- security controls / secrets / cookies / CORS
- shared API/session/tenant/money contracts
- clinical semantics / tooth identity / notation meaning / treatment meaning
- deployment / branch governance
- irreversible data operations

HIGH_RISK:

- `SERIAL_ONLY` by default
- individual review per ticket
- immediate T1
- risk-specific T2
- full T3
- individual PR
- no FAST downgrade
- no mixed-risk wave
- no automatic merge

---

# 7. Clinical risk split

Replace broad operational use of `risk:clinical` with:

## `risk:clinical-semantics`

Examples:

- tooth identity
- notation mapping
- clinical condition meaning
- treatment meaning
- persisted clinical interpretation

Default: `HIGH_RISK`.

## `risk:clinical-ui`

Examples:

- renderer layout
- root visual geometry when source-of-truth is unchanged
- shell/inspector UI
- responsive behavior
- RTL/LTR
- visual accessibility
- demo presentation

Default: `STANDARD` + mandatory visual evidence.

Any source-of-truth/semantic touch escalates immediately.

---

# 8. Verification tiers

## T0 — development sanity
Quick syntax/type/lint sanity. Not a completion gate.

## T1 — targeted ticket verification
Required for production changes, direct regressions, or explicit acceptance/risk needs.

```text
production code ⇒ T1 before wave gate
```

## T2 — wave/phase gate
Once per wave:

- subsystem lint
- subsystem tests
- subsystem build
- visual/RTL/responsive/a11y evidence when relevant
- relevant integration tests

## T3 — repository/protected integration
For:

- risk-appropriate PR checks
- full HIGH_RISK checks
- protected `staging`/`main` pushes
- production promotion

Current CI owns exact commands/thresholds.

---

# 9. Review policy

```text
FAST tests/docs:
  orchestrator mechanical inspection only

FAST isolated presentational UI:
  T1 + mechanical inspection
  escalate to STANDARD if behavior expands

STANDARD:
  one independent review per wave

HIGH_RISK:
  independent review per ticket

FINAL / explicit request:
  final review gate

DWF-11 debate:
  rare opt-in escalation only
```

DWF-11 is for difficult security, tenancy, finance, migration, architecture, or unresolved high-severity disputes — not daily development.


# 10. Ticket lifecycle V2.1

```text
DRAFT
→ READY
→ IN_PROGRESS
→ IMPLEMENTED
→ WAVE_READY
→ AWAITING_CI
→ VERIFIED
→ CLOSED
```

Additional states:

```text
BLOCKED
CI_RED
```

Meaning:

- `IMPLEMENTED`: ticket implementation returned; not a global quality claim.
- `WAVE_READY`: wave implementation is ready for gate/review.
- `AWAITING_CI`: PR exists; AI stops polling.
- `VERIFIED`: required wave/risk gates passed.
- `CLOSED`: traceability complete.

FAST/STANDARD tickets may reach `IMPLEMENTED` without their own independent review.

---

# 11. Worktree policy

Concurrent writers:

```text
1 concurrent writer = 1 isolated worktree
```

Non-negotiable.

Serial tickets inside one wave:

```text
one implementer
one worktree
multiple bounded ticket commits
```

Do not create a fresh worktree simply because the next serial micro-ticket begins.

---

# 12. PR strategy

## FAST / STANDARD wave PR

Allowed when:

- same approved plan
- same `wave_id`
- same target branch
- compatible risk
- no HIGH_RISK ticket
- related subsystem
- one commit per ticket

PR includes:

| Issue | Commit | Files |
|---|---|---|

## HIGH_RISK

```text
1 ticket = 1 PR
```

Pilot PRs #121/#124/#125 must be documented as **pilot-only one-ticket-one-PR evidence**, not the daily default.

---

# 13. CI redesign — required-context-safe

## 13.1 Deterministic change classifier

Create a repository-owned deterministic classifier, e.g.:

```text
.github/scripts/classify_ci_scope.py
```

No model call.

Inputs:

- event type
- base SHA
- head SHA
- changed files
- PR labels where available

Outputs:

```text
frontend
backend
mobile
dependencies
pwa
container
auth
tenancy
finance
migration
security
clinical_semantics
clinical_ui
workflow_governance
force_full
```

Unknown/ambiguous classification:

```text
force_full = true
```

## 13.2 PR behavior

### FAST frontend test/docs/presentational work

Run expensive work only when relevant.

Examples:

- Frontend Tests → run
- Design System Guardrails → when relevant
- Responsive Gate → relevant UI/clinical-ui only
- Backend/RLS/IDOR → skipped safely while required context still materializes
- Dependency reproducibility → dependency files only
- Production container → container/runtime/dependency surface or uncertainty
- Stale deployment recovery → PWA/deployment surface
- Branch Governance → always
- Platform Branch Protection → always

### STANDARD

Subsystem gates + relevant integration gates.

Cross-domain/shared-contract uncertainty broadens automatically.

### HIGH_RISK

```text
force_full = true
```

## 13.3 Protected pushes

For:

```text
push → staging
push → main
staging → main promotion
```

full validation runs.

This preserves the safety property:

> low-risk PR feedback can be selective, while the integrated `staging` revision still receives full protected-branch CI before automatic staging deployment.

`cd.yml` already uses successful `Dentix CI` protected-branch completion.

## 13.4 Specialized workflows

Keep cheap/governance checks always:

- branch governance
- platform branch enforcement

Keep existing path filters:

- Flutter mobile
- design-system guardrails

Condition expensive work:

- RLS concurrency
- HTTP IDOR
- mobile-responsive web gate
- stale-deployment recovery

Secret scanning:

```text
PR: newly introduced commit/range scan
protected push/manual/scheduled: full-history scan
```

Any security uncertainty forces full.

---

# 14. No AI CI polling

Add explicit repository rule:

```text
MODEL-DRIVEN CI POLLING IS FORBIDDEN.
```

After PR push:

1. record PR number
2. record head SHA
3. record workflow run IDs if useful
4. set/record `agent:awaiting-ci`
5. stop the model loop

Forbidden pattern:

```text
check → sleep → check → sleep → check
```

A deterministic non-model watcher may be used only if it costs no model turns and is safe in the runtime.

---

# 15. Deterministic CI completion signal

Create:

```text
.github/workflows/agent-ci-signal.yml
```

Requirements:

- trusted workflow code from default branch
- no execution of untrusted PR code
- read GitHub workflow/check state
- after relevant workflow completion:
  - resolve PR/SHA
  - inspect all required contexts
  - pending → keep `agent:awaiting-ci`
  - failure → `agent:ci-red`
  - all accepted → `agent:ci-green`
- one comment per state transition
- failed job links only on red
- no AI/model call
- no merge
- minimal permissions

Important:

`workflow_run` uses the default-branch workflow definition. Therefore this workflow must reach `main` before it is relied upon for staging workflow events.

---

# 16. AI resume policy

V2.1 baseline:

```text
GitHub state signal = automatic
AI wake = not assumed
```

On next invocation:

```text
read state once

green:
  continue

red:
  load dentix-systematic-debugging
  inspect failed logs first
  make smallest responsible fix
  T1 affected surface
  push
  return to AWAITING_CI
```

A future V2.2 may add true webhook/runtime wake only if officially supported and securely authorized.

Do not add provider secrets to repository files merely to achieve wake behavior.

---

# 17. Context and skill loading

## 17.1 No 12th native skill

Do not add an efficiency skill.

Efficiency belongs in:

- orchestration
- plan execution
- testing
- review triggers
- templates
- CI

## 17.2 Trigger index

```text
multi-ticket approved plan   → plan-execution + orchestration
backend                      → backend-fastapi
frontend                     → frontend-react
mobile                       → mobile-flutter
migration                    → database-migrations
auth/RBAC/RLS                → security-tenancy-rbac
performance investigation    → performance
actual failure               → systematic-debugging
wave/high-risk/final review  → code-review
wave/release verification    → testing-verification
```

Do not load skills because they might theoretically apply.

## 17.3 Implementer brief

A normal delegate receives only:

- objective
- source requirement IDs
- scope
- non-goals
- expected touch surface
- acceptance criteria
- mode
- risk
- parallel class
- wave
- short DENTIX invariants
- relevant domain skill
- explicit T1 requirements

Do not force every low-risk delegate to reread full orchestration policy and unrelated skills.

HIGH_RISK/contract work reads the required authoritative policies fully.

## 17.4 Reread rule

Do not reread an unchanged file in the same session unless:

- context was lost/compacted
- file changed
- ambiguity appeared
- rebase changed authority SHA

---

# 18. Exact policy/skill changes

## `AGENTS.md`

- remove stale `70%`
- say active CI owns thresholds
- add concise mode reference
- add no-model-polling rule
- keep safety invariants
- avoid duplicating full algorithms

## `.agents/README.md`

- remove `70% CI coverage target`
- add activation trigger/index
- mark debugging failure-only
- mark code review wave/high-risk/final
- mark testing gate-triggered
- keep 11 skills

## `dentix-orchestration`

Major change:

- FAST/STANDARD/HIGH_RISK
- `wave_id`
- wave budget
- ticket implementation vs wave verification
- review by mode
- wave PRs
- graph recalculation only immediately on drift/contract changes, otherwise wave boundary
- serial worktree reuse
- no polling
- `AWAITING_CI`
- no auto-merge

## `dentix-plan-execution`

Replace ambiguous task/phase verification with:

```text
default expensive verification unit = approved wave or phase
T1 occurs at ticket level only where required
```

Keep requirement ledger and anti-skip, but reconcile at:

- wave boundary
- phase boundary
- drift
- final completion

## `dentix-testing-verification`

- remove hard-coded percentages
- add T0/T1/T2/T3
- clarify targeted-first does not mean test after every trivial micro-task
- broad verification belongs to gate boundaries

## `dentix-code-review`

Keep severity/review logic.

Activate only for:

- STANDARD wave
- each HIGH_RISK ticket
- shared-contract change
- final integration/release
- explicit review request

## `dentix-systematic-debugging`

Keep RCA.

Add:

```text
failure-only; do not preload on a clean execution path
```

## Domain skills

Do not rewrite backend/frontend/mobile/security/migration/performance for this rollout unless a direct contradiction is found.

Do a later size/duplication audit.

---

# 19. Issue template V2.1

Update:

```text
.github/ISSUE_TEMPLATE/dentix-agent-task.yml
```

Add:

```text
execution_mode: FAST | STANDARD | HIGH_RISK
wave_id
verification_tier
review_policy
pr_strategy
```

Keep:

- objective
- source plan/IDs
- scope
- non-goals
- dependencies
- parallel class
- risk
- acceptance criteria
- expected touch surface

Reduce repeated prose.

FAST verification defaults to T1, not a pasted full-CI checklist.

`required_skills` may be derived from domain + risk + gate instead of repeatedly listing generic orchestration/review skills.

---

# 20. PR templates

Use lean and high-risk variants.

## Lean wave template

For FAST/STANDARD:

- source plan
- wave ID
- issues
- Issue → Commit → Files
- mode/risk
- acceptance summary
- T1 summary
- T2 summary
- CI state
- limitations
- security/DB only when relevant

## High-risk template

Retain:

- security / tenancy / RBAC
- DB/migration
- full independent review
- risk verification
- full CI
- release limitations

---

# 21. Labels

Add:

```text
mode:fast
mode:standard
mode:high-risk

agent:wave-ready
agent:awaiting-ci
agent:ci-green
agent:ci-red

risk:clinical-ui
risk:clinical-semantics
```

Use a tracking issue/sub-issues or stable wave metadata for `wave_id`; avoid uncontrolled permanent label growth.

Migrate `risk:clinical` gradually.

---

# 22. GitHub authentication preflight

Before GitHub-heavy orchestration:

```text
gh auth status
```

or equivalent authenticated connector check.

If unavailable:

- stop once
- report one blocker
- do not retry unauthenticated API calls until rate-limited
- do not burn model turns on repeated failed reads

---

# 23. Telemetry

Per pilot wave:

```text
accepted requirements
model invocations
delegate invocations
reviewer invocations
T1 runs
T2 runs
T3 runs
PR count
GitHub workflow count
AI polling calls
READY → VERIFIED wall clock
first-pass acceptance
rework commits
loaded skills
escaped defects
```

If exposed:

```text
AI credits
input tokens
output tokens
```

North star:

```text
accepted requirements / AI credit
```

Secondary:

```text
accepted requirements / model invocation
```

Do not optimize issue count.

---

# 24. Baseline evidence

Historical exact AI-credit telemetry for #120/#122/#123 does not exist. Do not fabricate it.

Available process baseline:

- PR #121: one changed test file + broad local gates + independent review + CI
- PR #124: one changed test file + targeted + full frontend + independent review + broad CI fan-out
- PR #125: same heavy pattern
- PR #124 triggered nine workflows
- its Dentix CI ran five major jobs

Use this as process baseline.


# 25. Odontogram retrofit — concrete proposal

Do not implement #126 under the current all-clinical/full-ticket-ceremony model.

## ODG-L1 — #126 root renderer

Proposed:

```text
mode: STANDARD
risk: clinical-ui
parallel: SERIAL_ONLY
wave: ODG-L1
```

Reason:

- issue explicitly forbids schema/API/persistence/source-of-truth changes
- scope is renderer/root-layer visual correctness
- clinically meaningful visual evidence remains mandatory

Required:

- T1 focused renderer/root tests
- visual matrix for all tooth families
- T2 clinical-chart/frontend gate
- one independent wave review
- one PR

Escalate to HIGH_RISK immediately if implementation touches:

- tooth identity
- notation semantics
- persisted clinical state
- treatment meaning
- canonical clinical source of truth

## ODG-L2 — #127 notation

Proposed:

```text
mode: HIGH_RISK
risk: clinical-semantics
parallel: SERIAL_ONLY
wave: ODG-L2
PR: individual
```

Reason:

Notation/labels can alter tooth-identity meaning.

Required:

- T1 notation/label tests
- semantics-focused independent review
- visual evidence
- full T3
- individual PR

## ODG-L3 — #128 + #129 + #130 + #131

Preserve internal dependency order:

```text
#128 → #129 → #130 → #131
```

Proposed:

```text
mode: STANDARD
risk: clinical-ui
one serial writer/worktree
four bounded commits
one wave review
one T2 gate
one PR
```

T2 includes:

- clinical-chart tests
- frontend lint/build as relevant
- dual-instance isolation
- RTL/LTR
- responsive matrix
- accessibility evidence
- required screenshots

Each production change still gets T1.

## ODG-L4 final gate — #132 + #133

### #132

Treat as:

```text
PART-I REGRESSION GATE
```

Run:

- final relevant frontend suite
- final visual matrix
- baseline/new-failure classification
- no production changes unless a diagnosed regression requires them

### #133

Treat as:

```text
FINAL EVIDENCE
+ GEMINI HANDOFF
+ HARD STOP
```

Where practical, combine #132 gate evidence and #133 documentation/handoff into one final governed PR.

No Gemini G0-G16 work begins until the hard stop is explicitly satisfied.

---

# 26. Expected Odontogram reduction

Current pattern tends toward:

```text
8 tickets
≈ 8 independent review cycles
≈ repeated broad verification
≈ repeated PRs
≈ repeated CI fan-out
```

V2.1 target:

```text
#126                         → 1 STANDARD PR
#127                         → 1 HIGH_RISK PR
#128 + #129 + #130 + #131   → 1 STANDARD wave PR
#132 + #133                  → 1 final gate/evidence PR
```

Approximately four governed PR boundaries instead of eight, while preserving stricter treatment for semantics.

The exact number is not sacred. Drift/risk can force escalation.

---

# 27. Model routing experiment — only after process pilot

Do not edit write lanes first.

After a successful measured lean wave:

Candidate first experiment:

```text
FAST tests/docs → agy
```

Only if:

- callable in the real Antigravity environment
- data-sharing authorization is explicit where required
- write sandbox/worktree isolation is proven
- first-pass acceptance is measured
- rework remains acceptable

Measure:

- first-pass acceptance
- retries
- reviewer findings
- rework commits
- elapsed time
- credits/tokens if exposed

If rework erases the savings:

```text
return the class to Codex
```

Do not route complex/HIGH_RISK work to a weaker lane merely to lower nominal per-call cost.

---

# 28. PR #135 disposition

During V2.1:

```text
#135 = DEFERRED
```

Recommended implementation action:

- mark Draft/deferred where practical
- do not merge
- preserve branch
- record useful discoveries:
  - `agy` read-only resolution was possible
  - data-sharing gate is real
- do not adopt concurrency 3

After the lean pilot:

```text
close as unnecessary
OR
rebase as opt-in high-risk debate review
```

Never make debate review a daily default.

---

# 29. Detailed implementation sequence

## Phase 0 — Freeze and baseline

### LWF-00.01
Confirm `staging` base SHA.

Expected audit base:

```text
1b74eca07308f7e5bb48da351d765f9e5fd03c42
```

If it changed, inspect only changed workflow surfaces before proceeding.

### LWF-00.02
Freeze #126–#133 from implementation under old V2.

Do not delete issues or requirement mappings.

### LWF-00.03
Defer PR #135.

### LWF-00.04
Capture process baseline from #121/#124/#125.

### LWF-00.05
Create:

```text
chore/dtx-lean-workflow-v2-1
```

No product runtime changes in Phases 0–4.

### Phase 0 acceptance

- #126 is not dispatched under old rules.
- #127–#133 remain dependency-traceable.
- PR #135 is not merged.
- baseline evidence is recorded.
- working branch starts from current `staging`.

---

## Phase 1 — Core contract rewrite

Files:

```text
docs/engineering/DENTIX_AI_DEVELOPMENT_WORKFLOW_V2.md
AGENTS.md
.agents/README.md
.agents/skills/dentix-orchestration/SKILL.md
.agents/skills/dentix-plan-execution/SKILL.md
.agents/skills/dentix-testing-verification/SKILL.md
.agents/skills/dentix-code-review/SKILL.md
.agents/skills/dentix-systematic-debugging/SKILL.md
```

Tasks:

### LWF-01.01
Add FAST/STANDARD/HIGH_RISK definitions.

### LWF-01.02
Add T0/T1/T2/T3.

### LWF-01.03
Add wave lifecycle and initial budgets.

### LWF-01.04
Move STANDARD independent review to wave boundary.

### LWF-01.05
Keep HIGH_RISK review per ticket.

### LWF-01.06
Add explicit no-model-polling rule.

### LWF-01.07
Add serial-worktree reuse.

### LWF-01.08
Add drift-abort:
actual touched production files outside expected surface → stop/reclassify.

### LWF-01.09
Recalculate graph:
- immediately on drift/contract change
- otherwise wave boundary

### LWF-01.10
Remove all stale hard-coded coverage values.

### LWF-01.11
Mark #120/#122/#123 one-ticket-one-PR behavior as pilot-only.

### LWF-01.12
Validate skill count remains 11.

Phase 1 acceptance:

- no new skill
- no app runtime behavior change
- no weakened security/tenant/finance rule
- no contradictory verification cadence
- no hard-coded coverage threshold in agent policy
- failure/debug skill no longer preloaded on clean work
- code-review trigger is explicit

---

## Phase 2 — GitHub contract surfaces

Files:

```text
.github/ISSUE_TEMPLATE/dentix-agent-task.yml
.github/pull_request_template.md
.github/PULL_REQUEST_TEMPLATE/high-risk.md   # if chosen
```

Tasks:

### LWF-02.01
Add execution mode field.

### LWF-02.02
Add wave ID.

### LWF-02.03
Add verification tier.

### LWF-02.04
Add review policy.

### LWF-02.05
Add PR strategy.

### LWF-02.06
Simplify FAST evidence requirements.

### LWF-02.07
Stop forcing every ticket to repeat generic skill lists where derivable.

### LWF-02.08
Add compact efficiency telemetry.

### LWF-02.09
Create labels:
- mode
- clinical split
- wave-ready
- awaiting/green/red CI

### LWF-02.10
Validate Issue Form YAML.

### LWF-02.11
Create one synthetic FAST and one synthetic HIGH_RISK contract and confirm they are unambiguous without executing product changes.

Phase 2 acceptance:

- FAST issue does not ask for universal full CI/review prose.
- HIGH_RISK issue still carries full controls.
- templates map directly to the new orchestration algorithm.

---

## Phase 3 — CI scope classifier and conditional execution

Potential files:

```text
.github/scripts/classify_ci_scope.py
.github/workflows/ci.yml
.github/workflows/cross-tenant-http-postgres.yml
.github/workflows/rls-concurrency.yml
.github/workflows/mobile-responsive.yml
.github/workflows/stale-deployment-recovery.yml
.github/workflows/history-secret-scan.yml
```

### LWF-03.01
Snapshot required status contexts from the active ruleset.

### LWF-03.02
Implement deterministic classifier.

### LWF-03.03
Test classifier against:

1. frontend test-only
2. frontend presentational
3. PWA/service-worker
4. backend
5. auth/RBAC
6. tenant/RLS
7. finance
8. migration/schema
9. dependency lock
10. Docker/runtime/deployment
11. workflow/governance
12. mixed frontend/backend
13. unknown path → full

### LWF-03.04
Condition expensive jobs while preserving terminal required check contexts.

### LWF-03.05
Guarantee full validation for push to `staging`.

### LWF-03.06
Guarantee full validation for push to `main`.

### LWF-03.07
Guarantee full validation for HIGH_RISK.

### LWF-03.08
Use PR-range/new-commit secret scan on ordinary PRs; full history on protected pushes/manual/scheduled.

### LWF-03.09
Test low-risk PR:
all required contexts must resolve; irrelevant expensive bodies must not run.

### LWF-03.10
Test high-risk/workflow-sensitive scenario:
full required gates must run.

### LWF-03.11
Do not alter ruleset status names until conditional behavior is proven.

Phase 3 acceptance:

- low-risk PR cannot hang because a required context is absent
- high-risk cannot bypass full validation
- protected pushes remain full
- `cd.yml` still gates deployment on tested protected revision
- no new third-party action is required if repository-owned classifier can do the job

---

## Phase 4 — Deterministic CI signal / no polling

File:

```text
.github/workflows/agent-ci-signal.yml
```

Tasks:

### LWF-04.01
Listen to relevant workflow completion events.

### LWF-04.02
Resolve PR and head SHA safely.

### LWF-04.03
Read required contexts.

### LWF-04.04
Maintain `agent:awaiting-ci`.

### LWF-04.05
Set `agent:ci-red` when a required check fails.

### LWF-04.06
Set `agent:ci-green` only when all required checks are terminal/accepted.

### LWF-04.07
Comment only on state transition.

### LWF-04.08
Link failing jobs only.

### LWF-04.09
No AI call, external model call, merge, or PR code execution.

### LWF-04.10
Promote workflow definition to `main` before relying on `workflow_run`.

Phase 4 acceptance:

```text
AI poll calls = 0
```

for the pilot.

---

## Phase 5 — Ruleset cleanup, only if justified

Do only after Phase 3 works.

Potential:

- remove proven duplicate status contexts
- preserve strict up-to-date requirement
- preserve PR protection
- preserve review-thread resolution

Do not consolidate checks merely for aesthetics.

---

## Phase 6 — Retrofit Odontogram graph

State/files:

```text
docs/engineering/ODONTOGRAM_VNEXT_TICKET_GRAPH.md
Issues #126–#133
labels / wave metadata
```

Tasks:

### LWF-06.01
#126 → STANDARD / clinical-ui / ODG-L1.

### LWF-06.02
#127 → HIGH_RISK / clinical-semantics / ODG-L2.

### LWF-06.03
#128–#131 → STANDARD / clinical-ui / ODG-L3, serial inside one wave.

### LWF-06.04
#132 → Part I regression gate role.

### LWF-06.05
#133 → final evidence/handoff hard-stop role.

### LWF-06.06
Remove unnecessary orchestration/review skill loading from simple implementer briefs.

### LWF-06.07
Rewrite verification to T1/T2/T3.

### LWF-06.08
Re-run complete source requirement coverage.

Acceptance:

```text
missing source requirement IDs = 0
```

---

## Phase 7 — Measured Lean pilot

Pilot target:

```text
Odontogram Part I
```

Record metrics per wave.

Success requires:

1. requirement coverage unchanged
2. no unacceptable CRITICAL/HIGH escape
3. AI polling = 0
4. reviewer invocations per accepted STANDARD ticket decrease
5. broad verification runs per accepted STANDARD ticket decrease
6. PR/CI cycles per accepted requirement decrease
7. rework does not erase savings
8. clinical visual evidence remains complete

If a quality problem appears:

```text
tighten the narrowest responsible gate
```

Do not automatically revert to universal per-ticket ceremony.

---

## Phase 8 — Antigravity/cheaper-lane experiment

Only after Phase 7 passes.

### LWF-08.01
Verify real `agy` write capability.

### LWF-08.02
Obtain required provider/data-sharing authorization.

### LWF-08.03
Pilot FAST tests/docs.

### LWF-08.04
Compare first-pass acceptance with Codex.

### LWF-08.05
Update `.delegate/config.json` only if net efficiency improves.

### LWF-08.06
Keep HIGH_RISK on strong approved lanes.

---

## Phase 9 — Optional DWF-11

Revisit PR #135 only now.

Outcome:

```text
close as unnecessary
OR
rebase as opt-in high-risk debate review
```

Never default-enable debate review.

---

## Phase 10 — Governance freeze

After at least two representative lean waves:

- review FAST file cap
- review STANDARD wave cap
- review model routing
- run skill size/duplication audit
- record measured efficiency
- freeze V2.1
- record DWF-12/DWF-13 lessons

---

# 30. Rollback policy

If lean behavior causes quality regression:

1. keep no-polling
2. keep telemetry
3. keep context-loading improvements
4. keep authenticated GitHub preflight
5. tighten only the failing class
6. escalate that class if needed
7. do not roll back product runtime
8. do not delete traceability

Examples:

```text
FAST presentational UI regresses
→ FAST becomes tests/docs only
→ UI moves to STANDARD

wave 5 too large
→ cap becomes 3

agy causes rework
→ route that class back to Codex
```

---

# 31. Non-negotiable invariants

No efficiency optimization may weaken:

- tenant isolation
- RLS
- RBAC
- auth
- privacy
- financial calculations
- data integrity
- migration safety
- clinical semantics
- protected branch governance
- no-fake-test rule
- no-fake-DONE rule
- requirement coverage
- concurrent-writer worktree isolation

---

# 32. What should become faster

V2.1 should reduce:

- model sessions per micro-task
- reviewer sessions per low/normal-risk ticket
- duplicate policy reads
- duplicate broad local tests
- PR count
- irrelevant CI work on low-risk PRs
- model CI checks
- deployment watching
- context growth
- expensive-model use for deterministic/simple work

---

# 33. What remains intentionally expensive when needed

DENTIX should still spend reasoning/time on:

- tenant isolation
- auth/RBAC
- finance
- migrations
- security
- clinical semantics
- production release
- ambiguous shared contracts

Credit efficiency means spending expensive reasoning where risk exists, not removing safety.

---

# 34. Final target workflow

```text
USER approves product plan
          │
          ▼
CODEX ORCHESTRATOR
  reads authority once
  maps requirements
  classifies mode/risk/waves
          │
          ▼
GITHUB
  issues + dependencies + wave state
          │
          ▼
IMPLEMENTATION
  concurrent writers → isolated worktrees
  serial wave → one worktree / multiple commits
          │
          ▼
T1 where required
          │
          ▼
WAVE GATE
  FAST: mechanical inspection
  STANDARD: one independent wave review
  HIGH_RISK: per-ticket review
          │
          ▼
T2 once at wave boundary
          │
          ▼
WAVE PR / HIGH-RISK PR
          │
          ▼
agent:awaiting-ci
AI MODEL STOPS
          │
          ▼
GITHUB ACTIONS
  selective PR gates by proven scope/risk
  full gates for HIGH_RISK
          │
          ▼
ci-green / ci-red
          │
          ├── red → one resume → failed logs → debugging skill → minimal fix
          │
          └── green → one resume → integration
          │
          ▼
STAGING PUSH
FULL CI
          │
          ▼
AUTOMATIC STAGING CD
          │
          ▼
USER-GOVERNED PRODUCTION PROMOTION
main
```

---

# 35. Final acceptance statement

V2.1 is accepted only when DENTIX demonstrates:

```text
same requirement completeness
same or better high-severity quality
zero model CI polling
fewer reviewer/model invocations per accepted requirement
fewer duplicated broad verification runs
fewer unnecessary PR/CI cycles
no weakening of HIGH_RISK controls
```

Permanent principle:

> **Use small tickets to control scope.  
> Use risk and wave boundaries to control expensive verification.  
> Use GitHub for persistent coordination.  
> Use AI only where reasoning is valuable.**
