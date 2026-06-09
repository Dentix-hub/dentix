# DENTIX Domain Module Conventions

As part of Phase 2 (Architecture Refactor), DENTIX is transitioning to a **Domain Module Pattern** to improve maintainability and decouple business logic.

## 1. File Structure

Each domain (e.g., `patients`, `appointments`, `billing`) should ideally be encapsulated. For now, we enforce separation of concerns across the following layers:

- **Routers** (`backend/routers/`)
  - **Rule**: NO business logic. 
  - **Responsibility**: HTTP parsing, authentication/permission checks, and returning standardized API responses.
  - **Delegates to**: Services.

- **Services** (`backend/services/`)
  - **Rule**: Pure business logic.
  - **Responsibility**: Enforce rules (e.g. "cannot cancel past appointment"), coordinate between multiple repositories/CRUDs, and emit domain events.
  - **Decorators**: Use `@transactional` for cross-entity mutations.

- **CRUD / Repositories** (`backend/crud/`)
  - **Rule**: Pure data access.
  - **Responsibility**: Build SQLAlchemy queries, handle caching, and execute database reads/writes.
  - **No HTTP**: Must not raise `HTTPException`.

- **Models** (`backend/models/`)
  - **Rule**: Declarative schema definitions only.

- **Events** (Future: `backend/events/`)
  - **Rule**: Handlers for domain events published by the `EventService`.

## 2. API Responses

All router endpoints MUST return data using the standard response helpers in `backend.core.response`:
- `success_response(data, message)`
- `cursor_paginated_response(data, limit, next_cursor, has_more, message)`

These helpers automatically inject the `trace_id` for request correlation.

## 3. Emitting Side Effects (Domain Events)

Side effects (notifications, CRM syncing, emails) MUST NOT be executed synchronously in the router or service.
Instead, use the **Transactional Outbox Pattern**:

```python
from backend.services.event_service import event_service

# Inside a service method:
event_service.emit_event(
    db=db,
    event_type="appointment.created",
    aggregate_type="appointment",
    aggregate_id=str(appointment.id),
    payload={"patient_id": patient_id, "time": appointment.date_time.isoformat()},
    tenant_id=tenant_id
)
# DB commit will save both the business entity and the event
```

## 4. Idempotency

Endpoints that create or mutate sensitive state (like payments) should use the `@idempotent()` decorator from `backend.core.idempotency` and require clients to pass an `Idempotency-Key` header.
