<!-- CLASSIFICATION: ARCHITECTURE-REFERENCE -->
# 🏥 Dentix Project Technical Guide (Subordinate Architectural Reference)

> **Document Classification**: `ARCHITECTURE-REFERENCE`
> **Authority Status**: SUBORDINATE REFERENCE ONLY
>
> **GOVERNANCE & WORKFLOW BOUNDARIES**:
> 1. This document serves as an engineering and architecture reference for the Dentix codebase.
> 2. It does **NOT** define the development, branching, testing, PR, or release lifecycle. The sole development lifecycle authority is `docs/engineering/DEVELOPMENT_WORKFLOW.md`.
> 3. This document **CANNOT override `PROJECT_STANDARDS.md`** (canonical architecture authority).
> 4. This document **CANNOT override `docs/engineering/DEVELOPMENT_WORKFLOW.md`** (canonical development workflow authority).
> 5. This document **CANNOT override root `AGENTS.md`** (cross-runtime execution and safety contract).
> 6. Historical operator names ("Hermes") in this guide refer to earlier persona documentation; active AI development is governed strictly by `AGENTS.md` and active `.agents/skills/`.

---

---

## 📋 Table of Contents
1. [System Overview & Architecture](#1-system-overview--architecture)
2. [Codebase Map & Directory Layout](#2-codebase-map--directory-layout)
3. [Technology Stack](#3-technology-stack)
4. [Core Architectural Patterns](#4-core-architectural-patterns)
5. [Coding & Module Conventions](#5-coding--module-conventions)
6. [AI Governance & Security Rules](#6-ai-governance--security-rules)
7. [Step-by-Step Diagnostic & Bug-Fixing Protocol](#7-step-by-step-diagnostic--bug-fixing-protocol)
8. [Testing & Verification Guide](#8-testing--verification-guide)

---

## 1. System Overview & Architecture

**Dentix** is a multi-tenant dental clinic management SaaS platform. It is designed as a **modular monolith** optimized for scalability, security (HIPAA/PHI compliance), and reliability.

### Core Data Flow Layer Map
```
HTTP Request (Frontend SPA / Flutter App)
    ↓
API Gateway / Middleware (Auth, Rate Limits, Tenant Isolation check)
    ↓
FastAPI Router (backend/routers/)         ← HTTP request parsing & schema validation only (≤15 lines per route)
    ↓
Service Layer (backend/services/)         ← Core business logic, transaction boundaries, side effects, event dispatching
    ↓
CRUD / Repository Layer (backend/crud/)    ← Database queries & CRUD operations
    ↓
SQLAlchemy ORM Models (backend/models/)   ← Schema declarative mapping & database event listeners
    ↓
PostgreSQL Database (Neon Serverless)
```

---

## 2. Codebase Map & Directory Layout

Use this directory map to locate files quickly during diagnostics:

```text
dentix/
├── backend/
│   ├── main.py                 # FastAPI application boot & entry point
│   ├── database.py             # SQLAlchemy engine creation & DB session dependency
│   ├── ai/                     # AI assistant orchestration layer (agents, tools, RAG memory)
│   │   ├── agent/              # Intent detection, routing, prompting logic
│   │   ├── tools/              # Tool definitions, registry, execution helpers
│   │   └── config.py           # AI configurations
│   ├── core/                   # Shared system utilities (config, permissions, cache, response models)
│   │   ├── response.py         # Standardized API response handlers
│   │   ├── tenant_scope.py     # Multi-tenancy database session context management
│   │   └── permissions.py      # Granular Role-Based Access Control matrix
│   ├── crud/                   # Database-only queries (no HTTP exceptions allowed)
│   ├── middleware/              # Auth, audit logging, CORS, and Tenant middleware
│   ├── models/                 # SQLAlchemy DB models
│   ├── routers/                # FastAPI HTTP routing endpoints (30+ routers)
│   ├── schemas/                # Pydantic V2 request & response schemas
│   ├── services/               # Pure business logic layer (25+ service files)
│   ├── tasks/                  # Background jobs & workers (Celery)
│   └── tests/                  # Pytest test suite (unit, integration, isolation checks)
├── frontend/
│   ├── src/
│   │   ├── api/                # API client layer (Axios instances & routing client definitions)
│   │   ├── components/         # Reusable presentation components
│   │   ├── features/           # Feature-scoped modules (billing, inventory, patients)
│   │   ├── hooks/              # Shared custom React hooks
│   │   ├── pages/              # Router page components
│   │   └── shared/             # Shared layout and UI components (modals, buttons)
│   └── vite.config.js          # Vite configuration
├── dentix_mobile/              # Flutter-based mobile app structure
│   ├── lib/                    # Dart files (UI, services, state management)
│   └── pubspec.yaml            # Flutter package specifications
├── docs/                       # Comprehensive project specs, plans, & architecture guidelines
└── scripts/                    # Database seeds, migration utilities, and local development scripts
```

---

## 3. Technology Stack

Keep these technology versions and characteristics in mind when designing modifications:

*   **Backend Framework**: FastAPI (Python 3.11+) - Asynchronous web layer wrapping synchronous, transaction-managed services.
*   **Database ORM**: SQLAlchemy 2.0+ (using Declarative Base and transaction-controlled scopes) & Alembic (single database migration tool).
*   **Database Engine**: PostgreSQL (Neon Serverless) with Multi-Tenancy indexing and potential Row Level Security (RLS).
*   **Caching & Queue**: Redis (optional caching fallback to local memory) + Celery background workers.
*   **Frontend**: React 18 with Vite build tool and TailwindCSS styling.
*   **Mobile Framework**: Flutter (Dart) for Android and iOS clients.
*   **AI Integrations**: Groq API (using LLaMA-3.3-70b for complex reasoning/routing and LLaMA-3.1-8b for fast task execution) with ChromaDB for clinical RAG.

---

## 4. Core Architectural Patterns

You must strictly preserve these design patterns during edits.

### 4.1 Multi-Tenant Data Isolation
Every tenant (dental clinic) has their data isolated. Data leaks across clinics are fatal system defects.
*   **How it works**: Every HTTP request is parsed by `TenantMiddleware` which extracts the `tenant_id` (usually from headers/tokens) and binds it to a Python `contextvars` context inside `backend/core/tenant_scope.py`.
*   **SQLAlchemy Hook**: An ORM event listener in `tenant_scope.py` automatically appends `.filter(Model.tenant_id == current_tenant_id)` on all execution queries.
*   **Super Admin Bypass**: A Super Admin can bypass query filtering explicitly via `set_super_admin_bypass(True)`.
*   *Rule for you*: Always ensure `tenant_id` is set on every model creation and verify that queries do not accidentally escape `tenant_id` scopes.

### 4.2 Role-Based Access Control (RBAC)
We support **10 Roles** (Super Admin, Admin, Manager, Doctor, Receptionist, Nurse, Accountant, Assistant, Patient, Guest) governed by the permissions defined in `backend/core/permissions.py`.
*   All endpoints check for required permissions via route dependencies: `dependencies=[Depends(check_permission(Permission.CLINICAL_WRITE))]`.

### 4.3 Transactional Outbox Pattern
Side effects (e.g., triggering SMS, email notification, syncs to external providers, auditing logs) must not occur synchronously inside the API request cycle.
*   **How it works**: The service layer writes a pending event row to a `domain_events` table within the same DB transaction. A separate worker picks up and processes these events asynchronously.
*   *Rule for you*: Never perform blocking HTTP calls or heavy third-party executions inside FastAPI routes or core services. Emit an event using the `EventService` instead.

### 4.4 Idempotency
Critical mutation endpoints (e.g., recording a patient payment, booking a time slot) must protect against double-submission by using the `@idempotent()` decorator and requiring an `Idempotency-Key` header.

---

## 5. Coding & Module Conventions

You must adhere to these coding styles when modifying code:

1.  **Router Layer Constraints**:
    *   No business logic is allowed in `backend/routers/`.
    *   Maximum length per endpoint should be ≤ 15 lines.
    *   Delegate all calculations and data mutations directly to the service layer.
    *   Endpoints must return standard response helpers: `success_response(data, message)` or `cursor_paginated_response(...)`.
2.  **Service Layer Rules**:
    *   Services must contain all domain-specific validation logic.
    *   Coordinate between multiple tables using CRUD helpers.
    *   Use `@transactional` decorator when updating multiple models.
    *   Raise typed domain exceptions (e.g., `PatientNotFoundError`), which FastAPI exception handlers will convert to appropriate HTTP responses.
3.  **CRUD Layer Rules**:
    *   CRUD functions must perform database operations only.
    *   They must **never** raise FastAPI `HTTPException`.
    *   They should handle query optimizations (e.g., resolving N+1 queries using `joinedload`).
4.  **Immutability**:
    *   When mutating configurations or transferring state between systems, construct new objects/Pydantic schemas instead of directly modifying existing mutable properties.

---

## 6. AI Governance & Security Rules

If you are modifying the backend AI modules (`backend/ai/`) or performing edits under AI supervision, you must strictly follow these rules (documented in `docs/AI_GOVERNANCE_RULES.md`):

1.  **No Direct Database Access**: The backend AI agent must never run raw SQL queries or fetch models directly. It must only interact with registered tools that call service layer methods.
2.  **Least Privilege**: The AI agent can only invoke tools matching the user's role-based permissions.
3.  **Fail Safe, Not Smart**: On errors, missing parameters, or ambiguous context, stop execution and ask the user for clarification. Do not attempt to guess parameters.
4.  **No Silent Recovery**: Do not mask exceptions or perform dangerous auto-retries. All failures must be visible.

---

## 7. Step-by-Step Diagnostic & Bug-Fixing Protocol

When the user reports a daily usage error, a bug in production, or unexpected behavior, execute the following systematic diagnostic process:

### Step 7.1: Reconstruct the Error Context
*   Identify the exact workflow, screen, or endpoint the user was interacting with.
*   Request or locate the specific error message, status code, or log output in `app.log` or terminal trace outputs.
*   Examine JSON payloads from files like `db_logs.json` or frontend network traces if available.

### Step 7.2: Trace the Data Flow (Frontend to Backend)
Like the inventory cost report bug (found in `ROOT_CAUSE_ANALYSIS_CORRECTED.md`), bugs are often caused by discrepancies between layers:
1.  **Frontend Modal / View**: Check if the React component strips fields before submission (e.g., cleaning up parameters in `handleSave()`).
2.  **API Client Layer**: Verify which HTTP method and endpoint helper is being called (e.g., `createTreatment` vs a specific nested sub-endpoint).
3.  **Pydantic Schema**: Check `backend/schemas/` to verify if all fields sent by the frontend are modeled on the request class.
4.  **Service Layer logic**: Check if the service method ignores or fails to store metadata (e.g., consuming inventory stock but neglecting to insert a tracking table like `TreatmentMaterialUsage`).

### Step 7.3: Search the Codebase (Pattern Extraction)
Use search tools to find:
*   Where the endpoint is declared in `backend/routers/`.
*   Which service functions process the logic.
*   If other modules use similar patterns that are working correctly (e.g., successful stock deductions in other components).

### Step 7.4: Develop a Targeted, Non-Cascading Fix
*   Adhere to **Rule 12 (No Cascading Fixes)**: Fix only the root cause. Avoid rewriting or "cleaning up" unrelated code paths as it introduces regressions.
*   Ensure both frontend schemas, backend routers, schemas, and database layers are aligned.
*   Include defensive checks (e.g., resolving parent references automatically if they are omitted by the client).

---

## 8. Testing & Verification Guide

Every bug fix or code change requires validation to guarantee that multi-tenancy and RBAC isolation are intact.

### 8.1 Backend Verification
Navigate to `backend/` and execute tests to verify logic:

```bash
# Run the complete test suite
python -m pytest

# Run RBAC security coverage tests
python -m pytest tests/test_rbac_complete.py -v

# Run tenant isolation security verification
python -m pytest tests/test_tenant_isolation_complete.py -v

# Check specific domain services
python -m pytest tests/services/test_treatment_service.py -v
```

### 8.2 Frontend Verification
Ensure that local modifications do not break Vite compilation or lint checks:
```bash
cd frontend
npm run lint
npm run build
```

---

*Use this guide as your operational compass. When analyzing user issues, map the problem to the layered architecture, find the broken data-flow bridge, apply a minimal compliant fix, and execute pytest to verify isolation integrity.*
