# ADR 0001 — Service-layer backend boundaries

Status: ACCEPTED  
Date verified: 2026-08-18

## Evidence

- `PROJECT_STANDARDS.md`
- `backend/routers/patients.py`
- `backend/routers/accounting.py`
- `backend/services/`
- `backend/crud/`

## Context

Dentix has FastAPI HTTP routers, domain/service modules, CRUD/data-access helpers, SQLAlchemy models, and Pydantic schemas. Current routers inspected in Plan 01 delegate non-trivial work to services rather than defining a second business-logic implementation in the UI or documentation.

## Decision

Use routers as HTTP/auth/validation boundaries, services for business workflows and cross-entity rules, and CRUD/data-access helpers for focused persistence operations where that layer is used. SQLAlchemy models/schemas remain the data definition/validation boundary.

This is a direction/ownership rule, not a claim that every legacy endpoint is perfectly layered today.

## Consequences

- New business rules should not be duplicated in routers or frontend code.
- Refactors must preserve API/business contracts unless separately approved.
- Legacy exceptions should be improved incrementally, not hidden by documentation.

## Non-goals

No runtime refactor is performed by this ADR.
