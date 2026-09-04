# DENTIX Agent Skills

This directory contains repository-scoped skills used by supported AI coding runtimes (including Codex and Antigravity).

## Source Priority
1. Non-negotiable safety, tenant isolation, RBAC, data integrity, privacy, clinical integrity, and financial integrity constraints
2. Explicit current user requirement or approved implementation plan (within safety constraints)
3. `PROJECT_STANDARDS.md` (architecture authority)
4. `docs/engineering/DEVELOPMENT_WORKFLOW.md` (development lifecycle authority)
5. Root `AGENTS.md` (cross-runtime execution and safety contract)
6. Active product / domain specifications
7. Relevant `.agents/skills/` instructions
8. External skills (optional methodology / transport only)
9. General engineering conventions

## Skill Catalog (10 Native Skills)
1. `dentix-plan-execution`: Disciplined execution of approved multi-phase implementation plans without skipping steps.
2. `dentix-backend-fastapi`: FastAPI / Python layered patterns (Router -> Service -> CRUD -> Database), Pydantic schemas, and async execution.
3. `dentix-frontend-react`: React 18 + Vite, Tailwind CSS, TanStack Query server state, Zustand client state, RTL/LTR layout, and accessibility.
4. `dentix-mobile-flutter`: Flutter / Dart mobile client, Riverpod state, GoRouter navigation, and Dio HTTP clients.
5. `dentix-security-tenancy-rbac`: Multi-tenant boundary isolation (`tenant_id`), role-based access control, clinical PII masking, and financial data protection.
6. `dentix-database-migrations`: SQLAlchemy async models, PostgreSQL indexing, and safe Alembic migration authoring.
7. `dentix-testing-verification`: Test-driven verification discipline across Pytest, Vitest, and Flutter test suites governed by active CI configuration thresholds.
8. `dentix-systematic-debugging`: 4-phase evidence-first root cause analysis (RCA) and minimal surgical fixing (activated on actual failures only).
9. `dentix-code-review`: Structured code review with severity classification (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `NOTE`) for sensitive or release changes.
10. `dentix-performance`: Measurement-first performance profiling across database queries (N+1), backend async tasks, React rendering, and Flutter rebuilds.

## Activation Triggers & Loading Discipline
Do not preload all skills indiscriminately. Load only skills triggered by the active scope:
- **Approved multi-step plan**: `dentix-plan-execution`
- **Backend changes**: `dentix-backend-fastapi`
- **Frontend UI / state**: `dentix-frontend-react`
- **Mobile app**: `dentix-mobile-flutter`
- **Migrations / schema**: `dentix-database-migrations`
- **Auth / RBAC / Tenancy / RLS**: `dentix-security-tenancy-rbac`
- **Performance profiling**: `dentix-performance`
- **Actual test/runtime failure**: `dentix-systematic-debugging` (failure-only; never preload on clean paths)
- **Verification**: `dentix-testing-verification`
- **Independent / sensitive / final review when needed**: `dentix-code-review`

## Authoring Rules
- **Focused Responsibility**: One skill = one primary responsibility. Maintain exactly the 10 native skills.
- **DENTIX Specificity**: Do not add generic language or framework skills unless actively used by DENTIX.
- **No Duplication**: Do not duplicate core contract rules already enforced in root `AGENTS.md`.
- **High Justification Bar**: Do not add a new skill until an existing skill cannot cleanly cover the recurring need.
