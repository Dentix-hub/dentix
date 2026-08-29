# Dry-run DENTIX agent task

This local example validates that the issue contract is understandable without access to an orchestrator chat. It is not approved implementation work.

## Problem

Frontend contributors need to locate the canonical shared button before proposing a low-risk documentation-only improvement. The current task is inspection only and must not change application files.

## Objective

Identify the canonical shared button component and report its repository path and public props from repository evidence.

## Source spec or plan

`docs/engineering/DENTIX_AI_DEVELOPMENT_WORKFLOW_V2.md` — read-only delegate smoke contract.

## Scope

- Inspect the frontend shared UI structure.
- Identify the canonical button implementation and its exports.
- Return a concise evidence-backed answer.

## Explicit non-goals

- Do not modify any file.
- Do not add a new component or dependency.
- Do not run a write-capable delegate.

## Dependencies

None. This is a read-only inspection with no contract dependency.

## Parallel classification

`PARALLEL_SAFE` because it performs no writes and changes no contract.

## Expected touch surface

- Read only: `frontend/src/shared/ui/` and its import/export references.
- Git-visible writes are forbidden.

## Acceptance criteria

- [ ] The report names the canonical component and exact repository path.
- [ ] The report summarizes its public props from code evidence.
- [ ] `git status --short` is identical before and after the inspection.
- [ ] The delegate returns an understandable exit status and structured result.

## Required DENTIX skills

- `dentix-orchestration`
- `dentix-frontend-react`
- `dentix-testing-verification`

## Risk

`LOW`

## Verification

- Capture `git status --short` before and after.
- Inspect the claimed file and its exports independently.
- Compare the before/after status exactly.

## Completion evidence

- Exact component path and cited code evidence.
- Before/after Git status.
- Delegate exit status.
- Orchestrator confirmation that no tracked or untracked repository file was created.
