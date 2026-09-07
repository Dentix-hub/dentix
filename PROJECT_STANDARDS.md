# Dentix Project Standards

> **Architecture & engineering source of truth for DENTIX.**

---

## 1. Architecture — HARD Constraints

These constraints protect data integrity and security. They cannot be relaxed without explicit justification.

### Multi-Tenant Isolation
- Every model containing tenant-scoped clinic/end-user data MUST carry a `tenant_id` column. Globally shared or system models are not required to contain `tenant_id`.
- Data separation is enforced at the database abstraction level using the automatic ORM execution event listener (`tenant_scope.py`).
- Never retrieve an entity by primary key alone without matching against the active `tenant_id`.

### Server-Side RBAC
- Protected application endpoints must enforce the appropriate server-side authentication/RBAC requirements using existing backend permission mechanisms (`get_current_user`, `check_permission`).
- Intentionally public/system endpoints such as health/liveness/readiness probes may remain unauthenticated when their existing contract requires that.
- Never rely solely on frontend UI hiding for access control.

### API Output Standardization
- Normal application API responses should preserve their established `StandardResponse[T]` contract where applicable:
```python
return success_response(data=items, message="Retrieved successfully")
```
- Infrastructure probes, streaming/file responses, webhooks, and other intentionally specialized endpoints may preserve their existing response contracts.

---

## 2. Architecture — DEFAULT Conventions

These are the standard architecture patterns. Deviation requires a technical reason, not permission for every exception.

### Backend (FastAPI / Python)
- **Layer flow**: Router → Service → CRUD → Database (SQLAlchemy Async / PostgreSQL).
- **Routers** (`backend/routers/`): Focused on HTTP semantics — extracting request parameters, validating authentication/RBAC, and delegating work to a Service. Prefer moving business logic into services. Do not split correct code solely to satisfy an arbitrary line-count threshold.
- **Services** (`backend/services/`): The core domain engine. All business rules, complex calculations, cross-entity coordination, and external integrations live here. Services must operate in tenant-aware context (receive or have access to `tenant_id`).
- **CRUD** (`backend/crud/`): Encapsulate database query building, joins, filtering, and persistence. Enforce tenant isolation in all queries using tenant scope utilities.
- **Models** (`backend/models/`): SQLAlchemy ORM blueprints with proper table definitions, relationships, and constraints.
- **Schemas** (`backend/schemas/`): Pydantic objects dedicated to strict typing, input sanitization, and output transformation. Separate base, create, update, and response models.
- **Async Pattern**: Follow the existing async/sync pattern used by each module. Do not introduce blocking I/O inside async request paths.
- **Dependency Flow**: `JWT Middleware → Router Endpoint → Domain Service → CRUD execution → Format wrapper → Client`.
- **Error Handling**: Use `HTTPException` with informative error codes. Inside services, use specialized domain exceptions managed at the router boundary or via top-level exception handlers.

### Frontend (React / Vite)
- **Framework**: React 18 + Vite.
- **Server State**: `@tanstack/react-query`. Queries define caching timelines. Mutations invalidate relevant query caches immediately.
- **Client State**: `zustand`. Redux is disallowed.
- **Shared UI Layer**: Reusable, generic application components live in `src/shared/ui/`.
- **Component Granularity**: Emphasize modular decomposition instead of monolithic pages.
- **Bidirectional Layout**: All UI must support RTL (Arabic) and LTR (English) for text, layouts, forms, and dialogs.

### Mobile (Flutter / Dart)
- **State Management**: Riverpod (`flutter_riverpod`).
- **Routing**: `go_router`.
- **Networking**: `dio` with centralized interceptors for authentication, tenant headers, and token refresh.
- **Model Serialization**: `freezed` / `json_serializable`.
- **Feature Structure**: Features organized under `dentix_mobile/lib/features/<feature>/` with presentation, domain, and data layers.
- **No Duplicate Logic**: Never duplicate complex backend financial calculations or clinical validation on the mobile client.

---

## 3. Conventions — RECOMMENDATION

These are preferences that improve consistency. They may be overridden by context.

### Naming

**Backend**: Files/directories `snake_case`, variables/functions `snake_case`, classes/models `PascalCase`, constants `SCREAMING_SNAKE_CASE`. Type-hint variables and return types.

**Frontend**: Component files `PascalCase`, variables/hooks `camelCase`.

### UI/UX & Design System
- **Styling**: Tailwind CSS. Avoid inline CSS.
- **Headless Components**: `@radix-ui/react` and `@headlessui/react` for accessible interactions.
- **Icons**: `lucide-react` or `react-icons`.
- **Motion**: `framer-motion` for subtle transitions.
- **Notifications**: `react-hot-toast` for non-blocking feedback.

---

*This document captures the current engineering standards of the Dentix project. Adherence to these pillars ensures horizontal scalability, technical clarity, and stable feature pipelines.*
