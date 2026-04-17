# Dentix — خطة الإصلاح الشاملة

> **الإصدار**: مبنية على فحص الكود الفعلي في v3 (DENTIX.zip + frontend.zip)  
> **المنهجية**: كل مهمة = ملف واحد + commit واحد + نتيجة قابلة للقياس  
> **القاعدة**: لا تنتقل للمرحلة التالية قبل اجتياز كل `✅ تحقق` في المرحلة الحالية

---

## الوضع الحالي — خريطة المشاكل

| الأولوية | المشكلة | الملف | الخطورة |
|----------|---------|-------|---------|
| 🔴 A1 | `insurance.py` — 5 endpoints بدون RBAC | `routers/insurance.py` | ثغرة أمنية |
| 🔴 A2 | `repair.py` — imports داخل functions | `routers/repair.py` | كود هش |
| 🔴 A3 | `system_admin.py` — inline imports متعددة | `routers/system_admin.py` | كود هش |
| 🔴 A4 | Alembic migration لـ `drop_ai_usage_logs` مش مربوط | `alembic/versions/` | DB state خطر |
| 🟡 B1 | `success_response` ناقص في 20+ router | متعدد | inconsistency |
| 🟡 B2 | `admin_tenants.py` — inline datetime import | `routers/admin_tenants.py` | كود هش |
| 🟡 B3 | `password_reset.py` — inline `import os` | `routers/password_reset.py` | كود هش |
| 🔵 C1 | مفيش CI/CD pipeline | `.github/workflows/` | لا automated checks |
| 🔵 C2 | Backend coverage < 75% | `tests/` | لا safety net |
| 🔵 C3 | مفيش E2E tests | `e2e/` | لا regression guard |
| 🔵 C4 | مفيش `docs/` folder | `docs/` | مفيش documentation |

---

## 🔴 المرحلة A — إصلاحات فورية (الأسبوع الأول)

---

### A1 — إصلاح `insurance.py`: إضافة RBAC على 5 endpoints

**المشكلة**: أي مستخدم مسجّل يقدر يعرض ويعدّل insurance providers بدون permission check.

**الملف**: `backend/routers/insurance.py`

```python
# ❌ الكود الحالي (السطر 47–211)
current_user: User = Depends(get_current_user)  # مكرر 5 مرات

# ✅ الإصلاح
# GET endpoints (عرض) → FINANCIAL_READ (receptionist, accountant, manager, admin)
# POST/PUT/PATCH endpoints (تعديل) → SYSTEM_CONFIG (admin فقط)
```

**الخطوات**:

```python
# السطر 49 — get_insurance_providers
current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),

# السطر 87 — get_insurance_provider
current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),

# السطر 127 — create_insurance_provider
current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),

# السطر 177 — update_insurance_provider
current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),

# السطر 211 — deactivate_insurance_provider
current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
```

**تأكد من وجود الـ import في أعلى الملف**:
```python
from ..core.permissions import Permission, require_permission
```

**✅ تحقق**:
```bash
# اختبر يدوياً بـ role = receptionist → يشوف insurance providers
# اختبر بـ role = receptionist → يحاول ينشئ provider → 403
# اختبر بـ role = admin → ينشئ provider → 201
pytest backend/tests/test_rbac_complete.py -v -k "insurance"
```

---

### A2 — إصلاح `repair.py`: تنظيف الـ inline imports

**المشكلة**: `repair.py` عنده imports جوه function bodies في 6 مواضع — ده بيخلي الكود غير قابل للـ profiling والـ testing.

**الملف**: `backend/routers/repair.py`

**الخطوات**:

```python
# ❌ الكود الحالي — imports داخل functions
def some_function():
    from fastapi import HTTPException       # السطر 16
    from sqlalchemy import text, inspect   # السطر 26
    from .. import crud, models, auth      # السطر 185
    from ..services.auth_service import AuthService  # السطر 186
    from .auth.dependencies import validate_password  # السطر 285
    import subprocess                      # السطر 279

# ✅ الإصلاح — انقل كل الـ imports لأعلى الملف
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
import subprocess
import logging

from .. import crud, models, auth
from ..services.auth_service import AuthService
from .auth.dependencies import get_current_user, get_db, validate_password
from ..core.permissions import Permission, require_permission
```

**ملاحظة مهمة**: `repair.py` لازم يكون protected بـ `SYSTEM_CONFIG` permission — تحقق إن كل endpoints فيه محمية:
```python
# كل endpoint في repair.py
current_user = Depends(require_permission(Permission.SYSTEM_CONFIG))
```

**✅ تحقق**:
```bash
python -c "from backend.main import app" && echo "✅ No import errors"
grep -n "^[[:space:]]\+import\|^[[:space:]]\+from " backend/routers/repair.py
# النتيجة المطلوبة: صفر نتائج
```

---

### A3 — إصلاح `system_admin.py`: تنظيف الـ inline imports

**الملف**: `backend/routers/system_admin.py`

```python
# ❌ الكود الحالي
def export_data():
    from ..main import drive_client     # السطر 18
    from datetime import datetime       # السطر 139
    import json                         # السطر 140
    from fastapi.responses import StreamingResponse  # السطر 141
    import subprocess                   # السطر 279

# ✅ الإصلاح
import json
import subprocess
from datetime import datetime
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
```

**أما `from ..main import drive_client`** — ده pattern إشكالي لأنه بيستورد من main.py:
```python
# ✅ البديل الأصح
from backend.core.startup import get_drive_client
# أو
drive_client = None  # يتعمل lazy initialization
try:
    from backend.main import drive_client
except ImportError:
    pass
```

**✅ تحقق**:
```bash
python -c "from backend.routers.system_admin import router" && echo "✅ OK"
```

---

### A4 — ربط Alembic migration لحذف `ai_usage_logs`

**المشكلة**: ملف `drop_ai_usage_logs.py` موجود لكن `down_revision = None` يعني مش مربوط بالـ migration chain — لو شغّلت `alembic upgrade head` هو مش هيتنفذ تلقائياً.

**الملف**: `backend/alembic/versions/drop_ai_usage_logs.py`

**الخطوات**:

**الخطوة 1**: ابحث عن الـ current head:
```bash
cd backend && alembic heads
# مثال: e0eb7ca469b9
```

**الخطوة 2**: عدّل الملف:
```python
# ❌ الحالي
down_revision = None

# ✅ الإصلاح — ضع الـ revision ID بتاع آخر migration
down_revision = 'e0eb7ca469b9'  # ← ضع الـ actual head هنا
```

**الخطوة 3**: اختبر على test database:
```bash
# إنشئ test DB مؤقتة
export DATABASE_URL="sqlite:///./test_migration.db"
alembic upgrade head
alembic current  # يجب أن يظهر drop_ai_usage_logs كـ current
```

**الخطوة 4**: تحقق إن `AIUsageLog = AILog` alias شغّال:
```python
# في Python shell
from backend import models
print(models.AIUsageLog is models.AILog)  # يجب أن يكون True
```

**✅ تحقق**:
```bash
alembic upgrade head
alembic current
# يجب أن يظهر: drop_ai_usage_logs (head)
python -c "from backend import models; assert models.AIUsageLog is models.AILog; print('✅ Alias OK')"
```

---

## 🟡 المرحلة B — تحسينات الكود (الأسبوع الثاني)

---

### B1 — تطبيق `success_response` على الـ routers المتبقية

**المشكلة**: 20+ router لسه بيرجع `JSONResponse` أو `dict` raw بدون standardization. ده بيخلي الـ frontend يتعامل مع response shapes مختلفة.

**الأولوية** (ابدأ بالأهم):

#### B1.1 — `dashboard.py`
```python
# ❌ الحالي
return {"revenue": total, "visits": count, ...}

# ✅ الإصلاح
from ..core.response import success_response
return success_response(data={"revenue": total, "visits": count, ...})
```

#### B1.2 — `notifications.py`
```python
# ❌ الحالي
return JSONResponse(content={"notifications": items})

# ✅ الإصلاح
from ..core.response import success_response, paginated_response
return paginated_response(data=items, total=total_count, page=page, per_page=limit)
```

#### B1.3 — `settings.py`
```python
# ❌ الحالي
return {"message": "Settings updated", "data": updated}

# ✅ الإصلاح
return success_response(data=updated, message="Settings updated")
```

#### B1.4 — `medications.py` + `price_lists.py` + `prescriptions.py`
```python
# Pattern موحّد لكل CRUD:
# GET list   → paginated_response(data=items, total=total)
# GET single → success_response(data=item)
# POST       → success_response(data=created, status_code=201)
# PUT        → success_response(data=updated)
# DELETE     → success_response(data=None, message="Deleted successfully")
```

#### B1.5 — `admin_tenants.py` + `admin_subscriptions.py` + `admin_system.py`
```python
# ✅ نفس الـ pattern
from ..core.response import success_response, error_response
```

**✅ تحقق**:
```bash
# بعد كل router تعدّله، شغّل الـ integration tests
pytest backend/tests/test_api_endpoints.py -v
# وتأكد إن الـ frontend لسه شغال (لو عندك dev server)
```

**ملاحظة Frontend**: لو الـ API interceptor في `frontend/src/api/index.js` بيعمل `response.data` مباشرة، لازم يتعدّل لـ `response.data.data`:
```javascript
// frontend/src/api/index.js
// تحقق إن الـ interceptor بيعمل unwrap للـ data:
api.interceptors.response.use(
  response => response.data?.data ?? response.data,
  error => Promise.reject(error)
);
```

---

### B2 — إصلاح `admin_tenants.py`: inline datetime import

**الملف**: `backend/routers/admin_tenants.py` — السطر 101

```python
# ❌ الحالي (جوه function)
def some_function():
    from datetime import datetime, timezone, timedelta
    ...

# ✅ الإصلاح — انقل لأعلى الملف
from datetime import datetime, timezone, timedelta
```

**✅ تحقق**:
```bash
python -c "from backend.routers.admin_tenants import router" && echo "✅ OK"
grep -n "^[[:space:]]\+from datetime\|^[[:space:]]\+import datetime" backend/routers/admin_tenants.py
# النتيجة المطلوبة: صفر نتائج
```

---

### B3 — إصلاح `password_reset.py`: inline `import os`

**الملف**: `backend/routers/password_reset.py` — السطر 74

```python
# ❌ الحالي
def reset_password():
    import os
    token = os.getenv("RESET_TOKEN_EXPIRE", "24")

# ✅ الإصلاح
import os  # في أعلى الملف
from backend.core.config import settings  # الأفضل — استخدم config object
```

**✅ تحقق**:
```bash
grep -n "^[[:space:]]\+import os" backend/routers/password_reset.py
# النتيجة المطلوبة: صفر نتائج
```

---

### B4 — تحقق نهائي من inline imports في كل الـ routers

```bash
# أمر شامل يظهر كل inline imports في كل الـ routers
grep -rn "^[[:space:]]\+import \|^[[:space:]]\+from " \
  backend/routers/ --include="*.py" \
  | grep -v "^.*#" \
  | grep -v __pycache__ \
  | sort -t: -k1,1
```

**الملفات المتوقع فيها نتائج بعد A2 و A3 و B2 و B3**: يجب أن يكون الناتج **صفر سطر** في الـ production routers.

---

## 🔵 المرحلة C — البنية التحتية للإنتاج (الأسبوعين الأخيرين)

---

### C1 — إعداد GitHub Actions CI Pipeline

**الملف الجديد**: `.github/workflows/ci.yml`

```yaml
name: Dentix CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  backend:
    name: Backend Tests + Security
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: dentix_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov bandit safety

      - name: Run database migrations
        env:
          DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/dentix_test
          SECRET_KEY: test-secret-key-for-ci-only
        run: alembic upgrade head

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/dentix_test
          SECRET_KEY: test-secret-key-for-ci-only
          ENVIRONMENT: test
        run: |
          pytest backend/tests/ \
            --cov=backend \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=70 \
            -v \
            --tb=short \
            -x

      - name: Upload coverage report
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

      - name: Security scan — Bandit
        run: |
          bandit -r backend/ \
            -ll \
            -x backend/tests,backend/scripts \
            --format txt
        # ⚠️ NO continue-on-error — يكسر الـ CI لو لقى HIGH finding

      - name: Dependency vulnerability check — Safety
        run: safety check --full-report

  frontend:
    name: Frontend Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: cd frontend && npm ci

      - name: Run frontend tests
        run: cd frontend && npm run test

      - name: Build check
        run: cd frontend && npm run build
```

**✅ تحقق**:
```bash
# Push commit صغير وراقب GitHub Actions
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions pipeline"
git push
# افتح GitHub → Actions tab → يجب أن تبدأ الـ pipeline
```

---

### C2 — رفع Backend Coverage لـ 75%+

**الخطوة 1**: قِس الـ coverage الحالية:
```bash
cd backend
pytest backend/tests/ \
  --cov=backend \
  --cov-report=html \
  --cov-report=term-missing \
  -q
# افتح htmlcov/index.html وابحث عن modules بـ coverage < 50%
```

**الخطوة 2**: أهم الملفات المتوقع ناقصة تغطيتها:

#### C2.1 — اختبارات `TreatmentService`
**الملف**: `backend/tests/services/test_treatment_service.py`

```python
"""
Tests for TreatmentService — validates business logic isolation.
"""
import pytest
from unittest.mock import MagicMock, patch
from backend.services.treatment_service import TreatmentService


class TestValidateStockAvailability:
    def test_sufficient_stock_returns_no_errors(self):
        mock_db = MagicMock()
        svc = TreatmentService(db=mock_db, tenant_id=1, current_user=MagicMock())
        # mock inventory to return available=True
        with patch.object(svc, '_check_material', return_value=(True, 10, "gauze")):
            errors = svc.validate_stock_availability([{"material_id": 1, "qty": 2}])
        assert errors == []

    def test_insufficient_stock_returns_error(self):
        mock_db = MagicMock()
        svc = TreatmentService(db=mock_db, tenant_id=1, current_user=MagicMock())
        with patch.object(svc, '_check_material', return_value=(False, 0, "gauze")):
            errors = svc.validate_stock_availability([{"material_id": 1, "qty": 5}])
        assert len(errors) == 1
        assert "gauze" in errors[0]


class TestCalculateTreatmentPrice:
    def test_cash_price_list(self, mock_db):
        svc = TreatmentService(db=mock_db, tenant_id=1, current_user=MagicMock())
        price = svc.calculate_treatment_price(procedure_id=1, price_list_id=1)
        assert isinstance(price, float)
        assert price >= 0

    def test_insurance_price_list_applies_coverage(self, mock_db):
        # insurance at 80% coverage
        svc = TreatmentService(db=mock_db, tenant_id=1, current_user=MagicMock())
        price = svc.calculate_treatment_price(procedure_id=1, price_list_id=2)
        # patient pays 20%
        assert price == pytest.approx(original_price * 0.2, rel=0.01)

    def test_missing_procedure_raises_404(self, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        svc = TreatmentService(db=mock_db, tenant_id=1, current_user=MagicMock())
        with pytest.raises(Exception):  # HTTPException 404
            svc.calculate_treatment_price(procedure_id=9999, price_list_id=1)
```

#### C2.2 — اختبارات tenant isolation للـ insurance module
```python
# backend/tests/test_tenant_isolation_complete.py
# أضف للـ test cases الموجودة:

def test_tenant_a_cannot_see_tenant_b_insurance_providers(client_a, client_b):
    """Tenant A cannot access Tenant B's insurance providers."""
    # Create provider in Tenant B
    resp_b = client_b.post("/api/v1/insurance/providers", json={"name": "B Insurance"})
    provider_id = resp_b.json()["data"]["id"]
    
    # Try to access from Tenant A
    resp_a = client_a.get(f"/api/v1/insurance/providers/{provider_id}")
    assert resp_a.status_code == 404  # Not visible to Tenant A
```

#### C2.3 — اختبارات `LabService`
```python
# backend/tests/services/test_lab_service.py
def test_lab_order_state_transition_create_to_sent():
    """Lab order moves from PENDING to SENT_TO_LAB correctly."""
    ...

def test_lab_payment_recorded_on_completion():
    """Lab payment is created when order is marked complete."""
    ...
```

**✅ تحقق**:
```bash
pytest backend/tests/ --cov=backend --cov-fail-under=75 -q
# يجب أن تنجح — لو فشلت، افتح htmlcov/index.html وأضف tests للـ uncovered lines
```

---

### C3 — إعداد E2E Tests بـ Playwright

**التثبيت**:
```bash
npm install -D @playwright/test
npx playwright install chromium
```

**الملف الجديد**: `e2e/critical-path.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

const BASE = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173';
const ADMIN = { email: 'admin@test.com', password: 'TestPass1!' };

test.describe('Dentix Critical Path', () => {

  test('1 — login and reach dashboard', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.fill('[name=username]', ADMIN.email);
    await page.fill('[name=password]', ADMIN.password);
    await page.click('button[type=submit]');
    await expect(page).toHaveURL(/dashboard/);
    await expect(page.locator('h1, [data-testid=dashboard-title]')).toBeVisible();
  });

  test('2 — create patient', async ({ page }) => {
    await loginAs(page, ADMIN);
    await page.goto(`${BASE}/patients`);
    await page.click('[data-testid=add-patient-btn], button:has-text("إضافة")');
    await page.fill('[name=name]', 'Playwright Test Patient');
    await page.fill('[name=phone]', '01000000000');
    await page.fill('[name=age]', '30');
    await page.click('button[type=submit]');
    await expect(page.locator('text=Playwright Test Patient')).toBeVisible();
  });

  test('3 — book appointment', async ({ page }) => {
    await loginAs(page, ADMIN);
    await page.goto(`${BASE}/appointments`);
    await page.click('[data-testid=new-appointment-btn], button:has-text("موعد")');
    // fill appointment form
    await page.click('button[type=submit]');
    await expect(page.locator('[data-testid=appointment-list]')).toBeVisible();
  });

  test('4 — add treatment and verify balance', async ({ page }) => {
    await loginAs(page, ADMIN);
    // navigate to patient created in test 2
    const patient = await page.locator('text=Playwright Test Patient').first();
    await patient.click();
    await page.click('[data-testid=add-treatment-btn]');
    // fill treatment
    await page.click('button[type=submit]');
    // verify balance updated
    await page.click('[data-testid=billing-tab]');
    await expect(page.locator('[data-testid=patient-balance]')).not.toHaveText('0');
  });

  test('5 — RBAC: nurse cannot access financials', async ({ page }) => {
    await loginAs(page, { email: 'nurse@test.com', password: 'TestPass1!' });
    await page.goto(`${BASE}/billing`);
    // Should be redirected or show 403
    await expect(page).not.toHaveURL(/billing/);
  });

});

async function loginAs(page, user) {
  await page.goto(`${BASE}/login`);
  await page.fill('[name=username]', user.email);
  await page.fill('[name=password]', user.password);
  await page.click('button[type=submit]');
  await page.waitForURL(/dashboard|patients|appointments/);
}
```

**الملف الجديد**: `playwright.config.ts`
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});
```

**أضف للـ CI** (في `ci.yml` تحت job جديد):
```yaml
  e2e:
    name: E2E Tests (Playwright)
    runs-on: ubuntu-latest
    needs: [backend, frontend]  # يشتغل بعد نجاحهم
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: npx playwright install chromium
      - name: Start services
        run: docker-compose -f docker-compose.test.yml up -d
      - run: npx playwright test
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

**✅ تحقق**:
```bash
# شغّل الـ dev servers أولاً
npx playwright test --headed  # تشوف الـ browser بتشتغل
npx playwright test           # headless للـ CI
```

---

### C4 — إنشاء `docs/` Folder

#### C4.1 — `docs/ARCHITECTURE.md`

```markdown
# Dentix — Architecture Guide

## Layer Map

```
HTTP Request
    ↓
FastAPI Router (routers/)          ← validation only, ≤15 lines/endpoint
    ↓
Service Layer (services/)          ← all business logic
    ↓
CRUD Layer (crud/)                 ← raw DB operations
    ↓
SQLAlchemy Models (models/)        ← schema + relationships
    ↓
PostgreSQL Database
```

## Multi-Tenancy Strategy

Every request carries a `tenant_id` (set by `TenantMiddleware`).
The `tenant_scope.py` event listener auto-injects
`.filter(Model.tenant_id == current_tenant_id)` on every ORM query.

Super Admin bypasses this via `set_super_admin_bypass(True)`.

## RBAC Matrix

| Permission | admin | manager | doctor | receptionist | nurse | accountant | assistant |
|-----------|:-----:|:-------:|:------:|:------------:|:-----:|:----------:|:--------:|
| PATIENT_CREATE | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| CLINICAL_WRITE | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| FINANCIAL_WRITE | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| SYSTEM_CONFIG | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Key Design Decisions

- **async-first**: FastAPI routes are sync wrappers where needed; services are sync SQLAlchemy
- **tenant_scope**: uses SQLAlchemy `do_orm_execute` event — auto, not manual
- **auth.py**: canonical JWT utilities — used by tests, scripts, and routers
- **AIUsageLog**: type alias for AILog in models/__init__.py — legacy code works unchanged
```

#### C4.2 — `docs/DEPLOYMENT.md`

```markdown
# Dentix — Deployment Guide

## Required Environment Variables

| Variable | Required | Default | Description |
|---------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | — | JWT signing key (min 32 chars) |
| `ENCRYPTION_KEY` | ✅ | — | Fernet key for PII encryption |
| `ENVIRONMENT` | ✅ | `development` | `development` / `staging` / `production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `60` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ❌ | `7` | JWT refresh token lifetime |
| `CLOUDINARY_URL` | ❌ | — | For file attachments |
| `GOOGLE_DRIVE_CREDENTIALS` | ❌ | — | For backup feature |

## Local Development Setup

```bash
# 1. Clone and setup
git clone <repo>
cd DENTIX

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Environment
cp .env.example .env
# Edit .env with your values

# 4. Database
alembic upgrade head

# 5. Run
uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Production Deployment

```bash
# Run migrations first (ALWAYS before deploying new code)
alembic upgrade head

# Start with gunicorn
gunicorn backend.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

# Or with Docker
docker-compose up -d
```

## Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
```

#### C4.3 — `docs/PERFORMANCE_BASELINE.md`

قِس وسجّل:
```bash
# Install httpx for quick benchmarking
pip install httpx

python -c "
import httpx, time, statistics

TOKEN = 'your-test-token'
BASE = 'http://localhost:8000/api/v1'
HEADERS = {'Authorization': f'Bearer {TOKEN}'}
ENDPOINTS = [
    ('GET', '/patients', None),
    ('GET', '/appointments', None),
    ('GET', '/dashboard', None),
]

for method, path, body in ENDPOINTS:
    times = []
    for _ in range(10):
        start = time.perf_counter()
        httpx.request(method, BASE + path, headers=HEADERS)
        times.append((time.perf_counter() - start) * 1000)
    print(f'{path}: avg={statistics.mean(times):.1f}ms p95={sorted(times)[9]:.1f}ms')
"
```

**الهدف**: كل endpoint < 200ms على test data معقولة (1000 patient)

---

### C5 — Security Scan + Dependency Audit

```bash
# Bandit — static security analysis
pip install bandit
bandit -r backend/ \
  -ll \
  -x backend/tests,backend/scripts \
  --format txt \
  --output docs/bandit-report.txt

# Safety — dependency vulnerabilities
pip install safety
safety check --full-report --output docs/safety-report.txt

# تحقق يدوي من الـ reports
cat docs/bandit-report.txt | grep "High\|Medium"
# الهدف: 0 High findings
```

**إصلاح أي High findings**:
```bash
# مثال شائع — subprocess without shell=False
# ❌
subprocess.run(cmd, shell=True)
# ✅
subprocess.run(cmd.split(), shell=False)

# مثال — hardcoded secret
# ❌
SECRET = "my-secret-key"
# ✅
SECRET = os.getenv("SECRET_KEY")
```

---

### C6 — OpenAPI Spec Export

**الملف الجديد**: `scripts/export_openapi.py`
```python
"""Export OpenAPI specification to docs/api-spec.json"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

spec = app.openapi()
output_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'api-spec.json')

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(spec, f, indent=2, ensure_ascii=False)

print(f"✅ OpenAPI spec exported: {len(spec['paths'])} endpoints")
```

**تشغيل**:
```bash
python scripts/export_openapi.py
# ✅ OpenAPI spec exported: 87 endpoints
```

**أضف لـ CI** (اختياري):
```yaml
- name: Export OpenAPI spec
  run: python scripts/export_openapi.py
- name: Upload API spec
  uses: actions/upload-artifact@v4
  with:
    name: api-spec
    path: docs/api-spec.json
```

---

## ✅ Checklist النهائي

### مقاييس النجاح

```bash
# 1. Zero inline imports in production routers
grep -rn "^[[:space:]]\+import \|^[[:space:]]\+from " \
  backend/routers/ --include="*.py" | grep -v __pycache__
# المطلوب: 0 نتائج

# 2. Zero unprotected endpoints
grep -rn "Depends(get_current_user)" backend/routers/ --include="*.py" \
  | grep -v "require_permission\|#\|auth/"
# المطلوب: 0 نتائج (ما عدا auth/users.py للـ self-profile endpoints)

# 3. Test coverage
pytest backend/tests/ --cov=backend --cov-fail-under=75 -q
# المطلوب: PASSED

# 4. Security scan
bandit -r backend/ -ll -x backend/tests,backend/scripts -q
# المطلوب: 0 High severity issues

# 5. Dependency safety
safety check -q
# المطلوب: No known security vulnerabilities

# 6. No print() in core code
grep -rn "print(" backend/ --include="*.py" \
  | grep -v "__pycache__\|test_\|scripts/\|alembic/"
# المطلوب: 0 نتائج

# 7. AI model unification verified
python -c "
from backend import models
assert models.AIUsageLog is models.AILog, 'AIUsageLog alias broken!'
print('✅ AIUsageLog = AILog alias working')
"

# 8. Frontend tests pass
cd frontend && npm test -- --run
# المطلوب: All tests pass

# 9. Alembic at head
alembic current
# المطلوب: يظهر الـ latest revision (head)

# 10. App starts without errors
python -c "from backend.main import app; print(f'✅ {len(app.routes)} routes loaded')"
# المطلوب: 80+ routes loaded, zero errors
```

---

## الجدول الزمني

| الأسبوع | المهام | الوقت التقديري |
|---------|--------|---------------|
| **أسبوع 1** | A1 + A2 + A3 + A4 | 6–8 ساعات |
| **أسبوع 2** | B1 + B2 + B3 + B4 | 8–10 ساعات |
| **أسبوع 3** | C1 + C5 + C6 | 5–6 ساعات |
| **أسبوع 4** | C2 + C3 + C4 | 10–12 ساعات |
| **إجمالي** | **كل المهام** | **~35 ساعة** |

---

## ترتيب الـ Commits المقترح

```
feat(security): add RBAC to insurance.py endpoints          ← A1
refactor(router): move inline imports to module level       ← A2 + A3 + B2 + B3
fix(migration): link drop_ai_usage_logs to alembic chain    ← A4
feat(response): apply success_response to dashboard router  ← B1.1
feat(response): apply success_response to notifications     ← B1.2
feat(response): apply success_response to remaining routers ← B1.3–B1.5
ci: add GitHub Actions pipeline with coverage + bandit      ← C1
test: add TreatmentService unit tests                       ← C2.1
test: add insurance tenant isolation tests                  ← C2.2
test: add LabService unit tests                             ← C2.3
test(e2e): add Playwright critical path spec                ← C3
docs: add ARCHITECTURE, DEPLOYMENT, PERFORMANCE_BASELINE    ← C4
chore: add bandit and safety security reports               ← C5
chore: add OpenAPI spec export script                       ← C6
```

---

> **نصيحة أخيرة**: ابدأ بـ A1 (30 دقيقة) — ده أسرع win وأعلى أثر أمني.  
> ثم A4 (ربط الـ migration) لأن الـ DB state لازم يكون consistent قبل أي deploy.  
> كل المهام التانية مهمة لكن مش فيها خطر أمني فوري.
