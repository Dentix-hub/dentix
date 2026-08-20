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

Production PRs must come from `staging`, except an explicitly scoped `hotfix/*` created from current `main` for a production-critical defect.

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

Before a PR may move from `staging` to `main`:

- backend tests and coverage pass;
- security checks pass;
- frontend build and unit tests pass;
- design-system guardrails pass where configured;
- Playwright critical path passes;
- visual regression passes;
- responsive/mobile acceptance passes once the mobile gate is installed;
- staging deployment is healthy;
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

`fix/mobile-ux-responsive-forensic` / PR #22 is preserved temporarily as evidence only. It is not a release candidate and must not be directly merged, rebased-and-merged, or wholesale cherry-picked. Its changes are recovered from current `staging` in smaller scoped PRs and the original PR is closed only after every changed file is classified and accounted for.
