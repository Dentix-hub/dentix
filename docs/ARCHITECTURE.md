# 🏗️ Smart Clinic Architecture

> **Document Version**: 1.0  
> **Last Updated**: January 2026

---

## Overview

Smart Clinic is a multi-tenant SaaS application for clinic management with AI-powered features.

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│                    Deployed on Vercel                        │
└─────────────────────────────┬───────────────────────────────┘
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│                 Deployed on HuggingFace                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Routers   │  │  Services   │  │   AI Module         │ │
│  │  (30+ APIs) │  │  (Business) │  │  (Groq + RAG)       │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                     │            │
│         └────────────────┼─────────────────────┘            │
│                          │                                  │
│  ┌───────────────────────┴───────────────────────────────┐ │
│  │                    CRUD Layer                          │ │
│  │              (SQLAlchemy Models)                       │ │
│  └───────────────────────┬───────────────────────────────┘ │
└──────────────────────────┼──────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
      ┌─────────┐    ┌─────────┐    ┌─────────┐
      │PostgreSQL│   │  Redis  │    │ChromaDB │
      │ (Data)   │   │ (Cache) │    │ (RAG)   │
      └─────────┘    └─────────┘    └─────────┘
```

---

## Layer Architecture

### 1. Routers Layer (`backend/routers/`)
- HTTP endpoints definition
- Request validation
- Response formatting
- **No business logic**

### 2. Services Layer (`backend/services/`)
- Business logic
- Complex operations
- Cross-module coordination

### 3. CRUD Layer (`backend/crud/`)
- Database operations
- Simple queries

### 4. Models Layer (`backend/models/`)
- SQLAlchemy ORM models
- Database schema

---

## Key Modules

| Module | Purpose |
|--------|---------|
| `auth` | Authentication, JWT, 2FA |
| `patients` | Patient management |
| `appointments` | Scheduling |
| `payments` | Billing, invoices |
| `ai` | AI assistant, RAG |
| `admin` | Clinic administration |
| `system_admin` | Super admin functions |

---

## Multi-Tenancy

```
┌─────────────────────────────────────────┐
│              System Admin               │
│         (Cross-tenant access)           │
└─────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│Clinic A │   │Clinic B │   │Clinic C │
│(Tenant) │   │(Tenant) │   │(Tenant) │
├─────────┤   ├─────────┤   ├─────────┤
│ Users   │   │ Users   │   │ Users   │
│Patients │   │Patients │   │Patients │
│  Data   │   │  Data   │   │  Data   │
└─────────┘   └─────────┘   └─────────┘
```

- Each tenant has isolated data
- `tenant_id` on all models
- Automatic filtering via middleware

---

## Security Layers

1. **Authentication**: JWT tokens with refresh
2. **Authorization**: RBAC (6 roles)
3. **Encryption**: Fernet for sensitive data
4. **Rate Limiting**: SlowAPI
5. **Security Headers**: HSTS, CSP, XSS protection

---

## AI Module

```
User Message
    │
    ▼
┌─────────────────┐
│ Intent Detection │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│ Tools │ │  RAG  │
│Execute│ │Search │
└───────┘ └───────┘
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│ Response Gen    │
└─────────────────┘
```

**AI Governance Rules:**
- Read-only by default
- Confirmation for write actions
- Intent confidence threshold
- Audit logging

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TailwindCSS |
| Backend | FastAPI, Python 3.11 |
| Database | PostgreSQL |
| Cache | Redis |
| AI | Groq API, ChromaDB |
| Auth | JWT (python-jose) |
| Monitoring | Prometheus |

---

## File Structure

```
smart-clinic/
├── backend/
│   ├── main.py           # App entry
│   ├── database.py       # DB config
│   ├── models/           # SQLAlchemy models
│   ├── routers/          # API endpoints
│   ├── services/         # Business logic
│   ├── core/             # Config, security
│   └── middleware/       # Custom middleware
├── frontend/
│   ├── src/
│   │   ├── api/          # API client
│   │   ├── features/     # Feature modules
│   │   ├── shared/       # Shared components
│   │   └── pages/        # Route pages
└── docs/                  # Documentation
```
