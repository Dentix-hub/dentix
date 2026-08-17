---
name: dentix-testing-verification
description: Design or run DENTIX verification for code changes, regressions, CI failures, acceptance criteria, backend tests, frontend checks, Flutter tests, tenant/RBAC coverage, or release-readiness.
---

# DENTIX Testing & Verification Discipline

## Principles of Verification
1. **CI is the Command Source of Truth**: Before running broad verification, inspect `.github/workflows/ci.yml` and the relevant package scripts. CI configuration is the source of truth for the current required commands and thresholds.
2. **Targeted First, Broad Before Completion**: Execute fast, focused unit/integration tests during development; execute comprehensive verification suites prior to phase completion.
3. **Repository Truth Thresholds**: Respect actual project CI configuration (e.g. backend coverage threshold of 70%). Never enforce arbitrary universal numbers.
4. **No Fake Passes**: Every claimed test passage must be backed by executed terminal commands and real exit codes.
5. **Baseline Failure Separation**: Distinguish pre-existing baseline failures from introduced regressions. Never claim pre-existing issues were caused by new changes unless confirmed by evidence.

## Standard Verification Commands

### Backend (Python / Pytest)
```bash
# Targeted test
pytest backend/tests/test_<feature>.py -v

# Full suite with coverage (matches current CI)
pytest backend/tests/ \
  --cov=backend \
  --cov-report=xml \
  --cov-report=term-missing \
  --cov-fail-under=70 \
  -v \
  --tb=short \
  -x
```

If `.github/workflows/ci.yml` changes later, follow the current CI file rather than this example.

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
