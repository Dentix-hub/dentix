# Dentix — Implementation Guide
## الترتيب الصح للتطبيق

---

## Phase A — Hotfixes (اليوم الأول)

### الخطوة 1: تشخيص React Error #130

```
الملف: frontend/src/main.jsx
الـ patch: patches/A1_error_boundary_diagnostic.jsx
```

أضف الـ DiagnosticErrorBoundary، شغّل الـ app، وابعتلي الـ componentStack من الـ console.
بعد التشخيص احذف الـ ErrorBoundary.

### الخطوة 2: إصلاح Asset Imports

```
الملفات: Layout.jsx, AIChat.jsx
الـ patch: patches/A2_asset_import_fixes.jsx
```

شغّل أولاً:
```bash
grep -rn "from '@/assets" src/ --include="*.jsx" --include="*.js"
```

### الخطوة 3: إصلاح Lazy Imports

```
الملف: App.jsx أو router/index.jsx
الـ patch: patches/A3_lazy_import_fixes.jsx
```

شغّل أولاً:
```bash
grep -rn "lazy(() => import" src/ --include="*.jsx"
```

### الخطوة 4: إصلاح API Endpoints

```
الملفات: tenant.store.js, SecuritySettings.jsx
الـ patch: patches/A5_api_endpoint_fixes.js
```

شغّل أولاً:
```bash
grep -rn "'/users/me'" src/ --include="*.jsx" --include="*.js" --include="*.ts"
```

### الخطوة 5: إصلاح SPA Catch-All

```
الملف: backend/main.py
الـ patch: patches/A6_main_catchall_fix.py
```

---

## Phase B — Standardization (اليوم الثاني)

### الخطوة 1: main.py cleanup

```
الملف: backend/main.py (السطر ~420)
الـ patch: patches/B_standardization_fixes.py (الجزء الأول)
```

### الخطوة 2: inventory.py migration

```
الملف: backend/schemas/inventory.py
الـ patch: patches/B_standardization_fixes.py (الجزء الثاني)
```

شغّل أولاً:
```bash
grep -n "class Config:" backend/schemas/inventory.py
```

---

## Phase C — Tests (اليوم الثالث)

### الخطوة 1: شغّل Coverage Report

```bash
cd backend
coverage run -m pytest tests/ -v 2>&1 | tail -50
coverage report --omit="*/migrations/*,*/test_*" | grep -E "crud/billing|ai/handlers|TOTAL"
```

### الخطوة 2: انسخ الـ test files

```bash
# test_ai_handlers.py — دايماً
cp patches/C1_test_ai_handlers.py backend/tests/test_ai_handlers.py

# test_crud_billing.py — بس لو crud/billing.py < 60%
cp patches/C2_test_crud_billing.py backend/tests/test_crud_billing.py
```

### الخطوة 3: عدّل الـ imports

لازم تعدّل الـ import paths في الـ test files عشان تتطابق مع structure مشروعك:
```python
# عدّل ده بناءً على الـ actual module paths عندك:
from backend.ai.handlers.appointment import handle_appointment_tool
# ← ممكن يكون:
from app.ai.handlers.appointment import handle_appointment_tool
# أو:
from src.ai.handlers.appointment import handle_appointment_tool
```

### الخطوة 4: شغّل الـ tests

```bash
pytest tests/test_ai_handlers.py -v
pytest tests/test_crud_billing.py -v  # لو نسخته
coverage run -m pytest tests/ -v && coverage report
```

---

## Verification Checklist

### بعد Phase A
- [ ] الـ browser console فارغ من React errors
- [ ] `/api/v1/users/me` يرجع 200 في الـ Network tab
- [ ] Refresh على `/appointments` أو أي route مش بيديك 404

### بعد Phase B  
- [ ] `python -m py_compile backend/schemas/inventory.py` بدون errors
- [ ] الـ server startup log يظهر مرة واحدة بس

### بعد Phase C
- [ ] `pytest tests/test_ai_handlers.py -v` كل الـ tests تعدي
- [ ] `coverage report` يظهر `ai/handlers/` > 80%
