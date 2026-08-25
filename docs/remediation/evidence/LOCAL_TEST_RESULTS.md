# Local Test Results — 2026-08-25

- Backend: `626 passed, 4 skipped, 30 warnings in 139.53s` (630 collected); 65.13% coverage against the 52% CI gate.
- Latest focused migration/RLS/backup/scheduler/database contract set: 22/22 passed before the final full suite.
- Additional focused corrective regression sets: 50/50 and 25/25 passed.
- Frontend: 62 test files / 258 tests passed.
- Frontend ESLint: passed with zero warnings.
- Frontend Vite/PWA production build: passed; 118 precache entries generated.
- Backend Ruff configured gate: `All checks passed!`.

The four backend skips include environment-dependent checks; PostgreSQL-specific execution is separately recorded as not run locally.
