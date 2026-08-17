# Dentix Documentation Classification

This classification prevents plans, snapshots, and old infrastructure notes from being mistaken for current product truth. It does not delete historical evidence.

## CANONICAL

- `/PROJECT_TRUTH.md` — entry point and precedence.
- `docs/product/TRUTH_SOURCE_MAP.md` — source/conflict index.
- `docs/product/MODULE_REGISTRY.md` — current module navigation inventory.
- `docs/product/CURRENT_PRODUCT_CAPABILITIES.md` — verified capability boundary.
- `docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md` — human-readable deployment/environment map that points to executable config.
- `PROJECT_STANDARDS.md` — governance where it does not conflict with executable truth.
- `WORKFLOW_RULES.md` — operational workflow rules after Plan 01 correction; executable Git/CI/CD state still wins.

## ACTIVE_SUPPORTING

These are useful but are not allowed to override canonical/executable truth:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docs/API.md`
- `docs/FINANCE_METRIC_CONTRACT.md`
- `docs/AI_AGENT_STACK.md`
- `docs/AI_GOVERNANCE_RULES.md`
- `docs/GLOBAL_RELEASE_GATE.md`
- `docs/MODULE_CONVENTIONS.md`
- `docs/E2E_TEST_PLAN.md`
- `docs/05-local-testing-guide.md`
- `frontend/DESIGN.md`

## HISTORICAL

Historical material is evidence of intent, implementation, or a point-in-time state. It must not be treated as current truth without re-validation.

- `DENTIX_MEMORY.md` — append-only project history/decision log; now explicitly non-canonical.
- `docs/CURRENT_STATE.md` — Finance V2 release snapshot tied to an earlier integration/PR state.
- `docs/IMPLEMENTATION_LEDGER.md`
- `docs/EXECUTION_MANIFEST.json`
- `docs/EXECUTION_PROTOCOL.md` when describing a completed execution package.
- `docs/PHASE_*.md`
- `docs/PLAN-*.md` and `docs/PLAN_*.md`
- `docs/GEMINI_*.md`
- `docs/01-executive-summary.md`, `docs/02-week1-security.md`, `docs/03-week2-3-performance-ux.md`, `docs/04-inventory-enhancement.md`
- implementation/reviewer prompts and completed repair/hardening plans unless a current canonical file explicitly adopts them.

## ARCHIVED

`docs/archive/` is reserved for documents that are both historical/obsolete and safe to move after reference checks. No bulk move was performed in Plan 01 because a complete safe reference graph was not established. See `docs/archive/README.md`.

## OBSOLETE statements / instructions identified

The following statements are known not to represent current repository-controlled truth and must not be followed as operational instructions:

- DigitalOcean as the current Dentix production deployment target in the old project memory.
- The old `python scripts/deployment/deploy.py --env ...` commands as the canonical deployment mechanism.
- `docker-compose.yml` described as a current DigitalOcean-specific production deployment source.
- Sentry described as the current monitoring implementation when `backend/main.py` explicitly marks it removed/replaced by internal logging.
- ORM tenant filtering described as the complete isolation mechanism; PostgreSQL RLS is also present for registered tenant tables.
- A fixed CI coverage threshold copied into prose when `.github/workflows/ci.yml` owns the value.
- `develop` assumed to be an active branch: no active `develop` branch was found during this audit even though CI still contains a `develop` trigger.

## Stale/duplicate guidance findings

1. Infrastructure truth had been duplicated across `DENTIX_MEMORY.md`, `WORKFLOW_RULES.md`, README, deployment docs, and workflows.
2. Architecture truth had been duplicated between README, `docs/ARCHITECTURE.md`, and runtime code, causing isolation/session drift.
3. Finance implementation plans and `docs/CURRENT_STATE.md` can look current despite being checkpoint evidence.
4. Test counts, coverage thresholds, provider names, URLs, and branch heads are dynamic and should live in executable sources.

## Lifecycle rule

Before moving a historical file to `docs/archive/`:

1. Search inbound references.
2. Ensure a canonical replacement exists.
3. Repair active links.
4. Preserve useful provenance/date/status.
5. Move; do not delete unless there is no evidentiary value and removal is explicitly approved.
