# Dentix Project Standards 🧬
> **Source of Truth** | Phase B Architecture Baseline | Last Updated: April 2026

This document formalizes the architecture, conventions, and engineering standards for the Dentix platform. It serves as the definitive reference for maintaining a cohesive, resilient, and standardized codebase across all future developments.

---

## 1. Architecture & Structural Patterns

Dentix utilizes a **Strict Service-Layer Architecture** (Backend) paired with a **Decomposed Component Architecture** (Frontend), operating firmly within a **Multi-Tenant Ecosystem**.

### Backend (FastAPI / Python)
- **Routers (`backend/routers/`)**: Keep them thin. The router's sole responsibility is HTTP semantics—extracting request parameters, validating authentication/RBAC, and delegating work to a Service. Limit endpoints to fewer than 15 lines.
- **Services (`backend/services/`)**: The core domain engine. All business rules, complex calculations, cross-entity coordination, and external integrations (like AI) live here. Services must be strictly initialized with `(db, tenant_id)` to ensure execution context.
- **Models (`backend/models/`)**: SQLAlchemy ORM blueprints. Every model containing end-user data MUST carry a `tenant_id` column.
- **Schemas (`backend/schemas/`)**: Pydantic objects dedicated to strict typing, input sanitization, and output transformation.
- **Tenant Security**: Data separation is strictly enforced at the database abstraction level using an automatic ORM execution event listener (`tenant_scope.py`).

### Frontend (React / Vite)
- **Component Granularity**: Emphasize modular decomposition instead of monolithic pages. Complex layouts (e.g. `Patients.jsx`) must be fragmented into targeted modules (e.g., `PatientTable`, `PatientFilters`).
- **Shared UI Layer**: Resuable, generic application components live exclusively inside `src/shared/ui/`.
- **Build Ecosystem**: Vite serves as the bundle runner.

---

## 2. Naming Conventions

### Backend
- **Files & Directories**: `snake_case` (e.g., `patient_service.py`).
- **Variables & Functions**: `snake_case` (e.g., `total_cost`, `calculate_margin()`).
- **Classes & Models**: `PascalCase` (e.g., `StandardResponse`, `LabOrder`).
- **Constants**: `SCREAMING_SNAKE_CASE` (e.g., `API_V1_STR`, `MAX_RETRIES`).
- **Interface Definitions**: Clearly type-hint variables and return types (`-> List[schemas.Patient]`).

### Frontend
- **Component Files / Classes**: `PascalCase` (e.g., `PatientDetails.jsx`, `DentalChartContainer.jsx`).
- **Variables & Hook Methods**: `camelCase` (e.g., `isModalOpen`, `useFetchPatients`).
- **Styles**: Standardized Tailwind syntax with dynamic merges utilizing `clsx` and `tailwind-merge`.

---

## 3. UI/UX & Design System

- **Core Stylings**: Tailored with Tailwind CSS (`v3.4+`). Avoid inline CSS. 
- **Headless Architecture**: For complex accessible interactions, lean heavily on `@radix-ui/react` and `@headlessui/react`.
- **Iconography**: Rely exclusively on standard SVG frameworks incorporated via `lucide-react` or `react-icons`.
- **Motion**: Subtle standardizations utilizing `framer-motion` for transitions.
- **Notifications**: Implement global event awareness utilizing `react-hot-toast` for non-blocking confirmation or inline errors.

---

## 4. Business Logic & State Management

### Backend
- **Dependency Flow**: A request traverses `JWT Middleware -> Router Endpoint -> Domain Service -> CRUD execution -> Format wrapper -> Client`.
- **Database Contexts**: Core business manipulation MUST be routed through standard instantiated services (e.g., `get_lab_service(db, tenant_id)`).

### Frontend
- **Server State**: Managed strictly through `@tanstack/react-query`. Queries define caching timelines to prevent extraneous network overhead. Mutations invalidate context queries immediately to sync the UI.
- **Client State**: Centralized using `zustand` to administer overarching user flow layouts, transient interface states (like active filters, toggles, or selected contexts), and theme preferences. Redux is disallowed.

---

## 5. Error Handling & Validation

### API Output Standardization
All successful downstream routes MUST be enveloped in the `StandardResponse[T]` Pydantic type signature.
**Implementation via Helpers**:
```python
# Returns fully serialized Generic Types 
return success_response(data=items, message="Retrieved successfully")
```

### Backend Exceptions
- Utilize native HTTP protocols combined with custom handlers. 
- Fast failure via `raise HTTPException(...)` should be utilized for authentication / malformed inputs directly in the router.
- Inside Service scopes, utilize specialized Domain Exceptions (e.g., `AIException`, `ValueError` for resource constraints) which are subsequently tracked and managed gracefully at the router's boundary or via top-level `ExceptionHandlers`.

### Frontend Mitigation
- `React Query` abstracts fetching failures directly. Rely on `onError` hooks inside `useMutation()`.
- Log critical runtime frontend crashes to `/api/v1/system/logs`.
- Display actionable, friendly toast alerts to the user. Avoid rendering raw `.stack` traces or undefined DB codes directly in the DOM.

---

*This document captures the current engineering standards of the Dentix project. Adherence to these pillars ensures horizontal scalability, technical clarity, and stable feature pipelines.*
