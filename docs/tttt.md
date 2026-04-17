# برومت شامل لتطبيق التحسينات على Dentix Backend

## 🎯 نظرة عامة
هذا البرومت يحتوي على تعليمات تفصيلية لتطبيق جميع التحسينات المقترحة على مشروع Dentix Backend بطريقة منهجية ومنظمة.

---

## المرحلة 1: التحسينات الحرجة (Critical) 🔴

### 1.1 إصلاح مشكلة ENCRYPTION_KEY

**الملف:** `backend/core/security.py`

**البرومت:**
```
قم بتحسين ملف backend/core/security.py بالشكل التالي:

1. أزل منطق توليد المفتاح التلقائي واجعل التطبيق يفشل في التشغيل إذا لم يكن ENCRYPTION_KEY موجوداً
2. أضف دالة لتوليد مفتاح جديد للاستخدام في setup
3. أضف دالة للتحقق من صحة المفتاح
4. أضف دالة لتدوير المفاتيح (key rotation)
5. أضف Enum للمفاتيح المختلفة (database encryption, file encryption, etc.)
6. أضف logging للعمليات الحساسة
7. أضف exception handling محسّن

متطلبات:
- يجب أن يكون الكود متوافق مع Python 3.11+
- استخدم typing hints
- أضف docstrings مفصلة
- أضف unit tests في ملف منفصل test_security.py
- أضف validation للمفتاح (يجب أن يكون 32 byte base64 encoded)

الكود يجب أن يحتوي على:
- Class EncryptionManager يدير جميع عمليات التشفير
- Method لتشفير البيانات encrypt(data: str) -> str
- Method لفك التشفير decrypt(data: str) -> str
- Method لتدوير المفاتيح rotate_key(old_key: str, new_key: str)
- Method للتحقق من صحة المفتاح validate_key(key: str) -> bool
- Method لتوليد مفتاح جديد generate_key() -> str
- Exception classes مخصصة: EncryptionError, InvalidKeyError, KeyRotationError

أضف أيضاً ملف backend/scripts/generate_encryption_key.py يحتوي على:
- Script بسيط لتوليد مفتاح جديد
- Validation للمفتاح
- Instructions للاستخدام

أنشئ ملف README_ENCRYPTION.md يشرح:
- كيفية توليد المفتاح
- كيفية إعداده في .env
- كيفية تدوير المفتاح
- Best practices للأمان
```

---

### 1.2 إضافة Global Exception Handler

**الملف:** `backend/core/exceptions.py` (ملف جديد)

**البرومت:**
```
أنشئ ملف backend/core/exceptions.py يحتوي على:

1. Custom Exception Classes:
   - BaseAppException (الأساسي لجميع الاستثناءات)
   - DatabaseException
   - ValidationException
   - AuthenticationException
   - AuthorizationException
   - ResourceNotFoundException
   - RateLimitException
   - ExternalServiceException
   - AIServiceException
   - TenantException

2. Exception Handler Functions:
   - async def handle_validation_exception(request, exc)
   - async def handle_database_exception(request, exc)
   - async def handle_authentication_exception(request, exc)
   - async def handle_rate_limit_exception(request, exc)
   - async def handle_generic_exception(request, exc)

3. Exception Middleware:
   - class ExceptionHandlerMiddleware يعترض جميع الاستثناءات
   - يسجل التفاصيل الكاملة
   - يرسل التنبيهات للاستثناءات الحرجة
   - يرجع response موحد للمستخدم

4. متطلبات الـ Response Format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "رسالة للمستخدم",
    "details": {},
    "trace_id": "uuid",
    "timestamp": "ISO 8601",
    "path": "/api/v1/patients"
  }
}
```

5. يجب تحديث ملف main.py لتسجيل جميع Exception Handlers

6. أضف Integration مع نظام التنبيهات (Slack/Email) للاستثناءات الحرجة

7. أضف ملف tests/test_exceptions.py يختبر:
   - جميع أنواع الاستثناءات
   - Response format
   - Logging
   - Alert system

متطلبات:
- استخدم structlog للـ structured logging
- أضف correlation ID لكل استثناء
- أضف stack trace كامل في logs
- لا تعرض تفاصيل حساسة للمستخدم
- أضف i18n support للرسائل
```

---

### 1.3 تحسين نظام Logging

**الملف:** `backend/core/logging.py`

**البرومت:**
```
قم بإنشاء نظام logging متقدم في backend/core/logging.py:

1. إعداد Structured Logging باستخدام structlog:
   - JSON output format
   - ISO 8601 timestamps
   - Context processors (user_id, tenant_id, trace_id)
   - Log levels مختلفة حسب البيئة

2. Log Handlers:
   - Console handler للـ development
   - File handler مع rotation (RotatingFileHandler)
   - Syslog handler للـ production
   - External service handler (optional: Datadog, Sentry)

3. Log Formatters:
   - Development: readable format with colors
   - Production: JSON format
   - Include: timestamp, level, logger_name, message, context

4. Context Manager للإضافة context للـ logs:
```python
with log_context(user_id=123, action="create_patient"):
    logger.info("patient.created", patient_id=456)
```

5. Performance Logging:
   - Decorator @log_performance لقياس وقت التنفيذ
   - تسجيل الـ slow queries تلقائياً
   - تسجيل الـ slow endpoints

6. Audit Logging:
   - تسجيل جميع العمليات الحساسة
   - Include: who, what, when, where, why
   - Store in separate audit_logs table

7. Log Levels Strategy:
   - DEBUG: تفاصيل للـ debugging
   - INFO: أحداث عادية
   - WARNING: أحداث غير متوقعة لكن يمكن التعامل معها
   - ERROR: أخطاء تحتاج تدخل
   - CRITICAL: فشل في النظام

8. قم بإنشاء ملف backend/models/audit_log.py:
   - Model لحفظ الـ audit logs
   - Indexes على user_id, action, timestamp
   - Retention policy (حذف السجلات القديمة)

9. أنشئ middleware للـ logging:
   - class RequestLoggingMiddleware
   - يسجل كل request/response
   - يسجل الوقت المستغرق
   - يسجل الـ status code
   - يسجل الـ user info

10. أضف tests في tests/test_logging.py

متطلبات:
- يجب دعم log rotation (حجم أقصى 100MB per file)
- يجب حفظ آخر 10 log files
- يجب تشفير الـ audit logs
- يجب دعم async logging
- أضف configuration من environment variables
```

---

### 1.4 إضافة Health Checks متقدمة

**الملف:** `backend/routers/health.py` (ملف جديد)

**البرومت:**
```
أنشئ ملف backend/routers/health.py يحتوي على health checks شاملة:

1. Basic Health Check:
   - GET /health
   - يرجع 200 OK إذا كان التطبيق يعمل

2. Detailed Health Check:
   - GET /health/detailed
   - يفحص جميع المكونات:
     * Database (connection, query latency)
     * Redis (connection, ping)
     * AI Service (Groq API)
     * File Storage
     * External APIs
   - Response format:
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2024-01-27T10:00:00Z",
  "version": "2.0.5",
  "uptime_seconds": 3600,
  "checks": {
    "database": {
      "status": "up",
      "latency_ms": 5,
      "connections": {"active": 5, "total": 20}
    },
    "redis": {
      "status": "up",
      "latency_ms": 2,
      "memory_used_mb": 50
    },
    "ai_service": {
      "status": "up",
      "provider": "groq"
    },
    "disk_space": {
      "status": "up",
      "free_gb": 100,
      "total_gb": 500
    }
  }
}
```

3. Liveness Probe:
   - GET /health/live
   - للاستخدام مع Kubernetes
   - يتحقق فقط من أن التطبيق يعمل

4. Readiness Probe:
   - GET /health/ready
   - يتحقق من أن التطبيق جاهز لاستقبال requests
   - يفحص Database و Redis

5. أنشئ Class HealthChecker في backend/core/health.py:
   - Methods منفصلة لكل فحص
   - Timeout لكل فحص (5 seconds max)
   - Caching للنتائج (30 seconds)
   - Async implementation

6. أضف Metrics:
   - عدد الـ health checks
   - عدد الفحوصات الفاشلة
   - Latency لكل component

7. أنشئ Background Task:
   - يفحص صحة النظام كل دقيقة
   - يرسل تنبيهات عند فشل أي component
   - يحفظ التاريخ في database

8. أضف Configuration:
   - تفعيل/تعطيل كل فحص
   - Timeout values
   - Alert thresholds

9. أضف tests في tests/test_health.py:
   - Test all health endpoints
   - Test failed scenarios
   - Test timeouts
   - Test caching

10. حدّث main.py لتضمين الـ health router

متطلبات:
- يجب أن تكون الفحوصات non-blocking
- استخدم asyncio.timeout للحماية
- لا تعرض معلومات حساسة
- أضف authentication للـ detailed endpoint
```

---

### 1.5 إعداد Monitoring & Alerting

**الملفات الجديدة:**
- `backend/core/monitoring.py`
- `backend/core/alerts.py`
- `backend/monitoring/dashboard.py`

**البرومت:**
```
أنشئ نظام monitoring و alerting شامل:

## A. Monitoring System (backend/core/monitoring.py)

1. Prometheus Metrics:
```python
from prometheus_client import Counter, Histogram, Gauge, Info

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Business metrics
patients_created_total = Counter('patients_created_total', 'Total patients created')
appointments_scheduled_total = Counter('appointments_scheduled_total', 'Appointments scheduled')
ai_requests_total = Counter('ai_requests_total', 'AI requests', ['model', 'status'])
ai_tokens_used = Counter('ai_tokens_used', 'AI tokens consumed', ['model'])

# System metrics
active_users = Gauge('active_users', 'Currently active users')
db_connections_active = Gauge('db_connections_active', 'Active DB connections')
cache_hit_rate = Gauge('cache_hit_rate', 'Cache hit rate percentage')
queue_size = Gauge('queue_size', 'Task queue size', ['queue_name'])

# Application info
app_info = Info('app_info', 'Application information')
app_info.info({
    'version': '2.0.5',
    'environment': os.getenv('ENVIRONMENT', 'development')
})
```

2. Custom Metrics Collector:
```python
class MetricsCollector:
    def __init__(self):
        self.redis = Redis.from_url(settings.redis_url)
    
    async def collect_business_metrics(self):
        """Collect business metrics periodically"""
        # Active users in last 5 minutes
        # Database statistics
        # Queue statistics
        pass
    
    def track_request(self, method, endpoint, status, duration):
        """Track individual request"""
        pass
    
    def track_ai_usage(self, model, tokens, cost):
        """Track AI usage"""
        pass
```

3. Middleware للـ metrics:
```python
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response
```

## B. Alert System (backend/core/alerts.py)

1. Alert Manager Class:
```python
class AlertManager:
    def __init__(self):
        self.slack_webhook = settings.slack_webhook_url
        self.email_config = settings.email_config
        self.sms_config = settings.sms_config
    
    async def send_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        details: dict = None
    ):
        """Send alert through configured channels"""
        pass
    
    async def check_thresholds(self):
        """Check metric thresholds and alert if exceeded"""
        pass
```

2. Alert Levels:
```python
from enum import Enum

class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

3. Alert Rules:
```python
ALERT_RULES = [
    {
        "name": "high_error_rate",
        "condition": lambda metrics: metrics['error_rate'] > 5,  # 5%
        "level": AlertLevel.ERROR,
        "message": "Error rate exceeded 5%"
    },
    {
        "name": "slow_requests",
        "condition": lambda metrics: metrics['p95_latency'] > 2.0,  # 2 seconds
        "level": AlertLevel.WARNING,
        "message": "P95 latency exceeded 2 seconds"
    },
    {
        "name": "database_connection_pool_exhausted",
        "condition": lambda metrics: metrics['db_pool_usage'] > 90,  # 90%
        "level": AlertLevel.CRITICAL,
        "message": "Database connection pool near exhaustion"
    }
]
```

4. Integration Channels:
   - Slack webhook
   - Email (SMTP)
   - SMS (Twilio)
   - PagerDuty
   - Custom webhooks

## C. Monitoring Dashboard (backend/monitoring/dashboard.py)

1. Create FastAPI router with monitoring endpoints:
   - GET /monitoring/metrics (Prometheus format)
   - GET /monitoring/dashboard (HTML dashboard)
   - GET /monitoring/alerts (Alert history)
   - GET /monitoring/reports (Daily/Weekly reports)

2. Dashboard Features:
   - Real-time metrics display
   - Charts for key metrics
   - Alert history
   - System health overview
   - Top endpoints by traffic
   - Slow queries list
   - AI usage statistics

3. Reports:
   - Daily summary report
   - Weekly performance report
   - Monthly cost analysis
   - Automated email delivery

## D. Background Tasks

1. Create periodic tasks:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=5)
async def collect_metrics():
    """Collect metrics every 5 minutes"""
    pass

@scheduler.scheduled_job('interval', minutes=1)
async def check_alerts():
    """Check alert conditions every minute"""
    pass

@scheduler.scheduled_job('cron', hour=9, minute=0)
async def send_daily_report():
    """Send daily report at 9 AM"""
    pass

scheduler.start()
```

## E. Configuration

أنشئ ملف backend/monitoring/config.py:
```python
class MonitoringConfig(BaseSettings):
    # Prometheus
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    
    # Alerts
    slack_webhook_url: str | None = None
    alert_email: str | None = None
    pagerduty_api_key: str | None = None
    
    # Thresholds
    error_rate_threshold: float = 5.0
    latency_p95_threshold: float = 2.0
    cpu_threshold: float = 80.0
    memory_threshold: float = 85.0
    
    # Reports
    daily_report_enabled: bool = True
    daily_report_email: str | None = None
```

## F. Tests

أنشئ tests/test_monitoring.py:
- Test metrics collection
- Test alert triggering
- Test integrations
- Test dashboard endpoints

## G. Documentation

أنشئ MONITORING.md:
- كيفية إعداد Prometheus
- كيفية إعداد Grafana
- قائمة بجميع الـ metrics
- Alert rules configuration
- Dashboard setup
- Troubleshooting guide

متطلبات:
- يجب أن يعمل النظام بدون Prometheus (graceful degradation)
- يجب حفظ metrics في Redis كـ backup
- يجب أن تكون جميع العمليات async
- يجب إضافة rate limiting على alert sending
- يجب تجنب alert fatigue (تجميع التنبيهات المتشابهة)
```

---

## المرحلة 2: التحسينات عالية الأولوية (High Priority) 🟡

### 2.1 تحسين التوثيق

**الملفات:**
- `README.md`
- `docs/API.md`
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docs/CONTRIBUTING.md`

**البرومت:**
```
قم بإنشاء توثيق شامل للمشروع:

## A. تحديث README.md الرئيسي

يجب أن يحتوي على:

1. Header جذاب:
   - اسم المشروع
   - Badges (build status, coverage, version, license)
   - وصف مختصر (2-3 جمل)
   - Screenshot/GIF للواجهة

2. جدول المحتويات:
   - روابط سريعة لجميع الأقسام

3. Features:
   - قائمة بالمميزات الرئيسية
   - أيقونات جذابة
   - روابط للتوثيق التفصيلي

4. Tech Stack:
   - جدول بالتقنيات المستخدمة
   - الإصدارات
   - الغرض من كل تقنية

5. Quick Start:
   - متطلبات النظام
   - خطوات التثبيت (copy-paste ready)
   - كيفية تشغيل المشروع
   - أول API call للتجربة

6. Project Structure:
   - شجرة الملفات مع شرح كل مجلد
   ```
   backend/
   ├── ai/              # AI agent module
   │   ├── agent/       # Core orchestration
   │   ├── tools/       # Tool definitions
   │   └── analytics/   # Usage tracking
   ├── models/          # SQLAlchemy models
   ├── routers/         # API endpoints
   ...
   ```

7. Configuration:
   - جميع Environment Variables
   - القيم الافتراضية
   - مثال على ملف .env

8. API Documentation:
   - رابط للـ Swagger UI
   - رابط للـ ReDoc
   - أمثلة على API calls الأساسية

9. Development:
   - كيفية إعداد البيئة التطويرية
   - كيفية تشغيل الاختبارات
   - كيفية المساهمة

10. Deployment:
    - خيارات النشر (Docker, Cloud, etc.)
    - روابط للتوثيق التفصيلي

11. License & Credits:
    - رخصة المشروع
    - المساهمون

## B. docs/API.md - توثيق API مفصل

1. Authentication:
   - شرح نظام المصادقة
   - كيفية الحصول على Token
   - مثال عملي

2. Endpoints بالتفصيل:
   لكل endpoint:
   - Description
   - Method & Path
   - Headers
   - Parameters
   - Request Body (مع مثال)
   - Response (مع أمثلة Success & Error)
   - Status Codes
   - Examples (cURL, Python, JavaScript)

3. Error Handling:
   - شرح نظام الأخطاء
   - Error Codes
   - مثال على كل نوع خطأ

4. Rate Limiting:
   - الحدود المسموحة
   - Headers للتحقق
   - كيفية التعامل مع التجاوز

5. Pagination:
   - كيفية استخدام pagination
   - Parameters
   - Response format

6. Filtering & Sorting:
   - كيفية فلترة النتائج
   - Query parameters المدعومة

## C. docs/ARCHITECTURE.md

1. Overview:
   - معمارية المشروع بشكل عام
   - Diagram للبنية

2. Design Principles:
   - Clean Architecture
   - SOLID Principles
   - DDD (Domain-Driven Design)

3. Layers:
   - شرح تفصيلي لكل طبقة
   - المسؤوليات
   - كيفية التفاعل بين الطبقات

4. Database Schema:
   - ERD Diagram
   - شرح الجداول الرئيسية
   - Relationships

5. AI Module Architecture:
   - كيف يعمل نظام AI
   - Flow diagram
   - Tool system
   - Security measures

6. Multi-Tenancy:
   - كيفية عزل البيانات
   - Tenant context
   - Best practices

7. Caching Strategy:
   - ما الذي يتم cache
   - Invalidation strategy
   - Redis usage

8. Security Architecture:
   - Authentication flow
   - Authorization (RBAC)
   - Data encryption
   - API security

## D. docs/DEPLOYMENT.md

1. Requirements:
   - الحد الأدنى من الموارد
   - الاعتمادات الخارجية

2. Environment Setup:
   - Production environment variables
   - Secrets management
   - Configuration checklist

3. Database Setup:
   - PostgreSQL installation & configuration
   - Migration strategy
   - Backup & restore

4. Docker Deployment:
   - Dockerfile explained
   - Docker Compose setup
   - Production considerations

5. Cloud Deployment:
   - AWS deployment guide
   - Azure deployment guide
   - GCP deployment guide
   - Heroku deployment guide

6. Kubernetes:
   - Kubernetes manifests
   - Helm charts
   - Scaling strategy

7. CI/CD:
   - GitHub Actions workflow
   - GitLab CI
   - Deployment pipeline

8. Monitoring:
   - Prometheus setup
   - Grafana dashboards
   - Log aggregation

9. Backup & Disaster Recovery:
   - Backup strategy
   - Recovery procedures
   - Testing backup

## E. docs/CONTRIBUTING.md

1. How to Contribute:
   - Fork & Clone
   - Branch naming
   - Commit messages

2. Development Setup:
   - Detailed steps
   - Common issues

3. Code Style:
   - PEP 8
   - Type hints
   - Docstrings

4. Testing:
   - كيفية كتابة الاختبارات
   - Coverage requirements
   - Running tests

5. Pull Request Process:
   - Checklist
   - Review process
   - Merging guidelines

6. Code Review Guidelines:
   - ما الذي نبحث عنه
   - Common issues

## F. docs/TROUBLESHOOTING.md

1. Common Issues:
   - المشاكل الشائعة وحلولها

2. FAQ:
   - أسئلة متكررة

3. Debug Mode:
   - كيفية تفعيل debug mode
   - Logging levels

4. Performance Issues:
   - كيفية تشخيص مشاكل الأداء
   - Common bottlenecks

## G. API Examples Collection

أنشئ مجلد docs/examples/ يحتوي على:
- Python examples
- JavaScript examples
- cURL examples
- Postman collection

متطلبات:
- استخدم Markdown formatting
- أضف diagrams (Mermaid or PlantUML)
- أضف code blocks with syntax highlighting
- اجعل جميع الأمثلة copy-paste ready
- تأكد من أن جميع الروابط تعمل
- استخدم لغة واضحة ومباشرة
- أضف emojis لجعل التوثيق أكثر جاذبية
```

---

### 2.2 زيادة تغطية الاختبارات

**البرومت:**
```
قم بإنشاء مجموعة اختبارات شاملة لزيادة التغطية إلى 80%+:

## A. Test Infrastructure (tests/conftest.py)

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database import Base, get_db
from backend.models import User, Tenant, Patient
from backend.auth import create_access_token

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def engine():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine):
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_tenant(db_session):
    tenant = Tenant(
        name="Dentix Clinic",
        subdomain="test",
        is_active=True
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant

@pytest.fixture
def test_user(db_session, test_tenant):
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        role="doctor",
        tenant_id=test_tenant.id,
        is_active=True
    )
    user.set_password("testpass123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    token = create_access_token({"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_user(db_session, test_tenant):
    user = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        role="admin",
        tenant_id=test_tenant.id,
        is_active=True
    )
    user.set_password("admin123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token({"sub": admin_user.username})
    return {"Authorization": f"Bearer {token}"}
```

## B. Unit Tests

### B.1 tests/unit/test_models.py
```python
def test_user_model_creation(db_session):
    """Test User model creation"""
    pass

def test_user_password_hashing(db_session):
    """Test password is hashed correctly"""
    pass

def test_user_password_verification(db_session):
    """Test password verification works"""
    pass

def test_patient_model_relationships(db_session):
    """Test Patient model relationships"""
    pass

# أضف tests لجميع Models
```

### B.2 tests/unit/test_services.py
```python
from backend.services import patient_service, auth_service

def test_create_patient_success(db_session, test_tenant):
    """Test successful patient creation"""
    pass

def test_create_patient_duplicate_email(db_session, test_tenant):
    """Test patient creation with duplicate email fails"""
    pass

def test_get_patient_by_id(db_session, test_tenant):
    """Test retrieving patient by ID"""
    pass

def test_update_patient(db_session, test_tenant):
    """Test updating patient information"""
    pass

def test_delete_patient(db_session, test_tenant):
    """Test soft delete of patient"""
    pass

# أضف tests لجميع Services
```

### B.3 tests/unit/test_utils.py
```python
def test_encryption_decryption():
    """Test encryption and decryption"""
    pass

def test_token_generation():
    """Test JWT token generation"""
    pass

def test_token_validation():
    """Test JWT token validation"""
    pass
```

## C. Integration Tests

### C.1 tests/integration/test_auth_endpoints.py
```python
def test_login_success(client, test_user):
    """Test successful login"""
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password(client, test_user):
    """Test login with wrong password"""
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "wrongpass"
    })
    assert response.status_code == 401

def test_login_nonexistent_user(client):
    """Test login with non-existent user"""
    pass

def test_get_current_user(client, auth_headers):
    """Test getting current user info"""
    pass

def test_logout(client, auth_headers):
    """Test logout"""
    pass

def test_refresh_token(client, auth_headers):
    """Test token refresh"""
    pass

def test_rate_limiting_auth(client):
    """Test rate limiting on auth endpoints"""
    pass
```

### C.2 tests/integration/test_patient_endpoints.py
```python
def test_create_patient(client, auth_headers):
    """Test creating a patient"""
    response = client.post(
        "/api/v1/patients/",
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "1234567890",
            "age": 30
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert "id" in data

def test_list_patients(client, auth_headers):
    """Test listing patients with pagination"""
    pass

def test_get_patient(client, auth_headers):
    """Test getting single patient"""
    pass

def test_update_patient(client, auth_headers):
    """Test updating patient"""
    pass

def test_delete_patient(client, auth_headers):
    """Test deleting patient"""
    pass

def test_search_patients(client, auth_headers):
    """Test searching patients"""
    pass

# أضف tests لجميع Patient endpoints
```

### C.3 tests/integration/test_appointment_endpoints.py
### C.4 tests/integration/test_ai_endpoints.py
### C.5 tests/integration/test_billing_endpoints.py
```
اتبع نفس النمط لجميع الـ endpoints
```

## D. Performance Tests

### tests/performance/test_load.py
```python
import pytest
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and get token"""
        response = self.client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpass123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def list_patients(self):
        self.client.get("/api/v1/patients/", headers=self.headers)
    
    @task(1)
    def create_patient(self):
        self.client.post(
            "/api/v1/patients/",
            json={"name": "Test", "email": "test@test.com"},
            headers=self.headers
        )
    
    @task(2)
    def get_patient(self):
        self.client.get("/api/v1/patients/1", headers=self.headers)
```

## E. Security Tests

### tests/security/test_authentication.py
```python
def test_unauthenticated_access_denied(client):
    """Test that protected endpoints require authentication"""
    pass

def test_invalid_token_rejected(client):
    """Test that invalid tokens are rejected"""
    pass

def test_expired_token_rejected(client):
    """Test that expired tokens are rejected"""
    pass

def test_sql_injection_prevented(client, auth_headers):
    """Test SQL injection prevention"""
    pass

def test_xss_prevented(client, auth_headers):
    """Test XSS prevention"""
    pass
```

### tests/security/test_authorization.py
```python
def test_rbac_doctor_cannot_access_admin(client, auth_headers):
    """Test that doctor role cannot access admin endpoints"""
    pass

def test_rbac_nurse_cannot_delete_patient(client, auth_headers):
    """Test that nurse role cannot delete patients"""
    pass

def test_tenant_isolation(client, auth_headers):
    """Test that tenant data is isolated"""
    pass
```

## F. End-to-End Tests

### tests/e2e/test_patient_workflow.py
```python
def test_complete_patient_workflow(client, auth_headers):
    """Test complete patient management workflow"""
    # 1. Create patient
    # 2. Schedule appointment
    # 3. Add treatment
    # 4. Generate bill
    # 5. Record payment
    pass
```

## G. Test Configuration

### pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --cov=backend
    --cov-report=html
    --cov-report=term-missing
    --cov-report=xml
    --cov-fail-under=80
    --maxfail=1
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    security: Security tests
```

## H. Coverage Report

### .coveragerc
```ini
[run]
source = backend
omit =
    */tests/*
    */migrations/*
    */__pycache__/*
    */venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

## I. Test Running Commands

أنشئ ملف tests/README.md يشرح:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test
pytest tests/unit/test_models.py::test_user_creation

# Run by marker
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Run in parallel
pytest -n auto

# Generate HTML report
pytest --html=report.html
```

## J. Continuous Testing

أنشئ GitHub Actions workflow (.github/workflows/tests.yml):
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
          REDIS_URL: redis://localhost:6379
        run: |
          pytest --cov --cov-fail-under=80
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

متطلبات:
- يجب أن تغطي الاختبارات 80%+ من الكود
- يجب أن تكون سريعة (< 5 minutes للكل)
- يجب أن تكون isolated (لا تعتمد على بعضها)
- يجب أن تكون deterministic (نفس النتيجة دائماً)
- استخدم fixtures للبيانات المشتركة
- استخدم mocks للخدمات الخارجية
- أضف docstrings لكل test
```

---

### 2.3 إضافة CI/CD Pipeline

**الملفات:**
- `.github/workflows/ci.yml`
- `.github/workflows/cd.yml`
- `.github/workflows/security.yml`

**البرومت:**
```
أنشئ CI/CD pipeline شامل باستخدام GitHub Actions:

## A. Continuous Integration (.github/workflows/ci.yml)

```yaml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

env:
  PYTHON_VERSION: '3.11'

jobs:
  code-quality:
    name: Code Quality Checks
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install ruff mypy black isort
      
      - name: Run Ruff (Linting)
        run: ruff check backend/
      
      - name: Run Black (Formatting)
        run: black --check backend/
      
      - name: Run isort (Import Sorting)
        run: isort --check-only backend/
      
      - name: Run MyPy (Type Checking)
        run: mypy backend/ --ignore-missing-imports
  
  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Bandit (Security)
        run: |
          pip install bandit
          bandit -r backend/ -f json -o bandit-report.json
      
      - name: Run Safety (Dependency Check)
        run: |
          pip install safety
          safety check --json
      
      - name: Run Trivy (Vulnerability Scanner)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
  
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    needs: [code-quality]
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio pytest-xdist
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379
          ENCRYPTION_KEY: ${{ secrets.TEST_ENCRYPTION_KEY }}
        run: |
          pytest --cov=backend --cov-report=xml --cov-report=html -n auto
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
      
      - name: Archive coverage report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: htmlcov/
  
  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [test, security-scan]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Build Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./backend/Dockerfile
          push: false
          tags: dentix-backend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Test Docker image
        run: |
          docker run --rm dentix-backend:${{ github.sha }} python -c "import backend; print('OK')"
```

## B. Continuous Deployment (.github/workflows/cd.yml)

```yaml
name: CD Pipeline

on:
  push:
    branches: [ main ]
    tags:
      - 'v*'

jobs:
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment:
      name: staging
      url: https://dentix-dentix-staging.hf.space
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build, tag, and push image to ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: dentix-backend
          IMAGE_TAG: staging-${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG -f backend/Dockerfile .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster dentix-staging \
            --service backend \
            --force-new-deployment
      
      - name: Wait for deployment
        run: |
          aws ecs wait services-stable \
            --cluster dentix-staging \
            --services backend
      
      - name: Run smoke tests
        run: |
          curl -f https://dentix-dentix-staging.hf.space/health || exit 1
      
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Staging deployment completed'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
  
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    needs: [deploy-staging]
    environment:
      name: production
      url: https://dentix-dentix.hf.space
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false
      
      - name: Deploy to Production ECS
        # Similar to staging but with production cluster
        run: |
          # Production deployment steps
      
      - name: Run production smoke tests
        run: |
          curl -f https://dentix-dentix.hf.space/health || exit 1
      
      - name: Rollback on failure
        if: failure()
        run: |
          # Rollback logic
```

## C. Security Scanning (.github/workflows/security.yml)

```yaml
name: Security Scanning

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  codeql:
    name: CodeQL Analysis
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v2
        with:
          languages: python
      
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v2
  
  dependency-review:
    name: Dependency Review
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Check for known vulnerabilities
        run: |
          pip install pip-audit
          pip-audit -r requirements.txt
  
  secret-scanning:
    name: Secret Scanning
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          head: HEAD
```

## D. Additional Workflows

### D.1 .github/workflows/dependency-update.yml
```yaml
name: Dependency Update

on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday

jobs:
  update-dependencies:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Update dependencies
        run: |
          pip install pip-tools
          pip-compile --upgrade requirements.txt
      
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          commit-message: 'chore: update dependencies'
          title: 'chore: Weekly dependency update'
          body: 'Automated dependency update'
          branch: dependency-update
```

### D.2 .github/workflows/performance.yml
```yaml
name: Performance Tests

on:
  schedule:
    - cron: '0 0 * * *'  # Daily
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Locust load tests
        run: |
          pip install locust
          locust -f tests/performance/test_load.py --headless -u 100 -r 10 --run-time 5m
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: locust_report.html
```

## E. Pre-commit Hooks (.pre-commit-config.yaml)

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  
  - repo: https://github.com/psf/black
    rev: 23.10.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

## F. Setup Instructions

أنشئ ملف CICD_SETUP.md:
```markdown
# CI/CD Setup Guide

## Prerequisites
1. GitHub repository
2. AWS account (for deployment)
3. DockerHub account (optional)

## Setup Steps

### 1. GitHub Secrets
Add these secrets to your repository:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `TEST_ENCRYPTION_KEY`
- `SLACK_WEBHOOK`

### 2. Enable GitHub Actions
- Go to repository Settings > Actions > General
- Enable "Allow all actions"

### 3. Branch Protection
- Go to Settings > Branches
- Add rule for `main` branch:
  - Require pull request reviews
  - Require status checks to pass
  - Require branches to be up to date

### 4. Install Pre-commit Hooks
```bash
pip install pre-commit
pre-commit install
```

### 5. Test Workflow
- Push to develop branch
- Check Actions tab for results
```

متطلبات:
- يجب أن تعمل جميع workflows بدون أخطاء
- يجب أن تكون fast (< 10 minutes)
- يجب أن تكون secure (no secrets in logs)
- يجب أن تكون reliable (retry on failure)
- أضف notifications (Slack/Email)
- أضف rollback mechanism
```

---

### 2.4 تحسين Database Indexes

**البرومت:**
```
قم بإضافة indexes محسّنة لجميع Models لتحسين أداء الاستعلامات:

## A. تحليل الاستعلامات الحالية

أولاً، أنشئ ملف backend/database/query_analyzer.py:
```python
from sqlalchemy import event, create_engine
from sqlalchemy.engine import Engine
import logging
import time

# Query timing logger
logger = logging.getLogger("sqlalchemy.query_timing")

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())
    logger.debug("Start Query: %s", statement)

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 0.1:  # Log slow queries (> 100ms)
        logger.warning("Slow Query (%.2f sec): %s", total, statement)

def analyze_slow_queries():
    """Analyze and report slow queries"""
    # Implementation to collect and report slow queries
    pass
```

## B. إضافة Indexes للـ Models

### B.1 تحديث backend/models/patient.py
```python
from sqlalchemy import Index

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)  # للبحث
    email = Column(String, unique=True, index=True)  # للبحث والتحقق
    phone = Column(String, index=True)  # للبحث
    national_id = Column(String, unique=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    is_active = Column(Boolean, default=True, index=True)  # للفلترة
    created_at = Column(DateTime, default=datetime.utcnow, index=True)  # للترتيب
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Composite indexes for common queries
    __table_args__ = (
        # البحث بالاسم ضمن tenant معين
        Index('idx_patient_name_tenant', 'name', 'tenant_id'),
        
        # المرضى النشطين لكل tenant
        Index('idx_active_patients_tenant', 'tenant_id', 'is_active'),
        
        # البحث بالهاتف ضمن tenant
        Index('idx_patient_phone_tenant', 'phone', 'tenant_id'),
        
        # الترتيب حسب تاريخ الإنشاء
        Index('idx_patient_created', 'tenant_id', 'created_at'),
        
        # Full-text search index (PostgreSQL specific)
        Index(
            'idx_patient_search',
            'name', 'email', 'phone',
            postgresql_using='gin',
            postgresql_ops={
                'name': 'gin_trgm_ops',
                'email': 'gin_trgm_ops',
                'phone': 'gin_trgm_ops'
            }
        ),
    )
```

### B.2 تحديث backend/models/clinical.py (Appointment)
```python
class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    appointment_date = Column(DateTime, nullable=False, index=True)
    status = Column(String, default="scheduled", index=True)
    
    __table_args__ = (
        # مواعيد اليوم للطبيب
        Index('idx_appt_doctor_date', 'doctor_id', 'appointment_date'),
        
        # مواعيد المريض
        Index('idx_appt_patient', 'patient_id', 'appointment_date'),
        
        # المواعيد حسب الحالة
        Index('idx_appt_status_date', 'status', 'appointment_date', 'tenant_id'),
        
        # المواعيد القادمة
        Index('idx_upcoming_appts', 'tenant_id', 'appointment_date', 
              postgresql_where=text("appointment_date > NOW()")),
    )
```

### B.3 تحديث backend/models/financial.py
```python
class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(DateTime, default=datetime.utcnow, index=True)
    payment_method = Column(String, index=True)
    status = Column(String, default="completed", index=True)
    
    __table_args__ = (
        # المدفوعات حسب التاريخ
        Index('idx_payment_date', 'tenant_id', 'payment_date'),
        
        # المدفوعات للمريض
        Index('idx_payment_patient', 'patient_id', 'payment_date'),
        
        # المدفوعات حسب الطريقة
        Index('idx_payment_method', 'tenant_id', 'payment_method', 'payment_date'),
        
        # تجميع المدفوعات (reporting)
        Index('idx_payment_aggregation', 'tenant_id', 'payment_date', 'amount'),
    )
```

### B.4 تحديث backend/models/user.py
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    role = Column(String, index=True)  # للصلاحيات
    is_active = Column(Boolean, default=True, index=True)
    last_login = Column(DateTime, index=True)
    
    __table_args__ = (
        # المستخدمين النشطين حسب الدور
        Index('idx_user_role_active', 'tenant_id', 'role', 'is_active'),
        
        # آخر تسجيل دخول
        Index('idx_user_last_login', 'tenant_id', 'last_login'),
    )
```

## C. Migration للـ Indexes

أنشئ ملف backend/migrations/add_indexes.py:
```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    """Add indexes for performance"""
    
    # Patient indexes
    op.create_index('idx_patient_name_tenant', 'patients', ['name', 'tenant_id'])
    op.create_index('idx_active_patients_tenant', 'patients', ['tenant_id', 'is_active'])
    op.create_index('idx_patient_phone_tenant', 'patients', ['phone', 'tenant_id'])
    
    # Enable pg_trgm extension for fuzzy search (PostgreSQL)
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    
    # Full-text search index
    op.execute("""
        CREATE INDEX idx_patient_search ON patients 
        USING gin (name gin_trgm_ops, email gin_trgm_ops, phone gin_trgm_ops)
    """)
    
    # Appointment indexes
    op.create_index('idx_appt_doctor_date', 'appointments', ['doctor_id', 'appointment_date'])
    op.create_index('idx_appt_patient', 'appointments', ['patient_id', 'appointment_date'])
    
    # Partial index for upcoming appointments
    op.execute("""
        CREATE INDEX idx_upcoming_appts ON appointments (tenant_id, appointment_date)
        WHERE appointment_date > NOW()
    """)
    
    # Payment indexes
    op.create_index('idx_payment_date', 'payments', ['tenant_id', 'payment_date'])
    op.create_index('idx_payment_aggregation', 'payments', 
                   ['tenant_id', 'payment_date', 'amount'])

def downgrade():
    """Remove indexes"""
    op.drop_index('idx_patient_name_tenant')
    op.drop_index('idx_active_patients_tenant')
    # ... drop all indexes
```

## D. Query Optimization

أنشئ ملف backend/database/optimizations.py:
```python
from sqlalchemy.orm import joinedload, selectinload, subqueryload

class QueryOptimizer:
    """Helper for optimizing common queries"""
    
    @staticmethod
    def get_patients_with_appointments(db, tenant_id):
        """Optimized query to get patients with their appointments"""
        return db.query(Patient).options(
            selectinload(Patient.appointments)
        ).filter(
            Patient.tenant_id == tenant_id
        ).all()
    
    @staticmethod
    def get_appointment_with_details(db, appointment_id):
        """Get appointment with all related data in one query"""
        return db.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor),
            selectinload(Appointment.treatments)
        ).filter(
            Appointment.id == appointment_id
        ).first()
    
    @staticmethod
    def search_patients_fuzzy(db, tenant_id, search_term):
        """Fuzzy search using trigram similarity"""
        from sqlalchemy import func
        
        return db.query(Patient).filter(
            Patient.tenant_id == tenant_id,
            func.similarity(Patient.name, search_term) > 0.3
        ).order_by(
            func.similarity(Patient.name, search_term).desc()
        ).limit(20).all()
```

## E. Monitoring

أنشئ ملف backend/database/monitoring.py:
```python
import psycopg2
from typing import List, Dict

class DatabaseMonitor:
    """Monitor database performance"""
    
    def get_missing_indexes(self) -> List[Dict]:
        """Find tables that might benefit from indexes"""
        query = """
        SELECT
            schemaname,
            tablename,
            attname,
            n_distinct,
            correlation
        FROM pg_stats
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        AND n_distinct > 100
        AND abs(correlation) < 0.1
        ORDER BY n_distinct DESC
        LIMIT 20
        """
        # Execute and return results
    
    def get_index_usage(self) -> List[Dict]:
        """Check which indexes are actually being used"""
        query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan as scans,
            idx_tup_read as tuples_read,
            idx_tup_fetch as tuples_fetched
        FROM pg_stat_user_indexes
        ORDER BY idx_scan DESC
        """
        # Execute and return results
    
    def get_slow_queries(self, min_duration_ms=100) -> List[Dict]:
        """Get slow queries from pg_stat_statements"""
        query = f"""
        SELECT
            query,
            calls,
            total_time,
            mean_time,
            max_time
        FROM pg_stat_statements
        WHERE mean_time > {min_duration_ms}
        ORDER BY total_time DESC
        LIMIT 20
        """
        # Execute and return results
```

## F. Testing

أنشئ ملف tests/test_indexes.py:
```python
def test_patient_search_performance(db_session, benchmark):
    """Test that patient search is fast with indexes"""
    # Create 10000 test patients
    patients = [
        Patient(name=f"Patient {i}", tenant_id=1)
        for i in range(10000)
    ]
    db_session.bulk_save_objects(patients)
    db_session.commit()
    
    # Benchmark search
    def search():
        return db_session.query(Patient).filter(
            Patient.name.like("%Patient 5%"),
            Patient.tenant_id == 1
        ).all()
    
    result = benchmark(search)
    assert len(result) > 0

def test_appointment_query_performance(db_session, benchmark):
    """Test appointment queries are optimized"""
    # Test implementation
    pass
```

## G. Documentation

أنشئ ملف DATABASE_OPTIMIZATION.md:
```markdown
# Database Optimization Guide

## Indexes Added

### Patient Table
- `idx_patient_name_tenant`: Name + Tenant ID (search)
- `idx_active_patients_tenant`: Tenant + Active status (filtering)
- `idx_patient_search`: Full-text search (GIN index)

### Appointment Table
- `idx_appt_doctor_date`: Doctor appointments by date
- `idx_upcoming_appts`: Future appointments only (partial index)

## Query Patterns

### DO ✓
```python
# Use indexes
patients = db.query(Patient).filter(
    Patient.tenant_id == tenant_id,
    Patient.is_active == True
).all()

# Use eager loading
patient = db.query(Patient).options(
    selectinload(Patient.appointments)
).first()
```

### DON'T ✗
```python
# Full table scan
patients = db.query(Patient).all()

# N+1 problem
for patient in patients:
    print(patient.appointments)  # Lazy load!
```

## Monitoring

Check index usage:
```sql
SELECT * FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

Find missing indexes:
```sql
SELECT * FROM pg_stat_user_tables 
WHERE schemaname = 'public'
AND seq_scan > 1000
ORDER BY seq_scan DESC;
```
```

متطلبات:
- يجب إنشاء indexes لجميع Foreign Keys
- يجب إنشاء composite indexes للاستعلامات الشائعة
- يجب استخدام partial indexes عند الحاجة
- يجب قياس التحسين في الأداء (قبل/بعد)
- يجب توثيق كل index وغرضه
- يجب مراقبة استخدام الـ indexes
```

---

### 2.5 تحسين Rate Limiting

**البرومت:**
```
قم بإنشاء نظام rate limiting متقدم مع مرونة عالية:

## A. Rate Limiter Class (backend/core/advanced_limiter.py)

```python
from redis import Redis
from typing import Optional, Callable
from functools import wraps
from fastapi import Request, HTTPException
import time

class RateLimiter:
    """Advanced rate limiter with multiple strategies"""
    
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url, decode_responses=True)
    
    def fixed_window(
        self,
        key_func: Callable,
        max_requests: int,
        window_seconds: int
    ):
        """Fixed window rate limiting"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                request = kwargs.get('request') or args[0]
                key = f"rate_limit:fixed:{key_func(request)}"
                
                current = self.redis.incr(key)
                if current == 1:
                    self.redis.expire(key, window_seconds)
                
                if current > max_requests:
                    retry_after = self.redis.ttl(key)
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded",
                        headers={"Retry-After": str(retry_after)}
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def sliding_window(
        self,
        key_func: Callable,
        max_requests: int,
        window_seconds: int
    ):
        """Sliding window rate limiting (more accurate)"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                request = kwargs.get('request') or args[0]
                key = f"rate_limit:sliding:{key_func(request)}"
                now = time.time()
                window_start = now - window_seconds
                
                # Remove old entries
                self.redis.zremrangebyscore(key, 0, window_start)
                
                # Count requests in window
                current_requests = self.redis.zcard(key)
                
                if current_requests >= max_requests:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded"
                    )
                
                # Add current request
                self.redis.zadd(key, {str(now): now})
                self.redis.expire(key, window_seconds)
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def token_bucket(
        self,
        key_func: Callable,
        capacity: int,
        refill_rate: float  # tokens per second
    ):
        """Token bucket rate limiting (smooth traffic)"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                request = kwargs.get('request') or args[0]
                key = f"rate_limit:bucket:{key_func(request)}"
                now = time.time()
                
                # Get current bucket state
                bucket = self.redis.hgetall(key)
                
                if bucket:
                    tokens = float(bucket['tokens'])
                    last_update = float(bucket['last_update'])
                else:
                    tokens = capacity
                    last_update = now
                
                # Refill tokens
                time_passed = now - last_update
                tokens = min(capacity, tokens + time_passed * refill_rate)
                
                if tokens < 1:
                    wait_time = (1 - tokens) / refill_rate
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded",
                        headers={"Retry-After": str(int(wait_time) + 1)}
                    )
                
                # Consume token
                tokens -= 1
                
                # Save state
                self.redis.hset(key, mapping={
                    'tokens': str(tokens),
                    'last_update': str(now)
                })
                self.redis.expire(key, 3600)  # 1 hour
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def adaptive(
        self,
        key_func: Callable,
        base_limit: int,
        window_seconds: int
    ):
        """Adaptive rate limiting based on system load"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Get system load
                load = self._get_system_load()
                
                # Adjust limit based on load
                if load > 0.8:
                    adjusted_limit = int(base_limit * 0.5)
                elif load > 0.6:
                    adjusted_limit = int(base_limit * 0.75)
                else:
                    adjusted_limit = base_limit
                
                # Apply fixed window with adjusted limit
                # ...implementation
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def _get_system_load(self) -> float:
        """Get current system load (0.0 - 1.0)"""
        # Implementation: check CPU, memory, active connections
        return 0.5  # Placeholder

# Initialize limiter
rate_limiter = RateLimiter(settings.redis_url)

# Key functions
def user_key(request: Request) -> str:
    """Rate limit by user"""
    user = request.state.user
    return f"user:{user.id}"

def ip_key(request: Request) -> str:
    """Rate limit by IP"""
    return f"ip:{request.client.host}"

def tenant_key(request: Request) -> str:
    """Rate limit by tenant"""
    tenant_id = request.state.tenant_id
    return f"tenant:{tenant_id}"

def endpoint_key(request: Request) -> str:
    """Rate limit by endpoint"""
    return f"endpoint:{request.url.path}"
```

## B. Rate Limiting Tiers (backend/core/rate_limit_tiers.py)

```python
from enum import Enum

class RateLimitTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

TIER_LIMITS = {
    RateLimitTier.FREE: {
        "requests_per_minute": 10,
        "requests_per_hour": 100,
        "requests_per_day": 1000,
        "ai_requests_per_day": 10,
    },
    RateLimitTier.BASIC: {
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "requests_per_day": 10000,
        "ai_requests_per_day": 100,
    },
    RateLimitTier.PREMIUM: {
        "requests_per_minute": 300,
        "requests_per_hour": 5000,
        "requests_per_day": 50000,
        "ai_requests_per_day": 1000,
    },
    RateLimitTier.ENTERPRISE: {
        "requests_per_minute": -1,  # Unlimited
        "requests_per_hour": -1,
        "requests_per_day": -1,
        "ai_requests_per_day": -1,
    }
}

def get_tenant_tier(tenant_id: int) -> RateLimitTier:
    """Get tenant's subscription tier"""
    # Query database
    pass

def check_tier_limit(
    tenant_id: int,
    limit_type: str,
    current_usage: int
) -> bool:
    """Check if tenant exceeded tier limit"""
    tier = get_tenant_tier(tenant_id)
    limit = TIER_LIMITS[tier][limit_type]
    
    if limit == -1:  # Unlimited
        return True
    
    return current_usage < limit
```

## C. Application to Endpoints

```python
from backend.core.advanced_limiter import rate_limiter, user_key, tenant_key

# Different limits for different operations

# Authentication endpoints - strict
@router.post("/auth/login")
@rate_limiter.fixed_window(ip_key, max_requests=5, window_seconds=60)
async def login(request: Request, credentials: LoginRequest):
    pass

# Read operations - generous
@router.get("/patients/")
@rate_limiter.sliding_window(tenant_key, max_requests=100, window_seconds=60)
async def list_patients(request: Request):
    pass

# Write operations - moderate
@router.post("/patients/")
@rate_limiter.token_bucket(user_key, capacity=30, refill_rate=0.5)
async def create_patient(request: Request, patient: PatientCreate):
    pass

# AI operations - strict with tier-based limits
@router.post("/ai/chat")
async def ai_chat(request: Request, message: str):
    tenant_id = request.state.tenant_id
    
    # Check tier limit
    daily_usage = get_ai_usage_today(tenant_id)
    if not check_tier_limit(tenant_id, "ai_requests_per_day", daily_usage):
        raise HTTPException(
            status_code=402,  # Payment Required
            detail="AI request limit exceeded for your tier"
        )
    
    # Apply rate limit
    @rate_limiter.sliding_window(tenant_key, max_requests=10, window_seconds=60)
    async def _ai_chat():
        # AI logic
        pass
    
    return await _ai_chat()
```

## D. Rate Limit Middleware

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic rate limiting"""
    
    async def dispatch(self, request: Request, call_next):
        # Add rate limit headers to response
        response = await call_next(request)
        
        # Get current limits
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            key = f"user:{user_id}"
            remaining = self._get_remaining_requests(key)
            reset_time = self._get_reset_time(key)
            
            response.headers["X-RateLimit-Limit"] = "100"
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
```

## E. Admin Dashboard for Rate Limits

```python
@router.get("/admin/rate-limits/stats")
async def get_rate_limit_stats(
    current_user: User = Depends(require_admin)
):
    """Get rate limit statistics"""
    return {
        "top_users": get_top_users_by_requests(),
        "blocked_ips": get_blocked_ips(),
        "tier_usage": get_usage_by_tier(),
        "endpoint_traffic": get_traffic_by_endpoint()
    }

@router.post("/admin/rate-limits/whitelist")
async def add_to_whitelist(
    identifier: str,
    type: str,  # "ip", "user", "tenant"
    current_user: User = Depends(require_admin)
):
    """Add to rate limit whitelist"""
    redis.sadd(f"whitelist:{type}", identifier)
    return {"message": "Added to whitelist"}
```

## F. Configuration

```python
class RateLimitConfig(BaseSettings):
    # Global settings
    rate_limit_enabled: bool = True
    rate_limit_strategy: str = "sliding_window"  # fixed_window, sliding_window, token_bucket
    
    # Default limits
    default_requests_per_minute: int = 60
    default_requests_per_hour: int = 1000
    
    # Burst protection
    burst_protection_enabled: bool = True
    burst_threshold: int = 10  # requests in 1 second
    
    # Whitelist
    whitelisted_ips: List[str] = []
    whitelisted_user_ids: List[int] = []
```

## G. Monitoring & Alerts

```python
async def monitor_rate_limits():
    """Monitor rate limit violations"""
    while True:
        # Check for excessive violations
        violations = redis.zrange(
            "rate_limit:violations",
            0, -1,
            withscores=True
        )
        
        for identifier, count in violations:
            if count > 100:  # 100 violations in monitoring period
                await alert_manager.send_alert(
                    AlertLevel.WARNING,
                    "Excessive rate limit violations",
                    {"identifier": identifier, "count": count}
                )
        
        await asyncio.sleep(300)  # Check every 5 minutes
```

متطلبات:
- يجب دعم multiple strategies (fixed, sliding, token bucket)
- يجب دعم tier-based limits
- يجب إضافة rate limit headers للـ responses
- يجب تسجيل جميع الانتهاكات
- يجب إمكانية الـ whitelist
- يجب إضافة admin dashboard
- يجب إضافة monitoring و alerts
```

---

## ملخص البرومتات

هذه مجموعة شاملة من البرومتات المفصلة لتطبيق جميع التحسينات المقترحة. كل برومت يحتوي على:

1. **السياق الكامل**: شرح المشكلة والهدف
2. **الكود المثالي**: أمثلة عملية جاهزة للتطبيق
3. **المتطلبات**: قائمة واضحة بما يجب تحقيقه
4. **التوثيق**: كيفية توثيق التحسين
5. **الاختبارات**: كيفية اختبار التحسين

يمكنك استخدام كل برومت بشكل مستقل أو متسلسل حسب الأولويات المحددة في التقرير.

هل تريدني أن أكمل البرومتات للمراحل المتبقية (المرحلة 3 و 4)؟
