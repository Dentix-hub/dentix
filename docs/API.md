# 📚 Smart Clinic API Documentation

> **Version**: 2.0.5  
> **Base URL**: `https://your-domain.com` or `http://localhost:8000`

---

## 🔐 Authentication

All protected endpoints require a Bearer token in the Authorization header:

```http
Authorization: Bearer <access_token>
```

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "yourpassword"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Refresh Token

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

---

## 👥 Patients

### List Patients

```http
GET /api/patients?skip=0&limit=20&search=ahmed
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| skip | int | Pagination offset (default: 0) |
| limit | int | Items per page (default: 20, max: 100) |
| search | string | Search by name, phone, or email |

### Create Patient

```http
POST /api/patients
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Ahmed Ali",
  "phone": "01234567890",
  "email": "ahmed@example.com",
  "age": 30,
  "gender": "male",
  "notes": "Optional medical notes"
}
```

### Get Patient

```http
GET /api/patients/{patient_id}
Authorization: Bearer <token>
```

### Update Patient

```http
PUT /api/patients/{patient_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Ahmed Mohamed Ali",
  "phone": "01234567891"
}
```

### Delete Patient

```http
DELETE /api/patients/{patient_id}
Authorization: Bearer <token>
```

---

## 📅 Appointments

### List Appointments

```http
GET /api/appointments?date=2026-01-27&status=scheduled
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| date | string | Filter by date (YYYY-MM-DD) |
| status | string | scheduled, completed, cancelled |
| patient_id | int | Filter by patient |

### Create Appointment

```http
POST /api/appointments
Authorization: Bearer <token>
Content-Type: application/json

{
  "patient_id": 1,
  "doctor_id": 2,
  "appointment_date": "2026-01-28T10:00:00",
  "notes": "Follow-up visit"
}
```

---

## 💰 Payments

### Create Payment

```http
POST /api/payments
Authorization: Bearer <token>
Content-Type: application/json

{
  "patient_id": 1,
  "amount": 500.00,
  "payment_method": "cash",
  "notes": "Consultation fee"
}
```

### Get Patient Balance

```http
GET /api/payments/balance/{patient_id}
Authorization: Bearer <token>
```

---

## 🤖 AI Assistant

### Chat with AI

```http
POST /ai/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "احجز موعد للمريض أحمد بكرة الساعة 10",
  "conversation_id": "optional-uuid"
}
```

**Response:**
```json
{
  "response": "تم حجز الموعد بنجاح...",
  "actions_taken": ["appointment_created"],
  "suggestions": ["هل تريد إضافة ملاحظات؟"]
}
```

---

## 🩺 Health Checks

### Basic Health

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.5",
  "timestamp": "2026-01-27T22:00:00Z"
}
```

### Detailed Health (Requires Auth)

```http
GET /health/detailed
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.5",
  "uptime_seconds": 3600,
  "checks": {
    "database": {"status": "up", "latency_ms": 5.2},
    "redis": {"status": "up", "latency_ms": 1.1},
    "ai_service": {"status": "up"},
    "disk_space": {"status": "up", "usage_percent": 45.2}
  }
}
```

### Kubernetes Probes

```http
GET /health/live   # Liveness probe
GET /health/ready  # Readiness probe
```

---

## ⚠️ Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "تفاصيل الخطأ",
    "trace_id": "abc123-uuid",
    "timestamp": "2026-01-27T22:00:00Z",
    "path": "/api/patients"
  }
}
```

**Error Codes:**
| Code | Status | Description |
|------|--------|-------------|
| VALIDATION_ERROR | 422 | Invalid input |
| AUTHENTICATION_ERROR | 401 | Invalid/expired token |
| AUTHORIZATION_ERROR | 403 | Permission denied |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |

---

## 🔑 Roles & Permissions

| Role | Description |
|------|-------------|
| super_admin | Full system access |
| admin | Clinic admin (tenant-level) |
| doctor | View/manage patients, appointments |
| receptionist | Manage appointments, basic patient info |
| nurse | View patients, add notes |
| accountant | Manage payments, reports |
| patient | View own records only |

---

## 📊 Rate Limits

| Endpoint Type | Limit |
|---------------|-------|
| Authentication | 5 requests/minute |
| General API | 100 requests/minute |
| AI Endpoints | 20 requests/minute |

---

## 📌 Notes

- All dates are in ISO 8601 format
- All responses are JSON
- Arabic language fully supported
- Multi-tenant: data isolated per clinic
