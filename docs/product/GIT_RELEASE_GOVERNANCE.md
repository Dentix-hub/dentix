# Dentix Git and Release Governance

## Permanent branches

- `main` — production only.
- `staging` — shared integration and pre-production validation.

No permanent `develop` branch is part of the current Dentix model.

## Normal promotion path

```text
scoped work branch
  -> pull request to staging
  -> required CI
  -> staging deployment and acceptance
  -> pull request staging -> main
  -> required CI
  -> production deployment
```

Allowed staging work prefixes are `feat/`, `feature/`, `fix/`, `refactor/`, `chore/`, `docs/`, `test/`, and `hotfix/`.

Production PRs normally come from `staging`. Two explicitly scoped exceptions are allowed: `hotfix/*` for a production-critical defect created from current `main`, and `release/*` for a documented reconciliation release created from current `main` when historical branch divergence prevents a safe direct `staging -> main` merge.

## Release reconciliation rule

A `release/*` branch is an exception, not a parallel development path. It may target `main` only when direct `staging -> main` promotion is blocked by proven historical divergence or conflicts.

1. Create `release/<scope>` from the current `main` head.
2. Copy/reconcile only the already validated staging release content; do not use a force merge or history rewrite.
3. Preserve `main`-authoritative infrastructure, especially `.github/workflows/cd.yml`, unless an intentional independently reviewed CD change is part of the release.
4. Verify the release branch is ahead of and not behind current `main` before opening the PR.
5. Require the same complete main-targeted CI suite as a normal staging promotion.
6. Merge only after all required gates pass; then reconcile branch history/cleanup as needed.

A `release/*` branch must never become a long-lived substitute for `staging`.

## Hotfix rule

1. Create `hotfix/<issue>` from current `main`.
2. Make the smallest safe correction.
3. PR `hotfix/<issue>` -> `main` and require normal CI.
4. After production validation, reconcile the same fix back into `staging` immediately.
5. Delete the hotfix branch after both branches contain the fix.

A production-only hotfix must never be left absent from `staging`.

## Pull-request requirements

Repository automation validates the allowed source/target path through `.github/workflows/branch-governance.yml`.

GitHub repository settings/rulesets must additionally enforce on both `main` and `staging`:

- pull request required;
- direct push prohibited;
- force push prohibited;
- branch deletion prohibited;
- required status checks enabled;
- unresolved review conversations block merge;
- the PR revision must be up to date with its base before merge.

The repository workflow is not a substitute for GitHub branch/ruleset protection; settings are the control that actually prevents direct pushes.

## Required release evidence

Before a production PR may merge into `main`:

- backend tests and coverage pass;
- security checks pass;
- frontend build and unit tests pass;
- design-system guardrails pass where configured;
- Playwright critical path passes;
- visual regression passes;
- responsive/mobile acceptance passes once the mobile gate is installed;
- the source release has completed staging deployment/acceptance when applicable;
- representative manual staging QA is complete for user-visible release changes.

## CD workflow authority

GitHub executes `workflow_run` workflows from the repository default branch. Because the default branch is `main`, `main/.github/workflows/cd.yml` is the authoritative CD definition.

The `staging` copy must remain aligned with the authoritative `main` copy so that future staging-to-main promotions do not reintroduce obsolete deployment logic or create merge conflicts.

The current CD path uses Hugging Face content sync for staging and production rather than Git-to-Git history pushes.

## Branch lifecycle

After a PR is merged and its target branch has passed required verification, delete the source branch unless it is a permanent branch or still backs an open PR.

A branch is eligible for cleanup only when all of the following are proven:

- its work is merged or explicitly superseded;
- no open PR depends on it;
- it is not referenced by deployment automation;
- no unique unmerged work remains.

## Mobile forensic exception

`fix/mobile-ux-responsive-forensic` / PR #22 is historical evidence only. It is not a release candidate and must not be directly merged, rebased-and-merged, or wholesale cherry-picked. Its validated replacement was recovered on current staging through scoped changes before production promotion.
