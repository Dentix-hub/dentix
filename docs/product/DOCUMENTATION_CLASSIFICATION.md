# Dentix Documentation Classification

This classification prevents plans, snapshots, and old infrastructure notes from being mistaken for current product truth. It does not delete historical evidence.

## CANONICAL

- `/PROJECT_TRUTH.md` — entry point and precedence.
- `docs/product/TRUTH_SOURCE_MAP.md` — source/conflict index.
- `docs/product/MODULE_REGISTRY.md` — current module navigation inventory.
- `docs/product/CURRENT_PRODUCT_CAPABILITIES.md` — verified capability boundary.
- `docs/product/ENVIRONMENT_AND_DEPLOYMENT_TRUTH.md` — human-readable deployment/environment map that points to executable config.
- `docs/product/DEPLOYMENT_ARTIFACT_DISPOSITION.md` — active/retired deployment artifact decisions.
- `docs/product/PRODUCTION_ARCHITECTURE_NORMALIZATION_STATUS.md` — architecture-normalization closeout state and unresolved release blockers.
- `PROJECT_STANDARDS.md` — governance where it does not conflict with executable truth.
- `WORKFLOW_RULES.md` — operational workflow rules; executable Git/CI/CD state still wins.

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
- `docs/product/GIT_RELEASE_GOVERNANCE.md`
- `frontend/DESIGN.md`

## HISTORICAL

Historical material is evidence of intent, implementation, or a point-in-time state. It must not be treated as current truth without re-validation.

- `DENTIX_MEMORY.md` — append-only project history/decision log; explicitly non-canonical.
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

`docs/archive/` is reserved for documents that are both historical/obsolete and safe to move after reference checks. No bulk move is implied by this classification. See `docs/archive/README.md`.

## OBSOLETE statements / instructions identified

The following statements are known not to represent current repository-controlled truth and must not be followed as operational instructions:

- DigitalOcean as the current Dentix production deployment target.
- The retired `python scripts/deployment/deploy.py --env ...` commands as the canonical deployment mechanism.
- `docker-compose.yml`, `docker-compose.production.yml`, Caddy, or `backend/Dockerfile` described as current production deployment sources.
- GHCR publication described as a required deployment distribution path; current CD synchronizes tested source to Hugging Face and CI retains image build validation only.
- `requirements.txt` or backend requirements compatibility files described as canonical dependency inputs; canonical Python dependencies are `pyproject.toml` + `uv.lock`.
- Sentry described as the current monitoring implementation when runtime code marks it removed/replaced by internal logging.
- ORM tenant filtering described as the complete isolation mechanism; PostgreSQL RLS and dedicated adversarial isolation tests are also part of the current contract.
- A fixed CI coverage threshold copied into prose when `.github/workflows/ci.yml` owns the value.
- `develop` assumed to be an active permanent branch or current CI target. Current CI targets `main` and `staging`.
- A workflow-only branch-governance check described as equivalent to GitHub platform branch/ruleset enforcement. Platform settings must be verified separately.

## Stale/duplicate guidance findings

1. Infrastructure truth was duplicated across `DENTIX_MEMORY.md`, `WORKFLOW_RULES.md`, README, deployment docs, and workflows; current canonical docs now point to executable deployment truth and the artifact disposition record.
2. Architecture truth was duplicated between README, `docs/ARCHITECTURE.md`, and runtime code, causing isolation/session drift; runtime + executable verification remain authoritative.
3. Finance implementation plans and `docs/CURRENT_STATE.md` can look current despite being checkpoint evidence.
4. Test counts, coverage thresholds, package versions, provider URLs, branch heads, and other mutable values should live in executable sources or point-in-time evidence rather than long-lived prose.
5. Security checkpoint PRs are evidence, not a substitute for resolving their blockers. A historical secret finding remains unresolved until key topology, rotation/revocation, and history handling are explicitly proven.

## Lifecycle rule

Before moving a historical file to `docs/archive/`:

1. Search inbound references.
2. Ensure a canonical replacement exists.
3. Repair active links.
4. Preserve useful provenance/date/status.
5. Move; do not delete unless there is no evidentiary value and removal is explicitly approved.
