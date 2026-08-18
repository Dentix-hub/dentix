# ADR 0002 — React Query and Zustand state ownership

Status: ACCEPTED  
Date verified: 2026-08-18

## Evidence

- `PROJECT_STANDARDS.md`
- `frontend/src/App.jsx`
- `frontend/src/lib/queryClient*`
- `frontend/src/store/ui.store.js`
- other stores/hooks under `frontend/src/`

## Context

The current React application provides TanStack React Query at the application root and uses Zustand stores for selected client/UI/tenant/auth state.

## Decision

Use TanStack React Query for server-derived/cacheable remote state and Zustand for intentional client-side/global UI state. Do not mirror the same server entity into a separate global store without a specific reason.

## Consequences

- Cache invalidation/query keys remain part of server-state design.
- UI state can stay lightweight and independent of network cache ownership.
- Feature refactors should avoid creating parallel sources of truth.

## Non-goals

This ADR does not require moving every existing local component state into Zustand or every request into React Query.
