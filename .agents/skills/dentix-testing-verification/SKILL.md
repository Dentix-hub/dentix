---
name: dentix-testing-verification
description: Design or run DENTIX verification for code changes, regressions, CI failures, acceptance criteria, backend tests, frontend checks, Flutter tests, tenant/RBAC coverage, or release-readiness.
---

# DENTIX Testing & Verification Discipline

## Principles of Verification
1. **CI is the Command Source of Truth**: Before running broad verification, inspect `.github/workflows/ci.yml` and relevant package scripts. Active CI configuration is the sole operational source of truth for required commands, coverage flags (`--cov-fail-under`), and thresholds. Never enforce arbitrary universal numbers.
2. **Tier-Aware Verification Cadence**: Execute targeted checks (`T1`) during ticket work; reserve broad verification suites (`T2`/`T3`) for wave/phase gates and CI boundaries.
3. **No Fake Passes**: Every claimed test passage must be backed by executed terminal commands and real exit codes.
4. **Baseline Failure Separation**: Distinguish pre-existing baseline failures from introduced regressions. Never claim pre-existing issues were caused by new changes unless confirmed by evidence.

## Verification Tiers

### `T0` — Development Sanity
Rapid syntax, typecheck, or lint check during active coding. Cheap and non-blocking.

### `T1` — Targeted Ticket Verification
Focused unit/integration tests covering the exact files or functions changed in a ticket. Mandatory for all production code changes and direct regressions before reaching `WAVE_READY`.

### `T2` — Wave / Phase Gate
Subsystem-level lint, test, build, and visual validation executed once at the wave or phase boundary before PR creation or phase completion.

### `T3` — Repository / Protected Integration
Authoritative full-suite CI execution on PRs (risk-appropriate) and protected branch pushes (`staging`/`main`). Governed strictly by active GitHub Actions workflow files.

## Standard Verification Commands

### Backend (Python / Pytest)
```bash
# T1 Targeted test
pytest backend/tests/test_<feature>.py -v

# T2/T3 Full suite with coverage (matches current CI configuration)
pytest backend/tests/ \
  --cov=backend \
  --cov-report=xml \
  --cov-report=term-missing \
  -v \
  --tb=short \
  -x
```

Always consult `.github/workflows/ci.yml` for the current coverage threshold and command line flags.


### Frontend (React / Vitest / Vite)
Run only scripts defined by the current `frontend/package.json`.
```bash
# Run linting
cd frontend && npm run lint

# Run unit and component tests
cd frontend && npm run test

# Run production build check
cd frontend && npm run build
```

### Mobile (Flutter)
When the Flutter SDK and project dependencies are available:
```bash
# Static analysis
flutter analyze

# Widget and unit tests
flutter test
```

## Reporting Format
Always document test results using this standard format:
```text
Verification:
- Command: <exact command line>
- Exit Status: <exit code 0 / non-zero>
- Result Summary: <passed count, skipped count, failure count, execution duration>
- Failures: <list of failures or "None">
- Classification: <New / Pre-existing Baseline>
```
