# Dentix — Deployment Guide

> Supporting guide. Current executable deployment truth is `.github/workflows/cd.yml`; environment/branch details are summarized in [`product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md`](product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md).

## Do not duplicate dynamic deployment values

Do not copy secret values, current branch SHAs, external Space identifiers, platform account names, or health URLs into this document. The workflow/environment configuration owns them.

## Required application configuration

`backend/database.py` requires `DATABASE_URL`. Other required/optional application keys are owned by current environment/config definitions and should be read from the repository's env examples/config code rather than a manually maintained table here.

Never commit real secrets.

## Local development

Use `docker-compose.dev.yml` or direct backend/frontend development commands. Apply schema changes only through explicit Alembic migrations when schema work is in scope.

## Staging

Repository-controlled sequence:

1. reviewed code reaches `staging`,
2. `Dentix CI` tests the revision,
3. successful CI triggers the staging job in `Dentix CD`,
4. that exact tested revision is pushed to the configured Hugging Face staging Space,
5. the workflow performs its configured backend health check.

## Production

Repository-controlled sequence:

1. reviewed/promoted code reaches `main`,
2. CI tests it,
3. production CD verifies the tested revision is current `main`,
4. CD creates/pushes a clean tracked-file snapshot to the configured Hugging Face production Space,
5. CD performs its configured production health check.

Production application startup does not perform ad-hoc schema mutation/seeding; migrations are a deployment concern.

`frontend/vercel.json` on `main` is executable frontend routing configuration, including the production API proxy currently committed there. External Vercel/DNS project configuration is outside this document unless represented by repository config.

## Historical instructions

Older DigitalOcean-specific notes and `python scripts/deployment/deploy.py --env ...` commands are retained only as history where they still appear in historical documents. They are not the canonical current deployment procedure.

## Verification before promotion

Use `.github/workflows/ci.yml`, relevant local tests, staging verification, and `.github/workflows/cd.yml` health checks. Do not replace those with copied test counts/thresholds in prose.
