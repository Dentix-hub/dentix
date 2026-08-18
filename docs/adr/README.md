# Dentix Architecture Decision Records

ADRs record major **currently evidenced** architectural decisions. They are not a place to retroactively invent rationale.

## Status vocabulary

- `ACCEPTED`: current executable sources support the decision.
- `SUPERSEDED`: a later ADR replaces it.
- `PROPOSED`: not yet current truth.
- `HISTORICAL`: retained for context but no longer current.

## Precedence

Runtime/config/migrations/tests outrank ADR prose if they diverge. When implementation changes, update/supersede the ADR rather than pretending the old text is still true.

## Current ADRs

- [0001 — Service-layer backend boundaries](0001-service-layer-backend-boundaries.md)
- [0002 — React Query and Zustand state ownership](0002-react-query-zustand-state-ownership.md)
- [0003 — PostgreSQL production database contract](0003-postgresql-production-database.md)
- [0004 — Layered tenant isolation](0004-layered-tenant-isolation.md)

## New ADR template

```md
# ADR NNNN — Title

Status: PROPOSED | ACCEPTED | SUPERSEDED | HISTORICAL
Date: YYYY-MM-DD

## Evidence
- executable/config/test paths

## Context
...

## Decision
...

## Consequences
...

## Non-goals
...
```
