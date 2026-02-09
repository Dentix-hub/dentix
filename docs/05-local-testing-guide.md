# 🧪 دليل الاختبار المحلي الشامل - Smart Clinic

## 📋 جدول المحتويات
1. [إعداد البيئة المحلية](#إعداد-البيئة-المحلية)
2. [اختبار Backend](#اختبار-backend)
3. [اختبار Frontend](#اختبار-frontend)
4. [اختبار التكامل](#اختبار-التكامل)
5. [اختبار الأداء](#اختبار-الأداء)
6. [اختبار الأمان](#اختبار-الأمان)
7. [Checklist قبل الرفع](#checklist-قبل-الرفع)

---

## 1️⃣ إعداد البيئة المحلية

### المتطلبات الأساسية

```bash
# تأكد من وجود هذه البرامج
python --version    # يجب أن يكون 3.10+
node --version      # يجب أن يكون 18+
npm --version       # يجب أن يكون 9+
git --version       # أي إصدار حديث
```

### خطوات الإعداد

#### A. Backend Setup

```bash
# 1. انتقل لمجلد Backend
cd backend

# 2. أنشئ virtual environment
python -m venv venv

# 3. فعّل الـ virtual environment
# في Windows:
venv\Scripts\activate
# في Linux/Mac:
source venv/bin/activate

# 4. نصّب المكتبات
pip install -r requirements.txt

# 5. أنشئ ملف .env
cp .env.example .env

# 6. عدّل ملف .env
# افتح .env وعدّل هذه القيم:
```

**ملف `.env` للتطوير المحلي:**
```env
# Database
DATABASE_URL=sqlite:///./clinic_test.db
# أو إذا تستخدم PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/smart_clinic_test

# Secret Keys
SECRET_KEY=your-super-secret-key-for-testing-only
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=development
DEBUG=True

# CORS
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# Redis (optional للتطوير)
REDIS_URL=redis://localhost:6379/0

# Email (للاختبار - استخدم Mailtrap أو Gmail)
SMTP_HOST=smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USER=your-mailtrap-user
SMTP_PASSWORD=your-mailtrap-password
SMTP_FROM=test@smartclinic.local

# File Storage
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=10485760  # 10MB
```

```bash
# 7. أنشئ قاعدة البيانات
python -c "from backend.database import engine; from backend.models import Base; Base.metadata.create_all(bind=engine)"

# 8. املأ البيانات التجريبية
python seed_test_data.py

# 9. شغّل السيرفر
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**التحقق من Backend:**
```bash
# افتح المتصفح على:
http://localhost:8000/docs

# يجب أن تشوف Swagger UI
# جرب endpoint بسيط:
http://localhost:8000/health
```

#### B. Frontend Setup

```bash
# 1. انتقل لمجلد Frontend
cd frontend

# 2. نصّب المكتبات
npm install

# 3. أنشئ ملف .env
cp .env.example .env.local

# 4. عدّل ملف .env.local
```

**ملف `.env.local`:**
```env
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000
VITE_ENVIRONMENT=development
```

```bash
# 5. شغّل السيرفر
npm run dev

# يجب أن يفتح على:
# http://localhost:5173
```

**التحقق من Frontend:**
- افتح `http://localhost:5173`
- يجب أن تشوف صفحة Login
- جرب تسجيل الدخول باستخدام:
  - Email: `admin@test.com`
  - Password: `admin123`

---

## 2️⃣ اختبار Backend

### A. Unit Tests (اختبارات الوحدات)

```bash
# في مجلد backend/

# 1. شغّل كل الاختبارات
pytest

# 2. شغّل مع تقرير التغطية
pytest --cov=backend --cov-report=html

# 3. شغّل اختبارات محددة
pytest tests/test_patients.py
pytest tests/test_inventory.py
pytest tests/test_auth.py

# 4. شغّل اختبار واحد
pytest tests/test_patients.py::test_create_patient

# 5. عرض نتائج مفصلة
pytest -v

# 6. إيقاف عند أول خطأ
pytest -x
```

**كتابة اختبار جديد:**

```python
# File: backend/tests/test_patients.py

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db, SessionLocal

client = TestClient(app)

# Override database dependency للاختبار
def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def test_create_patient():
    """Test creating a new patient"""
    
    # 1. Login first
    login_response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123"
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 2. Create patient
    response = client.post(
        "/api/patients",
        json={
            "name": "أحمد محمد",
            "phone": "01012345678",
            "date_of_birth": "1990-01-01",
            "gender": "male"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "أحمد محمد"
    assert data["phone"] == "01012345678"
    assert "id" in data

def test_get_patients():
    """Test retrieving patients list"""
    
    # Login
    login_response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123"
    })
    token = login_response.json()["access_token"]
    
    # Get patients
    response = client.get(
        "/api/patients",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_search_patients():
    """Test patient search"""
    
    # Login
    login_response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123"
    })
    token = login_response.json()["access_token"]
    
    # Search
    response = client.get(
        "/api/patients?search=أحمد",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert all("أحمد" in p["name"] for p in data)

def test_update_patient():
    """Test updating patient"""
    
    # Login
    login_response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123"
    })
    token = login_response.json()["access_token"]
    
    # Create patient first
    create_response = client.post(
        "/api/patients",
        json={
            "name": "محمد علي",
            "phone": "01098765432",
            "date_of_birth": "1985-05-15",
            "gender": "male"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    patient_id = create_response.json()["id"]
    
    # Update patient
    response = client.put(
        f"/api/patients/{patient_id}",
        json={
            "name": "محمد علي المحدث",
            "phone": "01098765432"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "محمد علي المحدث"

def test_delete_patient():
    """Test soft delete patient"""
    
    # Login
    login_response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123"
    })
    token = login_response.json()["access_token"]
    
    # Create patient
    create_response = client.post(
        "/api/patients",
        json={
            "name": "للحذف",
            "phone": "01055555555",
            "date_of_birth": "1995-01-01",
            "gender": "male"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    patient_id = create_response.json()["id"]
    
    # Delete
    response = client.delete(
        f"/api/patients/{patient_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    
    # Verify deleted (should not appear in list)
    list_response = client.get(
        "/api/patients",
        headers={"Authorization": f"Bearer {token}"}
    )
    patients = list_response.json()
    assert not any(p["id"] == patient_id for p in patients)

# Test validation
def test_create_patient_invalid_phone():
    """Test patient creation with invalid phone"""
    
    login_response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123"
    })
    token = login_response.json()["access_token"]
    
    response = client.post(
        "/api/patients",
        json={
            "name": "Test",
            "phone": "123",  # Invalid
            "date_of_birth": "1990-01-01",
            "gender": "male"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 422  # Validation error

# Test unauthorized access
def test_get_patients_unauthorized():
    """Test accessing patients without auth"""
    
    response = client.get("/api/patients")
    assert response.status_code == 401
```

### B. API Manual Testing (Postman/Thunder Client)

**إنشاء Collection في Postman:**

```json
{
  "info": {
    "name": "Smart Clinic API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Auth",
      "item": [
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"email\": \"admin@test.com\",\n  \"password\": \"admin123\"\n}"
            },
            "url": {
              "raw": "http://localhost:8000/api/auth/login",
              "protocol": "http",
              "host": ["localhost"],
              "port": "8000",
              "path": ["api", "auth", "login"]
            }
          }
        }
      ]
    },
    {
      "name": "Patients",
      "item": [
        {
          "name": "Get Patients",
          "request": {
            "method": "GET",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{token}}"
              }
            ],
            "url": "http://localhost:8000/api/patients"
          }
        },
        {
          "name": "Create Patient",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{token}}"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"name\": \"أحمد محمد\",\n  \"phone\": \"01012345678\",\n  \"date_of_birth\": \"1990-01-01\",\n  \"gender\": \"male\"\n}"
            },
            "url": "http://localhost:8000/api/patients"
          }
        }
      ]
    }
  ]
}
```

### C. Database Testing

```bash
# 1. فحص قاعدة البيانات
cd backend

# SQLite
sqlite3 clinic_test.db

# Commands في SQLite:
.tables                    # عرض كل الجداول
SELECT * FROM patients;    # عرض المرضى
SELECT * FROM users;       # عرض المستخدمين
.schema patients          # عرض بنية جدول المرضى
.exit                     # خروج

# PostgreSQL
psql -U postgres -d smart_clinic_test

# Commands في PostgreSQL:
\dt                       # عرض الجداول
SELECT * FROM patients;
\d patients              # وصف جدول
\q                       # خروج
```

**فحص Data Integrity:**

```python
# File: backend/tests/test_database_integrity.py

import pytest
from sqlalchemy import inspect
from backend.database import engine
from backend.models import Patient, User, Appointment

def test_database_tables_exist():
    """Verify all required tables exist"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_tables = [
        'users', 'patients', 'appointments', 
        'treatments', 'materials', 'warehouses',
        'batches', 'stock_items'
    ]
    
    for table in required_tables:
        assert table in tables, f"Table {table} is missing"

def test_foreign_keys():
    """Verify foreign key constraints"""
    inspector = inspect(engine)
    
    # Check appointments -> patients
    fks = inspector.get_foreign_keys('appointments')
    patient_fk = next((fk for fk in fks if 'patient_id' in fk['constrained_columns']), None)
    assert patient_fk is not None
    assert patient_fk['referred_table'] == 'patients'

def test_indexes():
    """Verify important indexes exist"""
    inspector = inspect(engine)
    
    # Check patient indexes
    indexes = inspector.get_indexes('patients')
    index_columns = [idx['column_names'] for idx in indexes]
    
    assert ['phone'] in index_columns
    assert ['national_id'] in index_columns
```

---

## 3️⃣ اختبار Frontend

### A. Component Testing

```bash
# في مجلد frontend/

# 1. شغّل الاختبارات
npm test

# 2. شغّل مع UI
npm test -- --ui

# 3. شغّل مع Coverage
npm test -- --coverage

# 4. Watch mode
npm test -- --watch
```

**مثال: اختبار Button Component:**

```typescript
// File: src/shared/ui/__tests__/Button.test.tsx

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Button } from '../Button';

describe('Button Component', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);
    
    await userEvent.click(screen.getByText('Click'));
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByText('Disabled')).toBeDisabled();
  });

  it('shows loading state', () => {
    render(<Button isLoading>Loading</Button>);
    expect(screen.getByText('Loading')).toBeDisabled();
  });

  it('applies correct variant classes', () => {
    const { rerender } = render(<Button variant="primary">Primary</Button>);
    expect(screen.getByText('Primary')).toHaveClass('bg-primary');
    
    rerender(<Button variant="secondary">Secondary</Button>);
    expect(screen.getByText('Secondary')).toHaveClass('bg-secondary');
  });
});
```

### B. Integration Testing (E2E مع Cypress)

```bash
# 1. نصّب Cypress
npm install -D cypress

# 2. افتح Cypress
npx cypress open

# 3. شغّل الاختبارات
npx cypress run
```

**مثال: Patient Flow Test:**

```typescript
// File: cypress/e2e/patient-workflow.cy.ts

describe('Patient Management Workflow', () => {
  beforeEach(() => {
    // Login before each test
    cy.visit('http://localhost:5173');
    cy.get('input[name="email"]').type('admin@test.com');
    cy.get('input[name="password"]').type('admin123');
    cy.get('button[type="submit"]').click();
    
    // Wait for dashboard
    cy.url().should('include', '/dashboard');
  });

  it('creates a new patient', () => {
    // Navigate to patients
    cy.get('a[href="/patients"]').click();
    cy.url().should('include', '/patients');
    
    // Click new patient button
    cy.contains('مريض جديد').click();
    
    // Fill form
    cy.get('input[name="name"]').type('أحمد محمد التجريبي');
    cy.get('input[name="phone"]').type('01012345678');
    cy.get('input[name="dateOfBirth"]').type('1990-01-01');
    cy.get('select[name="gender"]').select('male');
    
    // Submit
    cy.contains('حفظ').click();
    
    // Verify success
    cy.contains('تم إضافة المريض بنجاح').should('be.visible');
    cy.contains('أحمد محمد التجريبي').should('be.visible');
  });

  it('searches for a patient', () => {
    cy.visit('http://localhost:5173/patients');
    
    // Type in search
    cy.get('input[placeholder*="بحث"]').type('أحمد');
    
    // Verify results
    cy.get('[data-testid="patient-row"]').should('have.length.greaterThan', 0);
    cy.get('[data-testid="patient-row"]').first().should('contain', 'أحمد');
  });

  it('books an appointment for a patient', () => {
    // Go to appointments
    cy.visit('http://localhost:5173/appointments');
    
    // Click new appointment
    cy.contains('موعد جديد').click();
    
    // Select patient
    cy.get('input[name="patient"]').type('أحمد');
    cy.contains('أحمد محمد التجريبي').click();
    
    // Select date & time
    cy.get('input[name="date"]').type('2024-12-25');
    cy.get('input[name="time"]').type('10:00');
    
    // Submit
    cy.contains('حفظ').click();
    
    // Verify
    cy.contains('تم حجز الموعد بنجاح').should('be.visible');
  });

  it('complete treatment workflow', () => {
    // 1. Go to patient details
    cy.visit('http://localhost:5173/patients');
    cy.contains('أحمد محمد التجريبي').click();
    
    // 2. Add treatment
    cy.contains('إضافة علاج').click();
    
    // 3. Select procedure
    cy.get('select[name="procedure"]').select('Composite Filling');
    
    // 4. Select tooth
    cy.get('[data-tooth="11"]').click();
    
    // 5. Add materials (should auto-populate)
    cy.contains('المواد المستهلكة').should('be.visible');
    
    // 6. Save
    cy.contains('حفظ العلاج').click();
    
    // 7. Verify
    cy.contains('تم إضافة العلاج بنجاح').should('be.visible');
  });

  it('handles errors gracefully', () => {
    // Try to create patient with invalid data
    cy.visit('http://localhost:5173/patients');
    cy.contains('مريض جديد').click();
    
    // Submit empty form
    cy.contains('حفظ').click();
    
    // Should show validation errors
    cy.contains('الاسم مطلوب').should('be.visible');
    cy.contains('رقم الهاتف مطلوب').should('be.visible');
  });
});
```

### C. Visual Testing (Manual)

**Checklist للاختبار اليدوي:**

```markdown
## صفحة Login
- [ ] الحقول تظهر بشكل صحيح
- [ ] رسائل الخطأ واضحة
- [ ] زر "نسيت كلمة المرور" يعمل
- [ ] التحقق من البيانات يعمل
- [ ] Loading state يظهر عند الضغط على "دخول"

## Dashboard
- [ ] الإحصائيات تظهر بشكل صحيح
- [ ] الرسوم البيانية تعمل
- [ ] Quick actions تعمل
- [ ] Responsive على الموبايل

## صفحة المرضى
- [ ] قائمة المرضى تظهر
- [ ] البحث يعمل
- [ ] الـ Pagination يعمل
- [ ] إضافة مريض جديد يعمل
- [ ] تعديل المريض يعمل
- [ ] حذف المريض يعمل
- [ ] عرض تفاصيل المريض

## صفحة المواعيد
- [ ] Calendar view يعمل
- [ ] List view يعمل
- [ ] إضافة موعد يعمل
- [ ] تعديل موعد يعمل
- [ ] إلغاء موعد يعمل
- [ ] الألوان حسب الحالة صحيحة

## صفحة المخزون
- [ ] قائمة المواد تظهر
- [ ] Stock status صحيح (متوفر/منخفض/نفذ)
- [ ] إضافة مادة جديدة
- [ ] استلام شحنة
- [ ] استهلاك المواد
- [ ] Material Sessions
- [ ] تنبيهات الصلاحية

## نموذج استهلاك المواد (الجديد)
- [ ] المواد المقترحة تظهر تلقائياً
- [ ] Quick buttons للكميات تعمل
- [ ] Custom amount يعمل
- [ ] Stock warnings تظهر
- [ ] Alternatives تظهر لو المادة نفذت
- [ ] Cost analysis صحيح
```

---

## 4️⃣ اختبار الأداء

### A. Lighthouse (Chrome DevTools)

```bash
# 1. افتح Chrome DevTools (F12)
# 2. اختار tab "Lighthouse"
# 3. اختار:
#    - Performance
#    - Accessibility
#    - Best Practices
#    - SEO
# 4. اضغط "Generate report"
```

**الأهداف المطلوبة:**
- Performance: > 90
- Accessibility: > 90
- Best Practices: > 90
- SEO: > 80

### B. Load Testing (Backend)

```bash
# نصّب Locust
pip install locust
```

```python
# File: backend/tests/locustfile.py

from locust import HttpUser, task, between
import random

class SmartClinicUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login once at start"""
        response = self.client.post("/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def view_patients(self):
        """View patients list (most common action)"""
        self.client.get("/api/patients", headers=self.headers)
    
    @task(2)
    def search_patients(self):
        """Search for patients"""
        query = random.choice(["أحمد", "محمد", "فاطمة", "سارة"])
        self.client.get(f"/api/patients?search={query}", headers=self.headers)
    
    @task(1)
    def view_patient_details(self):
        """View patient details"""
        patient_id = random.randint(1, 100)
        self.client.get(f"/api/patients/{patient_id}", headers=self.headers)
    
    @task(2)
    def view_appointments(self):
        """View appointments"""
        self.client.get("/api/appointments", headers=self.headers)
    
    @task(1)
    def view_inventory(self):
        """View inventory"""
        self.client.get("/api/inventory/stock", headers=self.headers)
    
    @task(1)
    def create_appointment(self):
        """Create new appointment"""
        self.client.post("/api/appointments", json={
            "patient_id": random.randint(1, 100),
            "doctor_id": 1,
            "date": "2024-12-25",
            "time": "10:00",
            "duration": 30
        }, headers=self.headers)
```

```bash
# شغّل Load Test
locust -f locustfile.py --host=http://localhost:8000

# افتح المتصفح على:
http://localhost:8089

# ابدأ الاختبار:
# Number of users: 50
# Spawn rate: 10
# اضغط "Start swarming"
```

**الأهداف:**
- Response time (median): < 200ms
- Response time (95th percentile): < 500ms
- Requests per second: > 100
- Failure rate: < 1%

### C. Memory & CPU Profiling

```python
# File: backend/profile_app.py

from memory_profiler import profile
import time

@profile
def test_patient_query():
    """Profile patient query"""
    from backend.database import SessionLocal
    from backend.models import Patient
    
    db = SessionLocal()
    
    # Query all patients
    patients = db.query(Patient).all()
    
    # Process data
    result = [p.name for p in patients]
    
    db.close()
    return result

if __name__ == "__main__":
    test_patient_query()
```

```bash
# Run profiling
python -m memory_profiler profile_app.py
```

---

## 5️⃣ اختبار الأمان

### A. Security Checklist

```markdown
## Authentication & Authorization
- [ ] Password hashing يعمل (bcrypt)
- [ ] JWT tokens تنتهي صلاحيتها
- [ ] Session management آمن
- [ ] لا يمكن الوصول للـ API بدون token
- [ ] Permissions تعمل بشكل صحيح
- [ ] 2FA يعمل (لو موجود)

## Data Protection
- [ ] SQL Injection محمي (استخدام ORM)
- [ ] XSS محمي (تنظيف المدخلات)
- [ ] CSRF محمي
- [ ] Sensitive data encrypted
- [ ] File uploads آمنة
- [ ] لا توجد secrets في الكود

## API Security
- [ ] Rate limiting يعمل
- [ ] CORS configured صح
- [ ] HTTPS enforced (في production)
- [ ] Input validation شغال
- [ ] Error messages لا تكشف معلومات حساسة

## Database Security
- [ ] Backups تعمل
- [ ] Soft delete بدلاً من hard delete
- [ ] Audit logging شغال
- [ ] Database user له أقل صلاحيات ممكنة
```

### B. Security Testing Tools

```bash
# 1. OWASP ZAP (Zed Attack Proxy)
# حمّل من: https://www.zaproxy.org/download/
# شغّله وافحص http://localhost:8000

# 2. SQLMap (SQL Injection Testing)
sqlmap -u "http://localhost:8000/api/patients?search=test" \
       --cookie="session=YOUR_SESSION" \
       --batch

# 3. Security Headers Check
curl -I http://localhost:8000

# يجب أن تشوف:
# X-Frame-Options
# X-Content-Type-Options
# Strict-Transport-Security (في production)
```

### C. Penetration Testing Checklist

```markdown
## Basic Penetration Tests

### 1. Authentication Bypass
- [ ] محاولة الدخول بدون credentials
- [ ] محاولة استخدام tokens قديمة
- [ ] محاولة تخمين passwords
- [ ] محاولة SQL injection في login

### 2. Authorization Tests
- [ ] User عادي يحاول الوصول لصفحة admin
- [ ] محاولة الوصول لبيانات tenant آخر
- [ ] محاولة تعديل بيانات مستخدم آخر

### 3. Input Validation
- [ ] إرسال HTML في الحقول النصية
- [ ] إرسال JavaScript في الحقول
- [ ] إرسال SQL queries
- [ ] رفع ملفات ضخمة جداً
- [ ] رفع ملفات executable

### 4. Session Management
- [ ] Session hijacking
- [ ] Session fixation
- [ ] Concurrent sessions
```

---

## 6️⃣ اختبار التوافق

### A. المتصفحات

```markdown
## Desktop Browsers
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

## Mobile Browsers
- [ ] Chrome Mobile
- [ ] Safari Mobile
- [ ] Samsung Internet

## Responsive Design
- [ ] Desktop (1920x1080)
- [ ] Laptop (1366x768)
- [ ] Tablet (768x1024)
- [ ] Mobile (375x667)
```

### B. أنظمة التشغيل

```markdown
- [ ] Windows 10/11
- [ ] macOS
- [ ] Linux (Ubuntu/Debian)
- [ ] iOS
- [ ] Android
```

---

## 7️⃣ Checklist النهائي قبل الرفع

### A. Code Quality

```bash
# Backend
- [ ] كل الـ tests تنجح
- [ ] Test coverage > 70%
- [ ] لا توجد warnings في console
- [ ] كل الـ migrations تعمل
- [ ] Database seeds تعمل
- [ ] لا توجد debug files

# Frontend
- [ ] كل الـ tests تنجح
- [ ] لا توجد console errors
- [ ] لا توجد unused imports
- [ ] Build ينجح بدون errors
- [ ] Bundle size معقول (< 500KB gzipped)
```

### B. Documentation

```markdown
- [ ] README.md محدّث
- [ ] API documentation كاملة
- [ ] Environment variables موثقة
- [ ] Setup instructions واضحة
- [ ] Troubleshooting guide موجود
```

### C. Configuration

```markdown
- [ ] .env.example محدّث
- [ ] .gitignore صحيح
- [ ] Production configs جاهزة
- [ ] Database migrations tested
- [ ] Backup strategy محددة
```

### D. Performance

```markdown
- [ ] Lighthouse score > 90
- [ ] Load testing passed
- [ ] No memory leaks
- [ ] Database queries optimized
- [ ] Images optimized
- [ ] Caching implemented
```

### E. Security

```markdown
- [ ] Passwords hashed
- [ ] Secrets not in code
- [ ] HTTPS configured
- [ ] Rate limiting enabled
- [ ] Input validation everywhere
- [ ] SQL injection protected
- [ ] XSS protected
- [ ] CSRF protected
```

### F. Functionality

```markdown
## Core Features
- [ ] Login/Logout
- [ ] Patient CRUD
- [ ] Appointment CRUD
- [ ] Treatment creation
- [ ] Inventory management
- [ ] Billing
- [ ] Reports
- [ ] User management

## Edge Cases
- [ ] Empty states
- [ ] Error handling
- [ ] Loading states
- [ ] Offline behavior
- [ ] Data validation
```

---

## 8️⃣ سكريبت الاختبار الشامل

```bash
# File: test-all.sh

#!/bin/bash

echo "🧪 Starting Smart Clinic Full Test Suite"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Backend Tests
echo ""
echo "🔧 Testing Backend..."
cd backend

# Activate venv
source venv/bin/activate

# Run tests
pytest --cov=backend --cov-report=term-missing
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backend tests passed${NC}"
else
    echo -e "${RED}❌ Backend tests failed${NC}"
    exit 1
fi

# Frontend Tests
echo ""
echo "⚛️  Testing Frontend..."
cd ../frontend

# Run tests
npm test -- --run
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Frontend tests passed${NC}"
else
    echo -e "${RED}❌ Frontend tests failed${NC}"
    exit 1
fi

# Build test
echo ""
echo "🏗️  Testing Build..."
npm run build
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Build successful${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

# E2E Tests (optional)
echo ""
echo "🌐 Running E2E Tests..."
npx cypress run --headless
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ E2E tests passed${NC}"
else
    echo -e "${RED}❌ E2E tests failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=========================================="
echo "✅ All tests passed! Ready for deployment"
echo -e "==========================================${NC}"
```

```bash
# اعطي الصلاحيات
chmod +x test-all.sh

# شغّل الاختبار الشامل
./test-all.sh
```

---

## 📝 Notes

### عند اكتشاف مشكلة:

1. **سجّل المشكلة** في ملف `BUGS.md`
2. **اصلحها فوراً** أو ضعها في TODO
3. **اكتب test** يغطي المشكلة
4. **أعد الاختبار** للتأكد من الحل

### Best Practices:

- ✅ اختبر بعد كل تغيير كبير
- ✅ استخدم بيانات تجريبية واقعية
- ✅ اختبر السيناريوهات السلبية
- ✅ اختبر على أجهزة مختلفة
- ✅ اطلب من شخص آخر يجرب النظام

---

**جاهز للرفع بثقة! 🚀**
