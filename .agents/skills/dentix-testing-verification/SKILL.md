---
name: dentix-testing-verification
description: Design or run DENTIX verification for code changes, regressions, CI failures, acceptance criteria, backend tests, frontend checks, Flutter tests, tenant/RBAC coverage, or release-readiness.
---

# DENTIX Testing & Verification Discipline

## Principles of Verification
1. **CI is the Command Source of Truth**: Before running broad verification, inspect `.github/workflows/ci.yml` and relevant package scripts. Active CI configuration is the sole operational source of truth for required commands, coverage flags (`--cov-fail-under`), and thresholds.
2. **Targeted Verification Cadence**: Run focused unit/integration tests during development. Run broader subsystem checks before PR. CI serves as the authoritative integration gate.
3. **No Fake Passes**: Every claimed test passage must be backed by executed terminal commands and real exit codes.
4. **Baseline Failure Separation**: Distinguish pre-existing baseline failures from introduced regressions.

## Standard Verification Commands

### Backend (Python / Pytest)
```bash
# Targeted test for active feature
pytest backend/tests/test_<feature>.py -v

# Full suite with coverage (matches active CI configuration)
pytest backend/tests/ \
  --cov=backend \
  --cov-report=xml \
  --cov-report=term-missing \
  -v \
  --tb=short \
  -x
```

Always consult `.github/workflows/ci.yml` for current coverage thresholds and active flags.

### Frontend (React / Vitest / Vite)
```bash
# Run linting
cd frontend && npm run lint

# Run unit and component tests
cd frontend && npm run test

# Run production build check
cd frontend && npm run build
```

### Mobile (Flutter)
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
