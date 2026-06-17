# DENTIX Production Roadmap Prompt
> ابعت المحتوى ده كله لـ Hermes في Telegram

---

You are the lead architect for DENTIX. You have completed a full production readiness audit (score: 45/90 — 🔴 NOT READY). Your job now is to produce a complete, ordered implementation plan to bring DENTIX to production — without breaking any existing working functionality.

Load and apply the dentix-architect skill before starting.
Project path: [PROJECT_PATH]

---

## What's Already Working — DO NOT TOUCH
These are verified working features. Every fix must preserve them:
- Multi-tenant context isolation (ContextVar + middleware + event listener)
- RBAC with 10 roles + require_permission dependency
- Single-session policy (JWT sid + active_session_id on User model)
- Refresh token rotation with DB-backed session invalidation
- Soft delete across all models (is_deleted, deleted_at)
- Encrypted PII fields (Patient phone, email, address via EncryptedString)
- Outbox pattern (DomainEvent model + event_processor worker)
- Subscription lifecycle with grace period + auto-suspend
- Frontend RTL support (document.dir + i18n detection)
- Structured logging with trace IDs + correlation middleware
- Health checks in Dockerfile (/api/v1/health)
- Alembic migrations with pre-flight validation
- Prometheus instrumentation
- Security headers middleware (CSP, X-Frame-Options, HSTS)
- Pagination utility already exists at backend/core/pagination.py

---

## Known Issues From Audit (verified from actual files)

### CRITICAL
- C1: All DB ops use db.query() 1.x sync style across all 8 CRUD files + routers
- C2: No PostgreSQL RLS — only app-level event listener in core/tenant_scope.py
- C3: Celery in backend/core/celery_app.py + backend/workers/*.py (raw asyncio loops)
- C4: StatCard Tailwind purge bug — colorMap dynamic classes purged in production build
- C5: test_tenant_isolation.py + test_tenant_isolation_complete.py both 0 bytes (empty)

### HIGH
- H1: All 35+ routers use sync get_db instead of get_async_db
- H2: Frontend sessionStorage token storage in frontend/src/utils.js lines 21-39
- H3: ACCESS_TOKEN_EXPIRE_MINUTES=60 in .env.example line 65 (should be 15)
- H4: Refresh token rotation not enforced globally (only in /refresh endpoint)
- H5: console.log/console.error in 30+ frontend components
- H6: List endpoints missing pagination (pagination.py exists but not applied)

### MEDIUM
- M1: No rate limiting on /refresh, /login/2fa, /register (only /token has it)
- M2: CORS wildcard in dev — verify ENVIRONMENT=production is set in prod
- M3: Hardcoded Arabic strings in .jsx files (should use i18n keys)
- M4: No ErrorBoundary on data-fetching components
- M5: datadog/agent:latest in docker-compose.yml line 153
- M6: Postgres port possibly exposed publicly in docker-compose.yml
- M7: No Docker resource limits (memory/CPU) on any service

### QUICK WINS
- Remove ENVIRONMENT=production default from .env.example
- Add DEBUG=False to .env.example
- Add safelist to tailwind.config.js for StatCard colors
- Delete empty test files to avoid false coverage reporting

---

## Deliverable: DENTIX Production Roadmap

Produce this exact document structure:

---

# DENTIX — Road to Production
**Audit score**: 45/90 → Target: 80+/90
**Strategy**: Zero breaking changes — incremental migration

---

## Phase Dependency Map
Show which phases block others. Format:
Phase 2 (DB Models) → must complete before → Phase 3 (Async CRUD) → before → Phase 4 (Routers)
Phase 5 (Frontend) → fully parallel, no dependencies
etc.

---

## PHASE 0 — Quick Wins (Day 1, ~3 hours total)
### Goal: Zero-risk improvements with immediate impact

**Task 0.1 — Fix .env.example**
- Risk: 🟢 LOW
- Current: [read .env.example and quote exact lines]
- Fix: [show exact corrected content]
- Verification: grep -n "ENVIRONMENT\|DEBUG" .env.example
- Time: 10 min

**Task 0.2 — Fix StatCard Tailwind Safelist**
- Risk: 🟢 LOW
- File: frontend/tailwind.config.js
- Current: [read file and quote current safelist or lack thereof]
- Fix: Add complete safelist for all StatCard colorMap variants:
```js
safelist: [
  'bg-indigo-50', 'dark:bg-indigo-900/20', 'text-indigo-600', 'dark:text-indigo-400',
  'bg-emerald-50', 'dark:bg-emerald-900/20', 'text-emerald-600', 'dark:text-emerald-400',
  'bg-amber-50', 'dark:bg-amber-900/20', 'text-amber-600', 'dark:text-amber-400',
  'bg-rose-50', 'dark:bg-rose-900/20', 'text-rose-600', 'dark:text-rose-400',
  'bg-sky-50', 'dark:bg-sky-900/20', 'text-sky-600', 'dark:text-sky-400',
  'bg-violet-50', 'dark:bg-violet-900/20', 'text-violet-600', 'dark:text-violet-400',
]
```
- Verification: npm run build → inspect dist/assets/*.css for bg-indigo-50
- Rollback: remove safelist array
- Time: 20 min

**Task 0.3 — Pin Docker Image Versions**
- Risk: 🟢 LOW
- File: docker-compose.yml line 153
- Current: datadog/agent:latest
- Fix: datadog/agent:7.58.0 (verify latest stable first)
- Time: 10 min

**Task 0.4 — Fix Postgres Port Exposure**
- Risk: 🟢 LOW
- File: docker-compose.yml
- Current: [read and quote postgres service ports section]
- Fix: Remove public port mapping, internal network only
- Time: 10 min

**Task 0.5 — Remove Empty Test Files**
- Risk: 🟢 LOW
- Delete: backend/tests/test_tenant_isolation.py (0 bytes)
- Delete: backend/tests/test_tenant_isolation_complete.py (0 bytes)
- We will recreate these properly in Phase 6
- Time: 2 min

---

## PHASE 1 — Auth Hardening (Days 1-2)
### Goal: Fix auth without disrupting existing sessions

**Task 1.1 — Reduce Access Token Expiry**
- Risk: 🟢 LOW
- 🔄 INCREMENTAL SAFE
- File: .env.example line 65 + production .env
- Current: ACCESS_TOKEN_EXPIRE_MINUTES=60
- Fix: ACCESS_TOKEN_EXPIRE_MINUTES=15
- Impact on users: next token refresh will use 15min (transparent)
- Verification: decode a new JWT, check exp - iat = 900 seconds
- Time: 5 min

**Task 1.2 — Migrate Token Storage to httpOnly Cookies**
- Risk: 🟡 MEDIUM
- ⚠️ Grace period: accept both sessionStorage token AND cookie for 7 days, then remove sessionStorage fallback
- File: frontend/src/utils.js lines 21-39
- Current: [read and quote getToken/setToken/removeToken functions]
- Step 1: Update API calls to send credentials: 'include'
- Step 2: Verify backend already sets httpOnly cookie on login (read login.py)
- Step 3: Add fallback — if no cookie, check sessionStorage (grace period)
- Step 4: After 7 days in production — remove sessionStorage fallback
- Verification: login → DevTools → Application → Cookies → verify httpOnly flag
- Rollback: revert utils.js, keep sessionStorage path
- Time: 2 hours

**Task 1.3 — Add Rate Limiting to All Auth Endpoints**
- Risk: 🟢 LOW
- Files: backend/routers/auth/login.py
- Current: only /token has @limiter.limit("20/minute")
- Fix: add @limiter.limit("10/minute") to /refresh and /register, @limiter.limit("5/minute") to /login/2fa
- Verification: curl -X POST /refresh 11 times → 12th should return 429
- Time: 30 min

**Task 1.4 — Remove Console Statements from Frontend**
- Risk: 🟢 LOW
- Create: frontend/src/utils/logger.js
```js
const isProd = import.meta.env.PROD;
export const logger = {
  log: (...args) => !isProd && console.log(...args),
  error: (...args) => !isProd && console.error(...args),
};
```
- Then replace all console.log/error with logger.log/error across 30+ files
- Verification: npm run build → grep console dist/assets/*.js → should be empty
- Time: 1 hour

---

## PHASE 2 — Database: SQLAlchemy 2.0 Async Migration (Days 2-5)
### Goal: Migrate from sync 1.x to async 2.0 — one file at a time
### Strategy: Dual engine period — keep sync engine alive until all files migrated

**Task 2.1 — Add Async Engine (Dual Engine Start)**
- Risk: 🟡 MEDIUM
- 🔄 INCREMENTAL SAFE — old sync engine stays untouched
- File: backend/core/database.py
- Current: [read and quote current engine setup]
- Fix: add alongside existing:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

async_engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
```
- Add to .env: ASYNC_DATABASE_URL=postgresql+asyncpg://... (same DB, different driver)
- Verification: import async_engine in Python shell, await async_engine.connect()
- Time: 1 hour

**Task 2.2 — Migrate Models to SQLAlchemy 2.0 Mapped[] Style**
- Risk: 🟡 MEDIUM
- 🔄 INCREMENTAL SAFE — Mapped[] is backward compatible
- For each model file:
```python
# BEFORE
id = Column(Integer, primary_key=True)
name = Column(String, nullable=False)

# AFTER
id: Mapped[int] = mapped_column(primary_key=True)
name: Mapped[str] = mapped_column(nullable=False)
```
- Do NOT change relationships yet — do those in Task 2.5
- Verification: alembic revision --autogenerate → should produce empty migration
- Time: 3 hours

**Task 2.3 — Add DelfinaCare/rls Policies to All Tenant Models**
- Risk: 🟡 MEDIUM
- 🔄 INCREMENTAL SAFE — policies added to models, migration applied separately
- Install: pip install rls
- For each model with tenant_id:
```python
from rls.declarative import Permissive, ConditionArg, Command

class Patient(Base):
    __rls_policies__ = [
        Permissive(
            condition_args=[ConditionArg("tenant_id", Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
```
- Update Alembic env.py:
```python
from rls import register
register.base_wrapper(Base)
```
- Generate migration: alembic revision --autogenerate -m "add_rls_policies"
- ⚠️ DO NOT apply migration yet — verify in Task 2.4 first
- Time: 2 hours

**Task 2.4 — Test RLS Migration on Staging Before Applying**
- Risk: 🔴 HIGH — irreversible schema change
- ⏸️ TEST ON STAGING FIRST
- Copy production DB to staging, apply migration, run:
```sql
SET app.current_tenant = '1';
SELECT count(*) FROM patients; -- must show only tenant 1 count

SET app.current_tenant = '2';
SELECT count(*) FROM patients; -- must show only tenant 2 count

RESET app.current_tenant;
SELECT count(*) FROM patients; -- must show 0 (no bypass possible)
```
- Only proceed to production after staging passes all 3 queries
- Rollback: alembic downgrade -1
- Time: 2 hours

**Task 2.5 — Migrate CRUD Files to Async (One File at a Time)**
- Risk: 🟡 MEDIUM
- 🔄 INCREMENTAL SAFE — one file, test, then next
- Order: start with smallest CRUD file, end with patients (largest)
- For each file:
```python
# BEFORE
def get_patient(db: Session, patient_id: int):
    return db.query(Patient).filter(Patient.id == patient_id).first()

# AFTER
async def get_patient(session: AsyncSession, patient_id: int):
    result = await session.execute(
        select(Patient)
        .options(selectinload(Patient.appointments))
        .where(Patient.id == patient_id)
    )
    return result.scalar_one_or_none()
```
- Add selectinload/joinedload on ALL relationships at this step (fixes N+1 simultaneously)
- Verification after each file: run existing tests + manual test the feature
- Time: 4-6 hours

**Task 2.6 — Migrate All 35+ Routers to get_async_db**
- Risk: 🟡 MEDIUM
- 🔄 INCREMENTAL SAFE — router by router
- For each router:
```python
# BEFORE
db: Session = Depends(get_db)

# AFTER
session: AsyncSession = Depends(get_async_db)
```
- Convert all def endpoints to async def, await all CRUD calls
- Verification: run affected routes after each router change
- Time: 4-5 hours

**Task 2.7 — Remove Sync Engine (End of Dual Engine Period)**
- Risk: 🟢 LOW (at this point all code is async)
- Only after ALL routers and CRUD files migrated
- Remove from database.py: engine, SessionLocal, get_db
- Remove from requirements.txt: psycopg2-binary → replaced by asyncpg
- Verification: grep -r "get_db\b" backend/ → must return 0 results
- Time: 30 min

---

## PHASE 3 — Background Jobs: Celery → Prefect (Days 5-7)
### Goal: Replace Celery without losing any scheduled task
### Strategy: Map every Celery task → Prefect flow, run both until verified

**Task 3.1 — Inventory All Celery Tasks**
- Read backend/core/celery_app.py and ALL files in backend/workers/
- For each task document: name | schedule | what it does | Prefect flow name
- Do not skip any task — missing one means silent data loss

**Task 3.2 — Install Prefect and Create Flows**
- Install: pip install "prefect>=3.0"
- For each Celery task, create Prefect equivalent:
```python
from prefect import flow, task

@task(retries=3, retry_delay_seconds=60, log_prints=True)
async def process_outbox_events():
    async with AsyncSessionLocal() as session:
        # existing logic, now using async session
        pass

@flow(name="outbox-processor")
async def outbox_processor_flow():
    await process_outbox_events()
```
- Keep Celery running during this phase

**Task 3.3 — Test Each Prefect Flow Independently**
- Run each flow manually and verify output matches Celery behavior
- Check Prefect UI for run history and logs

**Task 3.4 — Switch Scheduler to Prefect (One Flow at a Time)**
- Disable Celery beat entry → enable Prefect equivalent → monitor 24 hours → next
- Rollback: re-enable Celery beat entry if Prefect flow fails

**Task 3.5 — Remove Celery**
- Only after ALL flows verified for 48 hours
- Remove: celery from requirements.txt, backend/core/celery_app.py
- Remove: CELERY_* env vars from .env.example
- Time: 30 min

---

## PHASE 4 — API Quality (Days 6-8, parallel with Phase 3)
### Goal: Fix endpoint issues without changing API contracts

**Task 4.1 — Apply Pagination to All List Endpoints**
- Find all endpoints returning .all() without pagination:
  grep -rn "\.all()" backend/routers/
- pagination.py already exists — apply CursorParams to each list endpoint
- Non-breaking: add limit/offset params with defaults (limit=50)

**Task 4.2 — Fix CORS for Production**
- File: backend/core/config.py
- Verify get_allow_origin_regex() returns None when ENVIRONMENT=production
- Add explicit allowed origins list for production domain

**Task 4.3 — Add Docker Resource Limits**
- File: docker-compose.yml
- Add to each service:
```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
```

---

## PHASE 5 — Frontend Fixes (Days 3-7, fully parallel)
### Goal: Fix RTL, components, error handling

**Task 5.1 — Audit and Fix Physical CSS Properties**
- Run: grep -rn "padding-left\|padding-right\|margin-left\|margin-right\|border-left\|border-right" frontend/src/
- Replace each with logical equivalent:
  padding-left → padding-inline-start
  padding-right → padding-inline-end
  margin-left → margin-inline-start
  margin-right → margin-inline-end
  border-left → border-inline-start
  border-right → border-inline-end
- Verification: switch browser to RTL → all layouts must mirror correctly

**Task 5.2 — Fix React Router Nesting**
- Read current router setup (src/App.jsx or src/router/)
- Show current broken structure → corrected structure
- Verification: navigate all main routes, check no 404 or blank pages

**Task 5.3 — Add Error Boundaries**
- Create: frontend/src/components/ErrorBoundary.jsx
- Wrap all page-level components
- Add react-hot-toast notification on query error

**Task 5.4 — Fix TanStack Query Mutations Missing invalidateQueries**
- Find: grep -rn "useMutation" frontend/src/ | grep -v "invalidateQueries"
- Add onSuccess → queryClient.invalidateQueries() to each

---

## PHASE 6 — Testing (Days 8-10)
### Goal: Minimum viable test coverage to guarantee SaaS safety

**Task 6.1 — Tenant Isolation Tests (CRITICAL — do first)**
- File: backend/tests/test_tenant_isolation.py (recreate from scratch)
```python
async def test_tenant_a_cannot_read_tenant_b_patients()
async def test_tenant_a_cannot_update_tenant_b_records()
async def test_rls_policy_exists_in_database()
async def test_admin_can_see_all_tenants()
async def test_clinic_owner_sees_only_own_clinic()
async def test_direct_sql_respects_rls()  # bypass ORM, test raw SQL
```
- These tests must FAIL before Phase 2.4, then PASS after

**Task 6.2 — Auth Tests**
```python
async def test_expired_access_token_rejected()
async def test_wrong_role_blocked_by_rbac()
async def test_token_blacklist_after_logout()
async def test_access_token_expires_in_15_minutes()
async def test_refresh_token_rotation()
```

**Task 6.3 — Core CRUD Tests**
```python
async def test_create_patient_assigns_correct_tenant()
async def test_appointment_crud_complete_lifecycle()
async def test_soft_delete_hides_record()
async def test_encrypted_pii_not_stored_plaintext()
```

---

## Pre-Production Checklist

**Database**
- [ ] RLS migration applied and verified on staging
- [ ] Tenant isolation tests passing (Task 6.1 — all 6 tests green)
- [ ] All tenant_id columns have indexes
- [ ] No N+1 queries (enable query logging, count queries per request)

**Auth**
- [ ] Access token expiry = 15 min
- [ ] Tokens in httpOnly cookies only (sessionStorage fallback removed)
- [ ] Rate limiting on all auth endpoints
- [ ] Refresh token rotation verified end-to-end

**Frontend**
- [ ] npm run build completes with 0 errors
- [ ] StatCard colors visible in production build (grep dist for bg-indigo-50)
- [ ] No console.* in production bundle
- [ ] RTL verified on Arabic content

**Infrastructure**
- [ ] No :latest Docker image tags
- [ ] Postgres port NOT exposed publicly
- [ ] Docker resource limits set on all services
- [ ] ENVIRONMENT=production set explicitly

**Security**
- [ ] git log --all --full-history -- "*.env" → no secrets found
- [ ] CORS restricted to production domain only
- [ ] Security headers verified at securityheaders.com

---

## Summary Timeline

| Day | Work |
|-----|------|
| Day 1 | Phase 0 (quick wins) + Phase 1 (auth hardening) + Phase 5 start |
| Days 2-3 | Phase 2: async engine + models + RLS policies |
| Day 4 | Phase 2: RLS staging test + async CRUD migration |
| Day 5 | Phase 2: router migration + remove sync engine |
| Days 6-7 | Phase 3: Celery → Prefect + Phase 4: API quality |
| Days 8-10 | Phase 6: tests |
| Day 10 | Pre-production checklist + staging full smoke test |

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| RLS migration locks out data | Test on staging copy first — always |
| Async migration breaks a route | Migrate one file at a time, test after each |
| Celery task lost in migration | Inventory ALL tasks before touching anything |
| Token migration logs out users | 7-day grace period with sessionStorage fallback |
| React Router fix breaks navigation | Test all routes after change |

---

## Rules for This Plan
- Read every file mentioned before writing its fix
- Quote exact current code, then show exact replacement code
- Never say "update X" without showing full before/after
- Flag every place where a DB migration is required
- After completing the full plan, ask: "أبدأ بـ Phase 0 دلوقتي؟"
