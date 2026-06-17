# DENTIX — Final Production Review Prompt
> للـ Claude Opus 4.6 — مراجعة شاملة بعد اكتمال كل الـ phases

---

You are a senior principal engineer conducting a final production readiness
review for DENTIX — a multi-tenant SaaS dental clinic management platform
targeting the Egyptian/MENA dental market.

Project path: /c/Users/es/DENTIX

---

## Background: What Was Done

The following work was completed across multiple sessions:

### Audit Result (starting point)
Score: 45/90 — 🔴 NOT READY

### Changes Implemented

**Phase 0 — Quick Wins**
- .env.example cleaned (ENVIRONMENT, DEBUG fixed)
- tailwind.config.js: safelist added for StatCard color variants
- docker-compose.yml: image versions pinned, postgres port removed from public
- Empty test files deleted

**Phase 1 — Auth Hardening**
- ACCESS_TOKEN_EXPIRE_MINUTES: 60 → 15
- Token storage: sessionStorage → httpOnly cookies with /api/auth/session endpoint
- Zustand: in-memory only, splash screen on page refresh
- Cookie settings: HttpOnly=True, Secure=True, SameSite=Lax
- 401 handling: try refresh first, then logout
- Rate limiting added to: /refresh, /register, /login/2fa
- frontend/src/utils/logger.js created (env-based, no remote calls)
- All console.log/error replaced with logger utility

**Phase 2 — SQLAlchemy 2.0 Async Migration**
- Dual async engine added to backend/core/database.py
- ASYNC_DATABASE_URL added (postgresql+asyncpg://)
- All 13 model files migrated to Mapped[] style:
  base.py, user.py, patient.py, tenant.py, clinical.py, financial.py,
  inventory.py, medication.py, price_list.py, security_event.py,
  system.py, domain_event.py, ai_audit.py
- DelfinaCare/rls __rls_policies__ added to all tenant-scoped models
- alembic/env.py updated with register.base_wrapper(Base)
- RLS migration generated and tested on staging
- All 8 CRUD files migrated to async select() + await session.execute()
- All relationships: selectinload/joinedload added (N+1 fixed)
- All 35+ routers migrated to AsyncSession + get_async_db
- Sync engine removed (engine, SessionLocal, get_db gone)
- psycopg2-binary removed, asyncpg added

**Phase 2 — Additional (discovered during implementation)**
- AI/RAG tests: MockKnowledgeStore forced via conftest.py (autouse)
  placed at AI tests folder level
- MockKnowledgeStore: returns [] for similarity_search, True for insert
- backup_service.py: pg_dump via asyncio subprocess, AUTOCOMMIT pool,
  raises RuntimeError if SQLite detected
- seeding.py: PostgreSQL advisory lock (pg_try_advisory_xact_lock(12345))
  prevents concurrent seeding in multi-replica deployments
- main.py lifespan: IntegrityError → skip+warn, connection errors → raise,
  other errors → warn+continue

**Phase 3 — Celery → Prefect**
- All Celery tasks inventoried and mapped to Prefect flows
- All workers rewritten as @flow/@task with retries=3
- celery removed from requirements.txt
- backend/core/celery_app.py deleted
- CELERY_* vars removed from .env.example

**Phase 4 — API Quality**
- CursorParams applied to all list endpoints (pagination.py already existed)
- CORS: restricted to production domain, ENVIRONMENT=production verified
- Docker resource limits added to all services:
  backend: 512M / 0.75 cpu
  postgres: 1G / 1.0 cpu
  redis: 256M / 0.25 cpu
  prefect worker: 512M / 0.5 cpu
  nginx: 128M / 0.25 cpu

**Phase 5 — Frontend**
- All physical CSS → logical properties
  (padding-left→inline-start, margin-right→inline-end, etc.)
- React Router nesting fixed
- ErrorBoundary.jsx created, wrapping all page-level components
- All useMutation: onSuccess → queryClient.invalidateQueries() added
- /api/auth/session endpoint integrated for auth state on refresh
- Splash screen: DENTIX logo + spinner while session loads

**Phase 6 — Testing**
- test_tenant_isolation.py: 6 tests (was 0 bytes)
- test_auth.py: 5 tests
- test_crud.py: 4 tests
- test_security_phase4.py: fixed User.email NOT NULL constraint
- test_runner.py + checklist.py: sys.executable replaces hardcoded "python"
- Total: 259 tests — ALL PASSING ✅

---

## Your Job: Final Production Review

Read the actual codebase. Do NOT trust the summary above — verify everything.
Quote exact file paths and line numbers for every finding.

---

## Review Checklist

### 1. Anti-pattern Scan
Run these searches and report exact counts:

```bash
# Must all be 0
grep -rn "db\.query(" backend/ --include="*.py"
grep -rn "Session = Depends(get_db)" backend/ --include="*.py"
grep -rn "from .database import.*get_db\b" backend/ --include="*.py"
grep -rn "console\.log\|console\.error\|console\.warn" frontend/src/
grep -rn "padding-left\|padding-right\|margin-left\|margin-right\|border-left\|border-right" frontend/src/ --include="*.jsx" --include="*.css"
grep -rn "sessionStorage" frontend/src/ --include="*.js" --include="*.jsx"
grep -rn "from celery\|import celery" backend/ --include="*.py"
grep -rn "time\.sleep(" backend/ --include="*.py"
grep -rn "localStorage" frontend/src/ --include="*.js" --include="*.jsx"
grep -rn "SyncSessionLocal\|sync_engine\b" backend/ --include="*.py"
```

Note: alembic/env.py is allowed to have sync engine — exclude it from the scan.

---

### 2. Security Verification

Read each file and verify:

**Auth**
- [ ] backend/.env.example: ACCESS_TOKEN_EXPIRE_MINUTES=15 (not 60)
- [ ] backend/routers/auth/login.py: httpOnly cookie set on login response
- [ ] backend/routers/auth/login.py: SameSite=Lax, Secure=True, HttpOnly=True
- [ ] backend/routers/auth/login.py: /refresh endpoint sets new cookie (not body)
- [ ] backend/routers/auth/login.py: rate limit on /token, /refresh, /register, /login/2fa
- [ ] frontend/src/utils.js: no getToken/setToken using sessionStorage
- [ ] frontend/src/: GET /api/auth/session called on app mount
- [ ] frontend/src/: 401 → try refresh → if fails → logout (not immediate logout)

**Secrets**
- [ ] .gitignore covers: .env, *.pem, *.key, *.p12, __pycache__, node_modules
- [ ] No hardcoded passwords, API keys, or secrets in any .py or .js file
- [ ] SECRET_KEY loaded from environment, not hardcoded

**Endpoints**
- [ ] Every router has auth dependency (require_permission or equivalent)
- [ ] List endpoints return paginated response (not unlimited .all())
- [ ] No endpoint returns data without tenant_id filter

**RLS**
- [ ] __rls_policies__ present on: User, Patient, Appointment, Treatment,
      Payment, LabOrder, StockItem, Material, Warehouse, InsuranceProvider,
      PriceList, AILog, SecurityEvent
- [ ] alembic/versions/: migration file exists for RLS policies
- [ ] alembic/env.py: register.base_wrapper(Base) present

---

### 3. Protected Features Verification

Read these files and confirm still intact:

| Feature | File to read | What to verify |
|---------|-------------|----------------|
| Tenant isolation | backend/core/tenant_scope.py | ContextVar + event listener active |
| RBAC | backend/core/permissions.py | require_permission + 10 roles defined |
| Single session | backend/models/user.py | active_session_id field present |
| Soft delete | ALL models | is_deleted + deleted_at on every tenant model |
| Encrypted PII | backend/models/patient.py | EncryptedString on phone, email, address |
| Outbox pattern | backend/models/domain_event.py | DomainEvent model intact |
| Outbox worker | backend/workers/ | Prefect flow processes DomainEvent |
| Subscription | backend/core/ or models/ | grace_period + auto_suspend logic |
| RTL support | frontend/src/ | document.dir set + i18n language detection |
| Trace logging | backend/core/logging.py | trace_id in log entries |
| Health check | backend/Dockerfile | HEALTHCHECK → /api/v1/health |
| Migrations | backend/alembic/env.py | pre-flight validation on startup |
| Prometheus | backend/main.py | metrics endpoint registered |
| Advisory lock | backend/core/seeding.py | pg_try_advisory_xact_lock(12345) |
| Backup | backend/services/backup_service.py | pg_dump async subprocess + AUTOCOMMIT pool |

---

### 4. New Features Correctness Check

Verify these were implemented correctly:

**httpOnly Cookie Flow**
- Read login endpoint: does it set cookie correctly?
- Read /api/auth/session endpoint: does it exist and return {id, name, role, tenant_id}?
- Read frontend app mount: does it call /api/auth/session before rendering?
- Read frontend 401 handler: refresh → retry → logout flow correct?

**Splash Screen**
- Read frontend: isAuthLoading initial state = true?
- Is login page hidden while isAuthLoading = true?
- Is splash screen simple (logo + spinner, no layout/sidebar)?

**Advisory Lock**
- Read seeding.py: is lock_id = 12345 (fixed integer)?
- Is it pg_try_advisory_XACT_lock (not pg_try_advisory_lock)?
- Does non-blocking path log "skipped" without raising?
- Does connection error still bubble up?

**Backup Service**
- Read backup_service.py: SQLite check raises RuntimeError?
- Is pg_dump called via asyncio.create_subprocess_exec?
- Is backup engine using AUTOCOMMIT isolation level?
- Is backup engine a separate pool (pool_size=1, max_overflow=0)?

**MockKnowledgeStore**
- Read conftest.py in AI tests folder: autouse=True fixture?
- Does it mock similarity_search → []?
- Does it mock insert_document → True?
- Is it scoped to AI tests folder only (not global)?

**Prefect Workers**
- Read all files in backend/workers/: are they @flow/@task?
- Do all tasks have retries=3?
- Is there a DomainEvent outbox processing flow?
- No celery imports anywhere in workers/?

---

### 5. Frontend Build Verification

```bash
cd /c/Users/es/DENTIX/frontend
npm run build 2>&1 | tail -20
grep -c "bg-indigo-50" dist/assets/*.css
grep -c "console\." dist/assets/*.js
```

Report:
- Build: success or errors?
- StatCard colors in bundle: yes/no (count of bg-indigo-50 occurrences)
- Console statements in bundle: count (must be 0)

---

### 6. Test Results

```bash
cd /c/Users/es/DENTIX
python -m pytest backend/tests/ -v --tb=short 2>&1 | tail -30
```

Report:
- Total tests: X
- Passed: X
- Failed: X (list any failures with file:line)
- Specifically confirm these pass:
  - test_tenant_isolation.py (6 tests)
  - test_auth.py (5 tests)
  - test_crud.py (4 tests)

---

### 7. Docker Compose Verification

Read docker-compose.yml and verify:

```yaml
# Check each service has:
deploy:
  resources:
    limits:
      memory: [value]
      cpus: '[value]'

# Check postgres service:
# - NO ports: mapping to host (internal only)
# - Has healthcheck defined

# Check all images:
# - NO :latest tags
# - All pinned to specific versions
```

---

## Output Format

# DENTIX Final Production Review
**Date**: 2026-06-15
**Reviewer**: Claude Opus 4.6
**Overall Verdict**: 🟢 READY / 🟡 READY WITH MINOR FIXES / 🔴 NOT READY

---

## Anti-pattern Scan Results
| Pattern | Count | Status |
|---------|-------|--------|
| db.query() remaining | X | ✅/❌ |
| sync get_db remaining | X | ✅/❌ |
| console.log remaining | X | ✅/❌ |
| Physical CSS properties | X | ✅/❌ |
| sessionStorage tokens | X | ✅/❌ |
| localStorage tokens | X | ✅/❌ |
| Celery imports | X | ✅/❌ |
| time.sleep in async | X | ✅/❌ |
| SyncSessionLocal remaining | X | ✅/❌ |

---

## Security Checklist
[each item: ✅ VERIFIED / ❌ FAILED (file:line) / ⚠️ PARTIAL]

---

## Protected Features
[each feature: ✅ INTACT / ❌ BROKEN (file:line) / ⚠️ MODIFIED]

---

## New Features Correctness
[each feature: ✅ CORRECT / ❌ WRONG (file:line + what's wrong + fix)]

---

## Build & Test Results
Build: [result]
StatCard CSS: [result]
Console in bundle: [count]
Tests: [X/259 passing]
Failed tests: [list or "none"]

---

## Docker Compose
[each check: ✅/❌]

---

## Issues Found

### Blocking (must fix before deploy)
**[BLOCK-N]** — [title]
- File: path/to/file line X
- Problem: [description]
- Fix: [exact code]

### Non-blocking (fix post-launch)
**[MINOR-N]** — [title]
- File: path/to/file line X
- Suggestion: [description]

---

## Final Verdict
[2-3 sentences: go/no-go + conditions if any]

---

## Review Rules
- Read actual files — never trust the summary
- Every finding needs file:line reference
- If a file doesn't exist where expected, flag it as MISSING
- If 259 tests pass but you find a logical bug, flag it regardless
- Be skeptical — this is production SaaS with real patient data
