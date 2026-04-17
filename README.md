---
title: Dentix — Smart Clinic Management
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 7860
---

# Dentix — Smart Clinic Management System

A comprehensive, multi-tenant dental clinic management platform with AI-powered features, built for scalability and security.

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI (Python 3.11+), SQLAlchemy ORM, Alembic |
| **Frontend** | React 18 + Vite, TailwindCSS |
| **Database** | PostgreSQL (Neon Serverless) |
| **Cache** | Redis (optional, falls back to in-memory) |
| **AI** | Groq API (LLaMA 3), ChromaDB (RAG) |
| **Auth** | JWT with refresh token rotation |
| **Monitoring** | Sentry, Prometheus metrics |
| **CI/CD** | GitHub Actions |

## 🏗 Architecture

```
Request → Middleware → Router → Service → CRUD → Database
                        ↓
                    RBAC Check
                  (permissions.py)
```

### Layer Responsibilities

| Layer | Path | Purpose |
|-------|------|---------|
| **Routers** | `backend/routers/` | HTTP endpoints, request validation, response formatting |
| **Services** | `backend/services/` | Business logic, cross-module coordination |
| **CRUD** | `backend/crud/` | Database operations, simple queries |
| **Models** | `backend/models/` | SQLAlchemy ORM definitions |
| **Schemas** | `backend/schemas/` | Pydantic request/response models |
| **Core** | `backend/core/` | Config, security, permissions, caching |

> Full architecture documentation: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## 🚀 Features

- **Multi-tenant Architecture**: Complete data isolation per clinic via `tenant_scope.py`
- **RBAC (10 Roles)**: Super Admin, Admin, Manager, Doctor, Receptionist, Nurse, Accountant, Assistant, Patient, Guest
- **AI-powered Assistant**: Natural language clinical queries via Groq + tool execution
- **Patient Management**: Full records, dental charts, attachments, prescriptions
- **Appointment Scheduling**: Conflict detection, doctor-based filtering
- **Treatment Tracking**: Price snapshots, automatic stock deduction
- **Financial Module**: Payments, expenses, salaries, invoices, insurance pricing
- **Inventory System**: Smart material learning, batch tracking, stock movements
- **Laboratory Management**: Order lifecycle (create → send → receive → complete)
- **Insurance & Pricing**: Multiple price lists, copay calculations, coverage limits

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (or Neon DB URL)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, SECRET_KEY, etc.

# Run database migrations
python -m alembic upgrade head

# Start the server
uvicorn backend.main:app --reload --port 7860
```

### Frontend Setup
```bash
cd frontend
npm install

# Configure environment
cp .env.example .env

# Start development server
npm run dev
```

### Environment Variables

See `.env.example` for the complete list. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | JWT signing key |
| `GROQ_API_KEY` | ❌ | AI assistant (optional) |
| `REDIS_URL` | ❌ | Cache (falls back to memory) |
| `FRONTEND_URL` | ✅ | CORS origin |
| `CLOUDINARY_URL` | ❌ | File uploads |

## 🛡️ Security

- **Authentication**: JWT with refresh token rotation + account lockout
- **Authorization**: Granular RBAC with 20+ permissions
- **Multi-tenancy**: Automatic query filtering via SQLAlchemy event listener
- **Password Policy**: zxcvbn strength check + complexity requirements
- **Rate Limiting**: SlowAPI on sensitive endpoints
- **Audit Logging**: All write operations logged
- **Input Validation**: Pydantic V2 schemas on all endpoints

## 🧪 Testing

### Backend
```bash
cd backend

# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=backend --cov-report=html

# Run specific test suite
python -m pytest tests/test_rbac_complete.py -v
python -m pytest tests/services/ -v
```

### Test Suites

| Suite | File | Coverage |
|-------|------|----------|
| RBAC (112 scenarios) | `test_rbac_complete.py` | Permissions matrix |
| Tenant Isolation | `test_tenant_isolation_complete.py` | Cross-tenant leaks |
| Tenant Scope | `test_tenant_scope_verification.py` | Model audit |
| Treatment Service | `tests/services/test_treatment_service.py` | Business logic |
| Appointment Service | `tests/services/test_appointment_service.py` | Scheduling |
| Insurance Pricing | `tests/services/test_pricing_insurance.py` | Copay/coverage |

### CI Pipeline
On every push to `main`:
- `pytest` with coverage threshold (70%)
- `bandit` security scan (no HIGH findings)
- `safety` dependency check

## 📖 API Documentation

- **Interactive Docs**: `http://localhost:7860/docs` (Swagger UI)
- **ReDoc**: `http://localhost:7860/redoc`
- **OpenAPI Spec**: [`docs/api-spec.json`](docs/api-spec.json)

## 📁 Project Structure

```
dentix/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # DB engine & session
│   ├── ai/                  # AI agent, tools, RAG
│   ├── core/                # Config, permissions, cache, response
│   ├── crud/                # Database operations
│   ├── middleware/           # Auth, logging, tenant
│   ├── models/              # SQLAlchemy ORM models
│   ├── routers/             # API endpoints (30+ routers)
│   ├── schemas/             # Pydantic validation models
│   ├── services/            # Business logic layer (25+ services)
│   ├── tasks/               # Background jobs
│   ├── tests/               # pytest test suites
│   └── utils/               # Helpers (audit, encryption)
├── frontend/
│   ├── src/
│   │   ├── api/             # API client (Axios)
│   │   ├── components/      # Reusable UI
│   │   ├── contexts/        # React context (Auth, Theme)
│   │   ├── features/        # Feature modules
│   │   ├── hooks/           # Custom hooks
│   │   ├── pages/           # Route pages
│   │   └── shared/          # Shared UI components
│   └── vite.config.js
├── docs/                    # Architecture & API docs
├── .github/workflows/       # CI pipeline
└── .env.example             # Environment template
```

## 📄 License

This project is licensed under the MIT License.

## 📞 Support

For support, please open an issue in the GitHub repository.